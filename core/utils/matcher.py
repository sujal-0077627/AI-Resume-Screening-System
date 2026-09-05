"""Resume matching engine using TF-IDF, Cosine Similarity and Sentence-Transformers."""
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Lazy-load sentence transformer to avoid slow startup
_model = None


def _get_sentence_model():
    """Load Sentence-Transformer model lazily (cached)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def _clean_text(text):
    """Basic text cleaning for matching."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s+#.]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def tfidf_similarity(job_text, resume_text):
    """
    Compute blended Term-Frequency / N-Gram Cosine similarity between job and resume.

    Uses n-grams (1-2) with sublinear term-frequency scaling and stop-words removal
    to capture both single keywords ("Python") and compound phrases ("Machine Learning",
    "REST API") reliably without IDF degradation on pairwise inputs.

    Returns:
        float: Similarity score between 0 and 1.
    """
    cleaned_job = _clean_text(job_text)
    cleaned_resume = _clean_text(resume_text)
    if not cleaned_job or not cleaned_resume:
        return 0.0

    corpus = [cleaned_job, cleaned_resume]
    # Use sublinear TF, custom token pattern for tech symbols, and smooth IDF with (1,2) n-grams
    vectorizer = TfidfVectorizer(
        stop_words='english',
        token_pattern=r'(?u)\b[\w+#\.\-]{2,}\b',
        ngram_range=(1, 2),
        sublinear_tf=True,
        norm='l2'
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        # Ensure value is bounded between 0 and 1
        return float(max(0.0, min(1.0, similarity)))
    except (ValueError, ZeroDivisionError):
        return 0.0



def semantic_similarity(job_text, resume_text):
    """
    Compute semantic similarity using Sentence-Transformers.
    Combines whole-document embedding vector cosine similarity with
    sentence-level maximum relevance to capture both holistic contextual
    relevance and detailed clause alignment accurately.

    Returns:
        float: Similarity score between 0 and 1.
    """
    try:
        model = _get_sentence_model()

        # Whole-document contextual embeddings
        doc_embeddings = model.encode([job_text[:3000], resume_text[:3000]])
        doc_sim = float(cosine_similarity([doc_embeddings[0]], [doc_embeddings[1]])[0][0])
        doc_sim = max(0.0, min(1.0, doc_sim))

        # Sentence-level clause comparison
        job_sentences = [
            s.strip() for s in re.split(r'[.!?\n]+', job_text)
            if len(s.strip()) >= 10
        ][:25]
        resume_sentences = [
            s.strip() for s in re.split(r'[.!?\n]+', resume_text)
            if len(s.strip()) >= 10
        ][:40]

        if not job_sentences or not resume_sentences:
            return doc_sim

        # Encode all sentences at once
        all_texts = job_sentences + resume_sentences
        embeddings = model.encode(all_texts)

        job_emb = embeddings[:len(job_sentences)]
        resume_emb = embeddings[len(job_sentences):]

        # Pairwise similarity: each job sentence vs each resume sentence
        sim_matrix = cosine_similarity(job_emb, resume_emb)
        best_matches = sim_matrix.max(axis=1)
        sent_sim = float(best_matches.mean())
        sent_sim = max(0.0, min(1.0, sent_sim))

        # Blend document-level context and clause-level alignment
        combined = (0.60 * doc_sim) + (0.40 * sent_sim)
        return float(max(0.0, min(1.0, combined)))
    except Exception:
        # Fallback to TF-IDF if model unavailable
        return tfidf_similarity(job_text, resume_text)


def _normalize_skill(skill):
    """Normalize a skill string for matching."""
    skill = skill.lower().strip()
    # Remove common punctuation and normalize whitespace
    skill = re.sub(r'[^\w\s+#./-]', '', skill)
    skill = re.sub(r'\s+', ' ', skill)
    # Normalize common British spellings to American so 'visualisation'
    # == 'visualization' etc. work WITHOUT any alias dictionary entries.
    if 'isation' in skill:
        skill = skill.replace('isation', 'ization')
    return skill.strip()


def _edit_ratio(a, b):
    """Similarity ratio between two strings (0-1). 1.0 = identical."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def _tokens_close(a, b):
    """
    True if two skill tokens are probably the same word with a small
    spelling difference (typo, plural, regional variant).

    Rules (precision-first):
      - length difference must be <= 2
      - very high similarity (>= 0.90) always accepts, e.g.
        'visualisation'~'visualization', 'kubernets'~'kubernetes'
      - moderate similarity (>= 0.85) needs first AND last char to match,
        so look-alikes like 'flask'~'flash' stay rejected
    """
    if a == b:
        return True

    candidates = [(a, b)]
    sa, sb = a.rstrip('s'), b.rstrip('s')
    if sa and sb and (sa, sb) != (a, b):
        candidates.append((sa, sb))

    for x, y in candidates:
        if abs(len(x) - len(y)) > 2:
            continue
        ratio = _edit_ratio(x, y)
        if ratio >= 0.90:
            return True
        if ratio >= 0.85 and x[0] == y[0] and x[-1] == y[-1]:
            return True
    return False


def _skill_aliases():
    """Return a dict of common standard abbreviations/synonyms for O(1) matching."""
    return {
        'ml': ['machine learning'],
        'machine learning': ['ml'],
        'ai': ['artificial intelligence'],
        'artificial intelligence': ['ai'],
        'nlp': ['natural language processing'],
        'natural language processing': ['nlp'],
        'react': ['react.js', 'reactjs', 'react js'],
        'react.js': ['react', 'reactjs', 'react js'],
        'reactjs': ['react', 'react.js', 'react js'],
        'node': ['node.js', 'nodejs', 'node js'],
        'node.js': ['node', 'nodejs', 'node js'],
        'nodejs': ['node', 'node.js', 'node js'],
        'vue': ['vue.js', 'vuejs', 'vue js'],
        'vue.js': ['vue', 'vuejs', 'vue js'],
        'vuejs': ['vue', 'vue.js', 'vue js'],
        'next.js': ['nextjs', 'next js'],
        'nextjs': ['next.js', 'next js'],
        'express': ['express.js', 'expressjs'],
        'express.js': ['express', 'expressjs'],
        'expressjs': ['express', 'express.js'],
        'postgresql': ['postgres', 'psql'],
        'postgres': ['postgresql', 'psql'],
        'psql': ['postgresql', 'postgres'],
        'js': ['javascript'],
        'javascript': ['js'],
        'ts': ['typescript'],
        'typescript': ['ts'],
        'c++': ['cpp', 'c plus plus'],
        'cpp': ['c++', 'c plus plus'],
        'c#': ['csharp', 'c sharp'],
        'csharp': ['c#', 'c sharp'],
        'golang': ['go'],
        'go': ['golang'],
        'k8s': ['kubernetes'],
        'kubernetes': ['k8s'],
        'drf': ['django rest framework'],
        'django rest framework': ['drf'],
        'rest api': ['restful api', 'rest', 'restful'],
        'restful': ['rest api', 'rest'],
        'rest': ['rest api', 'restful'],
        'html5': ['html'],
        'html': ['html5'],
        'css3': ['css'],
        'css': ['css3'],
        'tailwind css': ['tailwind'],
        'tailwind': ['tailwind css'],
        'power bi': ['powerbi', 'power bi desktop'],
        'powerbi': ['power bi'],
        'excel': ['ms excel', 'microsoft excel'],
        'ms excel': ['excel', 'microsoft excel'],
        'microsoft excel': ['excel', 'ms excel'],
        'aws': ['amazon web services'],
        'amazon web services': ['aws'],
        'gcp': ['google cloud', 'google cloud platform'],
        'google cloud': ['gcp', 'google cloud platform'],
        'azure': ['microsoft azure'],
        'microsoft azure': ['azure'],
        'ci/cd': ['cicd', 'ci cd', 'continuous integration', 'continuous deployment'],
        'cicd': ['ci/cd', 'ci cd'],
        'ci cd': ['ci/cd', 'cicd'],
        'api': ['rest api', 'restful api', 'web api'],
        'web scraping': ['scraping', 'web scraper'],
        'beautifulsoup': ['beautiful soup', 'bs4'],
        'beautiful soup': ['beautifulsoup', 'bs4'],
        'bs4': ['beautifulsoup', 'beautiful soup'],
        'selenium': ['selenium webdriver'],
        'scikit-learn': ['sklearn', 'scikit learn'],
        'sklearn': ['scikit-learn', 'scikit learn'],
        'tensorflow': ['tf'],
        'tf': ['tensorflow'],
        'pytorch': ['torch'],
        'torch': ['pytorch'],
        'opencv': ['cv2', 'open cv'],
        'cv2': ['opencv', 'open cv'],
        'llm': ['large language model', 'large language models'],
        'large language model': ['llm', 'large language models'],
        'large language models': ['llm', 'large language model'],
        'openai': ['open ai', 'chatgpt'],
        'chatgpt': ['openai'],
        'langchain': ['lang chain'],
        'hugging face': ['huggingface', 'hf'],
        'huggingface': ['hugging face', 'hf'],
        'git': ['github', 'gitlab'],
        'docker': ['docker container', 'containers'],
    }


def _semantic_skill_matches(skill, resume_chunks, threshold=0.76):
    """
    Zero-Shot AI Semantic Vector Matching using Sentence-Transformers.
    Computes embedding cosine similarity between the required skill and resume sentences.
    Works for ANY new word, technology, tool, or phrasing without requiring a dictionary!
    """
    if not resume_chunks:
        return False
    try:
        model = _get_sentence_model()
        if model is None:
            return False
        skill_emb = model.encode([skill])
        chunk_embs = model.encode(resume_chunks)
        sims = cosine_similarity(skill_emb, chunk_embs)[0]
        return bool(np.max(sims) >= threshold)
    except Exception:
        return False


def _skill_matches(skill, resume_lower, resume_chunks=None):
    """
    Check if a skill matches the resume text using multiple dynamic strategies:
    1. Exact word-boundary match (Works for ANY word)
    2. Alias/synonym match
    3. Partial token match (for multi-word skills)
    4. Fuzzy prefix/suffix match (e.g. React -> ReactJS)
    5. Typo-tolerant edit-distance match (e.g. kubernets -> kubernetes)
    6. Zero-Shot AI Embedding Semantic Cosine Matching (Any new tech or conceptual match)
    """
    skill_norm = _normalize_skill(skill)
    if not skill_norm:
        return False

    # Strategy 1: Exact word-boundary match
    escaped = re.escape(skill_norm)
    if re.search(rf'\b{escaped}\b', resume_lower):
        return True

    # Strategy 2: Common Alias/synonym match
    aliases = _skill_aliases()
    if skill_norm in aliases:
        for alias in aliases[skill_norm]:
            alias_norm = _normalize_skill(alias)
            if not alias_norm:
                continue
            escaped_alias = re.escape(alias_norm)
            if re.search(rf'\b{escaped_alias}\b', resume_lower):
                return True

    # Strategy 3: Partial token match for multi-word skills
    if ' ' in skill_norm:
        tokens = skill_norm.split()
        significant = [t for t in tokens if t not in ('and', 'the', 'of', 'for', 'with', 'in', 'on', 'at')]
        if significant and all(
            re.search(rf'\b{re.escape(t)}\b', resume_lower) for t in significant
        ):
            return True

    # Strategy 4: Fuzzy match for single-word skills (prefix / suffix)
    if len(skill_norm) >= 4 and ' ' not in skill_norm:
        if re.search(rf'\b{re.escape(skill_norm)}[\w.#+-]*', resume_lower):
            return True
        if re.search(rf'\b[\w.#+-]*{re.escape(skill_norm)}\b', resume_lower):
            return True

    # Strategy 5: Typo-tolerant matching (Edit-distance similarity)
    words = set(re.findall(r'[a-z][a-z0-9+#./-]{2,}', resume_lower))
    if words:
        skill_tokens = [t for t in skill_norm.split() if len(t) >= 4]
        if skill_tokens and all(
            any(_tokens_close(t, w) for w in words) for t in skill_tokens
        ):
            return True

    # Strategy 6: Zero-Shot AI Embedding Semantic Vector Matching (Any new word / concept)
    if resume_chunks:
        if _semantic_skill_matches(skill, resume_chunks):
            return True

    return False


def skill_match_score(required_skills, resume_text):
    """
    Compute skill match percentage.

    Uses fuzzy matching, word boundaries, alias matching, and zero-shot AI
    semantic vector matching to accurately identify present skills.

    Args:
        required_skills (list): List of required skills.
        resume_text (str): Extracted resume text.

    Returns:
        tuple: (matched_skills, missing_skills, skill_score)
    """
    resume_lower = resume_text.lower()
    resume_chunks = [
        s.strip() for s in re.split(r'[.\n•*|;]+', resume_text)
        if len(s.strip()) > 3
    ][:60]

    matched = []
    missing = []

    for skill in required_skills:
        if _skill_matches(skill, resume_lower, resume_chunks=resume_chunks):
            matched.append(skill)
        else:
            missing.append(skill)

    if not required_skills:
        return [], [], 0.0

    skill_score = (len(matched) / len(required_skills)) * 100.0
    return matched, missing, skill_score


def compute_experience_score(required_years, candidate_years):
    """
    Calculate experience match score (0-100%).
    If required_years is 0, full marks (100%) given.
    If candidate meets or exceeds requirement, 100%.
    Otherwise proportional to required years.
    """
    if not required_years or required_years <= 0:
        return 100.0
    if not candidate_years or candidate_years <= 0:
        return 50.0  # Baseline partial credit if unparsed
    if candidate_years >= required_years:
        return 100.0
    return round((candidate_years / required_years) * 100.0, 2)


def compute_match(job, resume_text, candidate_exp=0.0):
    """
    Compute overall match score combining semantic, skill, TF-IDF, and experience scores.

    Balanced Scoring Matrix:
    - 40% Semantic Similarity (Meaning & context match via Sentence-Transformers)
    - 40% Skill Match (Explicit required skills & aliases)
    - 20% TF-IDF & Role N-gram Term Coverage
    If the job specifies required experience years, experience score contributes proportionally.

    Returns:
        dict: {
            'overall_score': float (0-100),
            'tfidf_score': float (0-100),
            'semantic_score': float (0-100),
            'skill_score': float (0-100),
            'experience_score': float (0-100),
            'matched_skills': list,
            'missing_skills': list,
        }
    """
    job_text = f"{job.title}. {job.description}"

    tfidf = tfidf_similarity(job_text, resume_text) * 100.0
    semantic = semantic_similarity(job_text, resume_text) * 100.0
    req_skills = job.skills_list()
    matched, missing, skill_score = skill_match_score(req_skills, resume_text)

    req_exp = getattr(job, 'experience_required', 0)
    exp_score = compute_experience_score(req_exp, candidate_exp)

    if req_skills:
        if req_exp > 0:
            # 35% semantic, 35% skills, 15% tfidf, 15% experience
            overall = (0.35 * semantic) + (0.35 * skill_score) + (0.15 * tfidf) + (0.15 * exp_score)
        else:
            # 40% semantic, 40% skills, 20% tfidf
            overall = (0.40 * semantic) + (0.40 * skill_score) + (0.20 * tfidf)
    else:
        # Fallback when no explicit required skills exist: 60% semantic, 40% TF-IDF
        overall = (0.60 * semantic) + (0.40 * tfidf)

    overall = max(0.0, min(100.0, overall))

    return {
        'overall_score': round(overall, 2),
        'tfidf_score': round(tfidf, 2),
        'semantic_score': round(semantic, 2),
        'skill_score': round(skill_score, 2),
        'experience_score': round(exp_score, 2),
        'matched_skills': matched,
        'missing_skills': missing,
    }