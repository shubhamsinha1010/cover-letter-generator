from typing import List, Optional

from groq import Groq

from .prompts import COVER_LETTER_SYSTEM_PROMPT, COVER_LETTER_USER_PROMPT


class GroqCoverLetterGenerator:
    def __init__(self, api_key: str, model: str = "llama3-70b-8192", temperature: float = 0.3):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def generate(
        self,
        company: str,
        job_title: str,
        job_description: str,
        jd_skills: List[str],
        matched_skills: List[str],
        resume_snippets: List[str],
        resume_bio: Optional[str] = None,
    ) -> str:
        user_prompt = COVER_LETTER_USER_PROMPT.format(
            company=company,
            job_title=job_title,
            job_description=job_description.strip(),
            jd_skills=", ".join(jd_skills),
            matched_skills=", ".join(matched_skills) if matched_skills else "(none)",
            resume_bio=(resume_bio or "").strip(),
            resume_snippets="\n\n".join(resume_snippets) if resume_snippets else "(no snippets found)",
        )

        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": COVER_LETTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return completion.choices[0].message.content.strip()
