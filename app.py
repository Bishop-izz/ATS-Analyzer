from flask import Flask, render_template, request
import pdfplumber
import docx
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import requests

app = Flask(__name__)

# Ensure static folder exists
if not os.path.exists("static"):
    os.makedirs("static")

# -----------------------------------
# JOB ROLE DATABASE
# -----------------------------------

JOB_ROLES = {
    "AI Engineer": {
        "core": ["python", "machine learning", "deep learning", "tensorflow", "pytorch"],
        "secondary": ["nlp", "computer vision", "keras", "neural networks"]
    },
    "Data Scientist": {
        "core": ["python", "machine learning", "deep learning", "statistics", "pandas", "numpy"],
        "secondary": ["tensorflow", "pytorch", "nlp", "data visualization", "sql"]
    },
    "Frontend Developer": {
        "core": ["html", "css", "javascript", "react", "responsive design"],
        "secondary": ["bootstrap", "tailwind", "vue", "ui/ux", "api"]
    },
    "Backend Developer": {
        "core": ["python", "java", "node", "sql", "api", "database"],
        "secondary": ["django", "flask", "spring", "mongodb", "authentication"]
    },
    "Data Analyst": {
        "core": ["python", "sql", "excel", "statistics", "power bi", "tableau"],
        "secondary": ["pandas", "numpy", "data visualization"]
    },
    "Full Stack Developer": {
        "core": ["html", "css", "javascript", "react", "node", "mongodb"],
        "secondary": ["express", "api", "git", "bootstrap"]
    },
    "DevOps Engineer": {
        "core": ["docker", "kubernetes", "aws", "jenkins", "linux"],
        "secondary": ["terraform", "ansible", "ci/cd"]
    },
    "Mobile Developer": {
        "core": ["flutter", "react native", "android", "ios"],
        "secondary": ["firebase", "dart", "swift"]
    },
    "Cyber Security Engineer": {
        "core": ["network security", "penetration testing", "ethical hacking"],
        "secondary": ["kali linux", "siem", "firewalls"]
    },
    "Cloud Engineer": {
        "core": ["aws", "azure", "gcp", "cloud architecture"],
        "secondary": ["docker", "kubernetes", "devops"]
    },
    "Software Engineer": {
        "core": ["python", "java", "c++", "data structures", "algorithms"],
        "secondary": ["git", "oop", "software development"]
    }
}

# -----------------------------------
# SYNONYMS
# -----------------------------------

SYNONYMS = {
    "artificial intelligence": ["ai"],
    "machine learning": ["ml"],
    "deep learning": ["dl"],
    "ci/cd": ["continuous integration"],
    "javascript": ["js"],
    "kubernetes": ["k8s"]
}

# -----------------------------------
# TEXT EXTRACTION (UPDATED WITH OCR API)
# -----------------------------------

def extract_text(file):
    filename = file.filename.lower()

    try:
        # PDF
        if filename.endswith('.pdf'):
            with pdfplumber.open(file) as pdf:
                text = " ".join(page.extract_text() or "" for page in pdf.pages)
                return text.strip()

        # DOCX
        elif filename.endswith('.docx'):
            doc = docx.Document(file)
            text = " ".join(para.text for para in doc.paragraphs)
            return text.strip()

        # TXT
        elif filename.endswith('.txt'):
            return file.read().decode('utf-8').strip()

        # IMAGE FILES → OCR.Space API
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')):

            api_key = os.getenv("OCR_SPACE_API_KEY")

            payload = {
                'apikey': api_key,
                'language': 'eng',
                'isOverlayRequired': False
            }

            files = {
                'file': (file.filename, file.stream, file.mimetype)
            }

            response = requests.post(
                'https://api.ocr.space/parse/image',
                files=files,
                data=payload
            )

            result = response.json()

            if result.get("IsErroredOnProcessing"):
                print("OCR Error:", result.get("ErrorMessage"))
                return ""

            parsed_text = result["ParsedResults"][0]["ParsedText"]
            return parsed_text.strip()

    except Exception as e:
        print("Error extracting text:", e)

    return ""

# -----------------------------------
# HELPERS
# -----------------------------------

def match_skill(skill, text):
    if skill in text:
        return True
    if skill in SYNONYMS:
        for synonym in SYNONYMS[skill]:
            if synonym in text:
                return True
    return False


def generate_skill_chart(matched_count, total_skill_count):
    skill_percentage = (matched_count / total_skill_count) * 100 if total_skill_count > 0 else 0
    remaining_percentage = 100 - skill_percentage

    labels = ['Skill Match %', 'Remaining %']
    values = [skill_percentage, remaining_percentage]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, values)

    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height,
                 f'{height:.1f}%', ha='center', va='bottom')

    plt.ylim(0, 100)
    plt.title('Skill Match Percentage')
    plt.tight_layout()

    chart_path = os.path.join('static', 'skill_chart.png')
    plt.savefig(chart_path, dpi=300)
    plt.close()

    return chart_path


def calculate_score(resume_text, job_role):
    job_data = JOB_ROLES.get(job_role)
    if not job_data:
        return 0, [], []

    resume_text = resume_text.lower()

    core_skills = job_data["core"]
    secondary_skills = job_data["secondary"]

    matched = []
    missing = []

    for skill in core_skills + secondary_skills:
        if match_skill(skill, resume_text):
            matched.append(skill)
        else:
            missing.append(skill)

    total_skills = len(core_skills) + len(secondary_skills)
    score = (len(matched) / total_skills) * 100 if total_skills > 0 else 0

    return round(score, 2), matched, missing


# -----------------------------------
# ROUTES
# -----------------------------------

@app.route('/')
def home():
    return render_template("index.html", job_roles=JOB_ROLES.keys())


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return "No file uploaded"

    file = request.files['resume']
    job_role = request.form.get('job_role')

    if file.filename == '':
        return "No selected file"

    if job_role not in JOB_ROLES:
        return "Invalid job role selected"

    resume_text = extract_text(file)

    if not resume_text:
        return "Could not extract text from file"

    score, matched, missing = calculate_score(resume_text, job_role)

    total_skills = len(JOB_ROLES[job_role]["core"]) + len(JOB_ROLES[job_role]["secondary"])
    chart_path = generate_skill_chart(len(matched), total_skills)

    return render_template(
        "result.html",
        score=score,
        matched_skills=matched,
        missing_skills=missing,
        chart_path=chart_path
    )


if __name__ == '__main__':
    app.run(debug=True)
