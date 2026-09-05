"""End-to-end pipeline test: real PDF -> extraction -> matching."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'screening.settings')
django.setup()

from django.conf import settings
from core.models import Job
from core.utils.pdf_extractor import extract_text_from_pdf

text, best = '', ''
for root, dirs, files in os.walk(settings.MEDIA_ROOT):
    for f in files:
        if f.lower().endswith('.pdf'):
            t = extract_text_from_pdf(os.path.join(root, f))
            if len(t) > len(text):
                text, best = t, f

print('best pdf:', best, '| chars:', len(text))

j = Job(title='Data Scientist',
        description='Role for AI/ML work.\nSkills: Python, SQL, Machine Learning, '
                    'Data Visualization, Deep Learning, NLP, Django')
print('parsed skills:', j.skills_list())

from core.utils.matcher import compute_match
r = compute_match(j, text)
print('OVERALL:', r['overall_score'], '| skill:', r['skill_score'],
      '| semantic:', r['semantic_score'], '| tfidf:', r['tfidf_score'])
print('matched:', r['matched_skills'])
print('missing:', r['missing_skills'])

# Email generation test
from core.utils.email_generator import generate_email
e = generate_email(candidate_name='Test', job_title='DS', company_name='X',
                   status='selected', score=r['overall_score'], explanation='ok')
print('email generated:', bool(e.get('subject')), '| body len:', len(e.get('body', '')))

# Reports export test
import pandas as pd
df = pd.DataFrame([{'cand': 't', 'score': r['overall_score']}])
print('pandas export OK:', len(df) == 1)