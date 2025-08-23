import re
from typing import Dict, List, Set, Tuple

from rapidfuzz import process, fuzz


CANONICAL_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "go", "golang", "c++", "c#", "rust", "kotlin", "swift", "scala", "ruby", "php",
    # Frameworks & Libraries
    "react", "react.js", "reactjs", "next.js", "nextjs", "node", "node.js", "express", "django", "flask", "fastapi", "spring", "spring boot",
    "angular", "vue", "svelte", "tailwind", "bootstrap", "redux",
    # Data & ML
    "pandas", "numpy", "scikit-learn", "sklearn", "tensorflow", "pytorch", "mlflow", "xgboost", "lightgbm",
    # Cloud & DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible", "github actions", "gitlab ci", "jenkins",
    # Databases
    "postgres", "postgresql", "mysql", "mongodb", "redis", "dynamodb", "elasticsearch", "snowflake", "bigquery",
    # Other
    "grpc", "rest", "graphql", "apache kafka", "kafka", "rabbitmq", "spark", "hadoop", "airflow",
}

ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "gcloud": "gcp",
    "amazon web services": "aws",
    "ms azure": "azure",
    "llm": "large language models",
}


def _tokenize(text: str) -> List[str]:
    # Keep dots in tech terms like next.js, node.js
    words = re.findall(r"[a-zA-Z0-9.+#-]+", text.lower())
    return words


def extract_jd_skills(jd_text: str) -> Set[str]:
    tokens = _tokenize(jd_text)
    raw_terms: Set[str] = set(tokens)

    # Normalize aliases
    normalized: Set[str] = set()
    for t in raw_terms:
        t_norm = ALIASES.get(t, t)
        normalized.add(t_norm)

    # Filter to canonical-ish skills via fuzzy containment
    jd_skills: Set[str] = set()
    for skill in CANONICAL_SKILLS:
        # if any token matches skill with decent similarity
        match, score, _ = process.extractOne(skill, normalized, scorer=fuzz.partial_ratio) or (None, 0, None)
        if score >= 90:
            jd_skills.add(skill)
        elif skill in normalized:
            jd_skills.add(skill)

    return jd_skills


def match_resume_to_jd(jd_skills: Set[str], resume_text: str) -> Dict:
    resume_tokens = set(_tokenize(resume_text))

    matched: List[Tuple[str, str, int]] = []  # (jd_skill, resume_term, score)
    for jd_skill in jd_skills:
        res = process.extractOne(jd_skill, resume_tokens, scorer=fuzz.token_set_ratio)
        if res:
            resume_term, score, _ = res
            if score >= 80:
                matched.append((jd_skill, resume_term, score))

    matched_skills = [m[0] for m in matched]
    return {
        "matched": matched,
        "matched_skills": matched_skills,
    }


def select_supporting_snippets(match_result: Dict, resume_text: str, window: int = 380) -> List[str]:
    # For each matched skill, try to find a nearby sentence/line
    snippets: List[str] = []
    for jd_skill, resume_term, _ in match_result.get("matched", []):
        idx = resume_text.lower().find(resume_term.lower())
        if idx == -1:
            continue
        start = max(0, idx - window)
        end = min(len(resume_text), idx + window)
        snippet = resume_text[start:end].strip()
        snippets.append(f"Skill: {jd_skill}\nContext: {snippet}")
    # De-duplicate and limit
    uniq: List[str] = []
    seen = set()
    for s in snippets:
        key = s[:120]
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    return uniq[:8]
