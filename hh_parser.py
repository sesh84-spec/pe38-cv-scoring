import re
import time
import random
from typing import Optional

import requests
from bs4 import BeautifulSoup


# Более "похожий на браузер" набор заголовков
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def get_html(url: str, timeout: int = 20, pause_range: tuple[float, float] = (0.3, 1.0)) -> str:
    """
    Загружает HTML страницы.
    pause_range: небольшая случайная задержка перед запросом (уменьшает шанс антибота).
    """
    time.sleep(random.uniform(*pause_range))

    r = requests.get(
        url,
        headers=HEADERS,
        timeout=timeout,
        allow_redirects=True,
    )
    r.raise_for_status()
    return r.text


def _clean(text: str) -> str:
    text = re.sub(r"\r", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _safe_text(soup: BeautifulSoup, tag: Optional[str] = None, attrs: Optional[dict] = None, default: str = "Не найдено") -> str:
    el = soup.find(tag, attrs or {}) if tag else soup.find(attrs or {})
    return el.get_text(" ", strip=True) if el else default


def extract_vacancy_data(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.find("h1")
    title = title_el.get_text(" ", strip=True) if title_el else "Не найдено"

    salary_el = soup.find(attrs={"data-qa": "vacancy-salary"})
    salary = salary_el.get_text(" ", strip=True) if salary_el else "Не указано"

    company_el = soup.find(attrs={"data-qa": "vacancy-company-name"})
    company = company_el.get_text(" ", strip=True) if company_el else "Не найдено"

    desc_el = soup.find(attrs={"data-qa": "vacancy-description"})
    desc = desc_el.get_text("\n", strip=True) if desc_el else "Описание не найдено"

    md = (
        f"# {title}\n\n"
        f"**Компания:** {company}\n\n"
        f"**Зарплата:** {salary}\n\n"
        f"## Описание\n\n{desc}"
    )
    return _clean(md)


def extract_resume_data(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    name = _safe_text(soup, "h2", {"data-qa": "bloko-header-1"}, default="Имя не найдено")
    location = _safe_text(soup, "span", {"data-qa": "resume-personal-address"}, default="Не найдено")
    job_title = _safe_text(soup, "span", {"data-qa": "resume-block-title-position"}, default="Не найдено")
    status = _safe_text(soup, "span", {"data-qa": "job-search-status"}, default="Не найдено")

    experiences_md = []
    exp_block = soup.find("div", {"data-qa": "resume-block-experience"})
    if exp_block:
        items = exp_block.find_all("div", class_="resume-block-item-gap")
        for item in items:
            period_el = item.find("div", class_="bloko-column_s-2")
            period = period_el.get_text(" ", strip=True) if period_el else ""

            company_el = item.find("div", class_="bloko-text_strong")
            company = company_el.get_text(" ", strip=True) if company_el else ""

            pos_el = item.find(attrs={"data-qa": "resume-block-experience-position"})
            position = pos_el.get_text(" ", strip=True) if pos_el else ""

            desc_el = item.find(attrs={"data-qa": "resume-block-experience-description"})
            desc = desc_el.get_text("\n", strip=True) if desc_el else ""

            if any([period, company, position, desc]):
                experiences_md.append(
                    f"**{period}**\n\n*{company}*\n\n**{position}**\n\n{desc}\n"
                )

    skills = []
    skills_block = soup.find("div", {"data-qa": "skills-table"})
    if skills_block:
        for tag in skills_block.find_all("span", {"data-qa": "bloko-tag__text"}):
            t = tag.get_text(" ", strip=True)
            if t:
                skills.append(t)

    md = (
        f"# {name}\n\n"
        f"**Местоположение:** {location}\n\n"
        f"**Желаемая должность:** {job_title}\n\n"
        f"**Статус поиска:** {status}\n\n"
        f"## Опыт работы\n\n"
        f"{(''.join(experiences_md)).strip() if experiences_md else 'Опыт работы не найден.'}\n\n"
        f"## Ключевые навыки\n\n"
        f"{', '.join(skills) if skills else 'Навыки не указаны.'}"
    )
    return _clean(md)
