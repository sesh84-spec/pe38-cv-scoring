import os

from flask import Flask, render_template, request
from dotenv import load_dotenv
from openai import OpenAI

from hh_parser import get_html, extract_vacancy_data, extract_resume_data

load_dotenv()

app = Flask(__name__)

SYSTEM_PROMPT = """
Проскорь кандидата, насколько он подходит для данной вакансии.

Сначала напиши короткий анализ (3–7 пунктов), который поясняет оценку.
Отдельно оцени качество заполнения резюме по шкале 1–10:
- Понятно ли, с какими задачами сталкивался кандидат?
- Описано ли, как именно он их решал?
- Указаны ли результаты/достижения?

Затем представь итоговую оценку соответствия вакансии по шкале 1–10.
Итоговая оценка должна учитывать качество резюме.

Формат ответа:
1) Анализ:
- ...
2) Качество резюме: X/10
3) Соответствие вакансии: Y/10
""".strip()


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Не найден OPENAI_API_KEY. Проверь .env или переменные окружения.")
    return OpenAI(api_key=api_key)


def score_cv(job_text: str, cv_text: str) -> str:
    client = get_client()
    user_prompt = f"# ВАКАНСИЯ\n{job_text}\n\n# РЕЗЮМЕ\n{cv_text}"

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=900,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content


def looks_like_url(s: str) -> bool:
    s = (s or "").strip().lower()
    return s.startswith("http://") or s.startswith("https://")


@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    error = ""

    job_input = ""
    cv_input = ""

    mode = "auto"  # auto | text | url

    parsed_job = ""
    parsed_cv = ""

    if request.method == "POST":
        job_input = (request.form.get("job_input") or "").strip()
        cv_input = (request.form.get("cv_input") or "").strip()
        mode = (request.form.get("mode") or "auto").strip()

        if not job_input or not cv_input:
            error = "Заполни оба поля: вакансия и резюме (текст или ссылка)."
        else:
            try:
                # Определяем режим
                job_is_url = looks_like_url(job_input)
                cv_is_url = looks_like_url(cv_input)

                use_urls = False
                if mode == "url":
                    use_urls = True
                elif mode == "text":
                    use_urls = False
                else:  # auto
                    use_urls = job_is_url and cv_is_url

                if use_urls:
                    job_html = get_html(job_input)
                    cv_html = get_html(cv_input)

                    parsed_job = extract_vacancy_data(job_html)
                    parsed_cv = extract_resume_data(cv_html)

                    result = score_cv(parsed_job, parsed_cv)
                else:
                    result = score_cv(job_input, cv_input)

            except Exception as e:
                error = f"Ошибка: {e}"

    return render_template(
        "index.html",
        result=result,
        error=error,
        job_input=job_input,
        cv_input=cv_input,
        mode=mode,
        parsed_job=parsed_job,
        parsed_cv=parsed_cv,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
