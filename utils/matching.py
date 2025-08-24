import re
from typing import Dict, List, Set, Tuple

from rapidfuzz import process, fuzz


CANONICAL_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "go", "golang", "c++", "c#", "rust", "kotlin", "swift", "scala", "ruby", "php",
    # Frameworks & Libraries
    "react", "react.js", "reactjs", "next.js", "nextjs", "node", "node.js", "express", "django", "flask", "fastapi", "spring", "spring boot",
    "angular", "vue", "svelte", "tailwind", "bootstrap", "redux",
    # Practices & Patterns
    "test-driven development", "tdd", "microservices", "event-driven", "serverless",
    # Data & ML
    "pandas", "numpy", "scikit-learn", "sklearn", "tensorflow", "pytorch", "mlflow", "xgboost", "lightgbm",
    # Cloud & DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "terraform", "ansible", "github actions", "gitlab ci", "jenkins",
    # Databases
    "postgres", "postgresql", "mysql", "mongodb", "redis", "dynamodb", "elasticsearch", "snowflake", "bigquery",
    # APIs & Data Infra
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
    "k8s": "kubernetes",
    "postgres": "postgresql",
}


def _tokenize(text: str) -> List[str]:
    # Keep dots in tech terms like next.js, node.js
    words = re.findall(r"[a-zA-Z0-9.+#-]+", text.lower())
    return words


def _ngrams(tokens: List[str], n: int) -> List[str]:
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def extract_jd_skills(jd_text: str) -> Set[str]:
    tokens = _tokenize(jd_text)
    # Build a term set including unigrams, bigrams, trigrams
    terms: Set[str] = set(tokens)
    terms.update(_ngrams(tokens, 2))
    terms.update(_ngrams(tokens, 3))

    # Normalize aliases
    normalized: Set[str] = set()
    for t in terms:
        t_norm = ALIASES.get(t, t)
        normalized.add(t_norm)

    # Filter to canonical-ish skills via fuzzy containment
    jd_skills: Set[str] = set()
    for skill in CANONICAL_SKILLS:
        # Try to find a close match among normalized terms
        res = process.extractOne(skill, normalized, scorer=fuzz.partial_ratio)
        score = res[1] if res else 0
        if score >= 88:
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
            if score >= 78:
                matched.append((jd_skill, resume_term, score))

    matched_skills = [m[0] for m in matched]
    return {
        "matched": matched,
        "matched_skills": matched_skills,
    }


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Tuple[int, str]]:
    chunks: List[Tuple[int, str]] = []
    i = 0
    n = len(text)
    idx = 0
    while i < n:
        chunk = text[i : i + chunk_size]
        chunks.append((idx, chunk))
        idx += 1
        i += max(1, chunk_size - overlap)
    return chunks


def _score_chunks_against_jd(jd_text: str, chunks: List[Tuple[int, str]]) -> List[Tuple[int, str, int]]:
    scored: List[Tuple[int, str, int]] = []
    for cid, ctext in chunks:
        score = fuzz.token_set_ratio(ctext.lower(), jd_text.lower())
        scored.append((cid, ctext, score))
    # sort high to low
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored


def _diversify_top_k(scored: List[Tuple[int, str, int]], k: int = 6, min_gap: int = 1) -> List[Tuple[int, str, int]]:
    selected: List[Tuple[int, str, int]] = []
    used_ids: Set[int] = set()
    for cid, ctext, score in scored:
        # avoid adjacent chunk ids to reduce redundancy
        if any(abs(cid - uid) <= min_gap for uid in used_ids):
            continue
        selected.append((cid, ctext, score))
        used_ids.add(cid)
        if len(selected) >= k:
            break
    # if not enough selected, fill remaining ignoring diversity
    if len(selected) < k:
        for item in scored:
            if item not in selected:
                selected.append(item)
                if len(selected) >= k:
                    break
    return selected


def select_supporting_snippets(match_result: Dict, resume_text: str, jd_text: str, top_k: int = 6) -> List[str]:
    """
    Select top-K resume snippets most relevant to the JD using chunk reranking and light diversity.
    Each snippet is labeled with any matched JD skills appearing inside the chunk (if found).
    """
    chunks = _chunk_text(resume_text, chunk_size=1000, overlap=200)
    scored = _score_chunks_against_jd(jd_text, chunks)
    top = _diversify_top_k(scored, k=top_k, min_gap=1)

    # map matched skills into chunks where they appear
    matched = match_result.get("matched", [])
    snippets: List[str] = []
    for cid, ctext, score in top:
        skills_in_chunk: List[str] = []
        lower_ctext = ctext.lower()
        for jd_skill, resume_term, _ in matched:
            if resume_term.lower() in lower_ctext or jd_skill.lower() in lower_ctext:
                skills_in_chunk.append(jd_skill)
        skills_str = ", ".join(sorted(set(skills_in_chunk))) if skills_in_chunk else "(general relevance)"
        snippets.append(f"Relevance: {score}\nSkills: {skills_str}\nContext: {ctext.strip()}")

    return snippets[:top_k]
