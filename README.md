# AI Cover Letter Generator (Streamlit + Groq)

Generate a tailored cover letter from your resume (PDF) and a job description using Groq-hosted LLMs.

## Features
- Upload resume (PDF) and paste Job Description
- Extract JD skills and match to your resume with fuzzy matching
- Provide supporting resume snippets as evidence
- Generate a concise, tailored cover letter with Groq (Llama 3 / Mixtral)

## Requirements
- Python 3.10+
- Groq API key

## Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env  # then edit .env to add your GROQ_API_KEY
```

## Run
```bash
streamlit run app.py
```

## Configuration
- Set `GROQ_API_KEY` in `.env` or input it in the app sidebar expander.
- Choose a Groq model in the sidebar: `openai/gpt-oss-20b` (default) or `openai/gpt-oss-120b`.
- Adjust creativity (temperature) as desired.

## Notes
- PDF text extraction uses `pypdf`; highly stylized PDFs may yield imperfect text.
- The app avoids fabricating by constraining to your resume snippets; edit your resume for best results.

## Security
- Your API key is kept local in environment variables or Streamlit session state.
