from flask import Flask, render_template, request
import pdfplumber
import docx
import pytesseract
from PIL import Image
import re
import spacy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

app = Flask(__name__)

# Ensure static folder exists
if not os.path.exists("static"):
    os.makedirs("static")

# Load SpaCy model
nlp = spacy.load("en_core_web_sm")

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
# TEXT EXTRACTION
# -----------------------------------
def extract_text(file):
    filename = file.filename.lower()
    try:
        if filename.endswith('.pdf'):
            with pdfplumber.open(file) as pdf:
                return " ".join(page.extract_text() or "" for page in pdf.pages)

        elif filename.endswith('.docx'):
            doc = docx.Document(file)
            return " ".join(para.text for para in doc.paragraphs)

        elif filename.endswith('.txt'):
            return file.read().decode('utf-8')

        elif filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')):
            image = Image.open(file)
            return pytesseract.image_to_string(image)

    except Exception as e:
        print("Error extracting text:", e)

    return ""

# -----------------------------------
# HELPERS
# -----------------------------------
def detect_experience(text):
    matches = re.findall(r'(\d+)\+?\s+years', text.lower())
    return max([int(x) for x in matches]) if matches else 0

def detect_education(text):
    degrees = ["bachelor", "master", "phd", "b.tech", "m.tech"]
    return [deg for deg in degrees if deg in text.lower()]

def detect_projects(text):
    return "project" in text.lower()

def match_skill(skill, text):
    if skill in text:
        return True
    if skill in SYNONYMS:
        for synonym in SYNONYMS[skill]:
            if synonym in text:
                return True
    return False

# -----------------------------------
# MODERN SKILL PERCENTAGE CHART
# -----------------------------------
def generate_skill_chart(matched_count, total_skill_count):
    skill_percentage = (matched_count / total_skill_count) * 100 if total_skill_count > 0 else 0
    remaining_percentage = 100 - skill_percentage

    labels = ['Skill Match %', 'Remaining %']
    values = [skill_percentage, remaining_percentage]

    plt.figure(figsize=(8, 5))
    colors = ['#4CAF50', '#E0E0E0']

    bars = plt.bar(labels, values, color=colors)
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f'{height:.1f}%',
            ha='center',
            va='bottom',
            fontsize=12,
            fontweight='bold'
        )

    plt.ylim(0, 100)
    plt.title('Skill Match Percentage', fontsize=16, fontweight='bold')
    plt.ylabel('Percentage')
    plt.tight_layout()

    chart_path = os.path.join('static', 'skill_chart.png')
    plt.savefig(chart_path, dpi=300)
    plt.close()

    return chart_path

# -----------------------------------
# SCORING SYSTEM
# -----------------------------------
def calculate_score(resume_text, job_role):
    job_data = JOB_ROLES.get(job_role)
    if not job_data:
        return 0, [], [], 0, [], {}

    resume_text = resume_text.lower()

    core_skills = job_data["core"]
    secondary_skills = job_data["secondary"]

    matched = []
    missing = []

    earned_skill_points = 0
    total_skill_points = (len(core_skills) * 10) + (len(secondary_skills) * 5)

    for skill in core_skills:
        if match_skill(skill, resume_text):
            earned_skill_points += 10
            matched.append(skill)
        else:
            missing.append(skill)

    for skill in secondary_skills:
        if match_skill(skill, resume_text):
            earned_skill_points += 5
            matched.append(skill)
        else:
            missing.append(skill)

    skill_percentage = (earned_skill_points / total_skill_points) * 100 if total_skill_points > 0 else 0

    return round(skill_percentage, 2), matched, missing, 0, [], {}

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

    # Selected role analysis
    score, matched, missing, _, _, _ = calculate_score(resume_text, job_role)

    total_skills = len(JOB_ROLES[job_role]["core"]) + len(JOB_ROLES[job_role]["secondary"])
    chart_path = generate_skill_chart(len(matched), total_skills)

    # -------- MULTI ROLE COMPARISON --------
    role_comparison = []

    for role in JOB_ROLES.keys():
        role_score, _, _, _, _, _ = calculate_score(resume_text, role)

        role_comparison.append({
            "role": role,
            "score": role_score
        })

    role_comparison = sorted(role_comparison, key=lambda x: x["score"], reverse=True)

    top_roles = role_comparison[:5]
    best_role = top_roles[0]

    return render_template(
        "result.html",
        score=score,
        matched_skills=matched,
        missing_skills=missing,
        chart_path=chart_path,
        top_roles=top_roles,
        best_role=best_role
    )

# -----------------------------------
if __name__ == '__main__':
    app.run(debug=True)