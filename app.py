import io
import os
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

from utils.parsing import extract_text_from_pdf, normalize_text
from utils.matching import extract_jd_skills, match_resume_to_jd, select_supporting_snippets
from utils.llm import GroqCoverLetterGenerator


def init_env():
    load_dotenv()


@st.cache_data(show_spinner=False)
def parse_resume_cached(file_bytes: bytes) -> str:
    return extract_text_from_pdf(file_bytes)


@st.cache_data(show_spinner=False)
def jd_skills_cached(jd_text: str):
    return sorted(list(extract_jd_skills(jd_text)))


def get_api_key_from_env_or_input() -> Optional[str]:
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    with st.expander("Set Groq API Key"):
        key = st.text_input("GROQ_API_KEY", type="password")
        if key:
            st.session_state["GROQ_API_KEY"] = key
            return key
    return st.session_state.get("GROQ_API_KEY")


def main():
    st.set_page_config(page_title="AI Cover Letter Generator", page_icon="✉️", layout="centered")
    init_env()

    st.title("✉️ AI Cover Letter Generator")
    st.caption("Upload your resume and a job description. Generates a tailored cover letter that cites your relevant experience.")

    # Inputs
    with st.sidebar:
        st.header("Inputs")
        company = st.text_input("Company Name", placeholder="Acme Corp")
        job_title = st.text_input("Job Title", placeholder="Senior Software Engineer")
        jd_text = st.text_area("Job Description", height=240, placeholder="Paste the JD here…")
        uploaded_pdf = st.file_uploader("Upload Resume (PDF)", type=["pdf"]) 

        model = st.selectbox(
            "Groq Model",
            options=["llama-3.1-8b-instant"],
            index=0,
            help="Select the LLM model hosted on Groq"
        )

        temperature = st.slider("Creativity (temperature)", 0.0, 1.2, 0.3, 0.1)

    # API Key
    api_key = get_api_key_from_env_or_input()
    if not api_key:
        st.info("Provide your GROQ_API_KEY in a .env file or set it in the expander.")

    # Main actions
    generate_btn = st.button("Generate Cover Letter", type="primary", use_container_width=True)

    if generate_btn:
        if not all([company, job_title, jd_text, uploaded_pdf, api_key]):
            st.error("Please provide Company, Job Title, Job Description, Resume PDF, and Groq API Key.")
            return

        with st.status("Processing…", expanded=False) as status:
            status.update(label="Reading resume PDF")
            try:
                resume_text = parse_resume_cached(uploaded_pdf.read())
            except Exception as e:
                st.exception(e)
                st.stop()

            status.update(label="Parsing job description and matching skills")
            jd_skills = jd_skills_cached(jd_text)
            match_result = match_resume_to_jd(set(jd_skills), resume_text)

            status.update(label="Selecting supporting snippets from resume")
            snippets = select_supporting_snippets(match_result, resume_text, jd_text)

            status.update(label="Generating cover letter with Groq")
            generator = GroqCoverLetterGenerator(api_key=api_key, model=model, temperature=temperature)
            try:
                cover_letter = generator.generate(
                    company=company,
                    job_title=job_title,
                    job_description=jd_text,
                    jd_skills=jd_skills,
                    matched_skills=match_result["matched_skills"],
                    resume_snippets=snippets,
                    resume_bio=normalize_text(resume_text[:1200])  # brief resume summary context
                )
            except Exception as e:
                st.exception(e)
                st.stop()

            status.update(label="Done", state="complete")

        st.subheader("Generated Cover Letter")
        st.write(cover_letter)

        st.download_button(
            label="Download as .txt",
            data=cover_letter.encode("utf-8"),
            file_name=f"Cover_Letter_{company.replace(' ', '_')}_{job_title.replace(' ', '_')}.txt",
            mime="text/plain"
        )

        st.success("Cover letter generated successfully.")


if __name__ == "__main__":
    main()
