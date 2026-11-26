
import streamlit as st
import json
import urllib.request
import urllib.error
import re
import math

from pypdf import PdfReader
from io import BytesIO
from xml.sax.saxutils import escape

import plotly.graph_objects as go

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER


# -----------------------------------
# PAGE CONFIGURATION
# -----------------------------------

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide"
)


# -----------------------------------
# HEADER
# -----------------------------------

st.title("📄 AI Resume Analyzer")
st.markdown("### Your personal AI-powered resume reviewer")
st.caption("Upload a PDF resume, compare it with a job description, review evidence, and download an analysis report.")

st.divider()


# -----------------------------------
# SIDEBAR
# -----------------------------------

with st.sidebar:

    st.title("📄 Resume Analyzer")
    st.write("AI-powered career assistant")

    st.divider()

    st.subheader("Features")

    st.write("📌 Resume Analysis")
    st.write("🎯 ATS Compatibility")
    st.write("🛠️ Skill Gap Detection")
    st.write("💡 Improvement Suggestions")

    st.divider()

    st.caption("Powered by Llama 3.2")
    st.caption("Runs locally using Ollama")
    st.caption("Model: llama3.2:3b")


# -----------------------------------
# DASHBOARD
# -----------------------------------

st.subheader("🚀 Start Your Resume Analysis")

col1, col2, col3 = st.columns(3)

with col1:
    st.info("📄 Resume Scanner\n\nExtract resume information")

with col2:
    st.info("🎯 ATS Matcher\n\nCompare job requirements")

with col3:
    st.info("💡 AI Suggestions\n\nDiscover improvement areas")

st.divider()


# -----------------------------------
# INPUTS
# -----------------------------------

uploaded_file = st.file_uploader(
    "Upload your resume (PDF)",
    type=["pdf"]
)

job_description = st.text_area(
    "Paste the job description",
    height=200
)


# -----------------------------------
# SKILL RECOGNITION DATABASE
# -----------------------------------

SKILL_DATABASE = {
    "Python": ["python", "python3"],
    "Java": ["java"],
    "C++": ["c++", "cpp"],
    "JavaScript": ["javascript", "java script", "js"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3"],
    "React.js": ["react.js", "reactjs", "react js"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo db"],
    "SQL": ["sql", "structured query language", "sql queries"],
    "Machine Learning": ["machine learning", "machine-learning", "ml"],
    "Artificial Intelligence": ["artificial intelligence"],
    "Scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Git": ["git"],
    "GitHub": ["github"],
    "VS Code": ["vs code", "visual studio code"],
    "Flask": ["flask"],
    "Django": ["django"],
    "REST APIs": ["rest api", "rest apis", "restful api", "restful apis", "restful services", "rest web services"],
    "OOP": ["object-oriented programming", "object oriented programming", "object-oriented", "object oriented", "oop"],
    "Data Structures and Algorithms": [
        "data structures and algorithms",
        "data structures",
        "algorithms",
        "dsa"
    ],
    "Problem Solving": ["problem solving", "problem-solving"],
    "Debugging": ["debugging", "debug"],
    "APIs": ["apis", "api"],
    "Communication": ["communication"],
    "Teamwork": ["teamwork"],
    "Time Management": ["time management"],
    "Critical Thinking": ["critical thinking"]
}


def contains_skill(text, skill):

    text = text.lower()

    variations = SKILL_DATABASE.get(skill, [skill.lower()])

    for variation in variations:

        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(variation)
            + r"(?![a-z0-9])"
        )

        if re.search(pattern, text):
            return True

    return False


def extract_skills(text):

    found_skills = []

    for skill in SKILL_DATABASE:

        if contains_skill(text, skill):
            found_skills.append(skill)

    return found_skills


# -----------------------------------
# SKILL EVIDENCE MATCHING
# -----------------------------------

def get_skill_evidence(resume_text, skill):

    lines = resume_text.splitlines()

    matching_lines = []

    for line in lines:

        if contains_skill(line, skill):

            cleaned = line.strip()

            if cleaned:
                matching_lines.append(cleaned)

    return matching_lines


def normalize_line(line):
    """Clean PDF extraction artifacts and normalize whitespace."""
    return re.sub(r"\s+", " ", line.replace("\x7f", " ")).strip()


def get_section_name(line):
    """
    Detect resume section headings, including headings followed by a colon
    or followed by content on the same line.
    """
    cleaned = normalize_line(line).lower()
    cleaned = re.sub(r"^[\W_]+|[\W_]+$", "", cleaned)

    heading_map = {
        "technical skills": "technical_skills",
        "skills": "technical_skills",
        "core competencies": "technical_skills",
        "technologies": "technical_skills",
        "technical expertise": "technical_skills",
        "soft skills": "soft_skills",
        "projects": "projects",
        "project experience": "projects",
        "education": "education",
        "internship": "experience",
        "internships": "experience",
        "experience": "experience",
        "work experience": "experience",
        "professional experience": "experience",
        "certifications": "certifications",
        "certificates": "certifications",
        "languages": "other",
        "professional summary": "summary",
        "summary": "summary",
        "profile": "summary",
        "objective": "summary",
    }

    if cleaned in heading_map:
        return heading_map[cleaned]

    # Handle headings like "Soft Skills: Problem Solving | Teamwork".
    for heading, section in sorted(heading_map.items(), key=lambda item: len(item[0]), reverse=True):
        if re.match(r"^" + re.escape(heading) + r"\s*[:\-|]", cleaned):
            return section

    return None


def get_skill_status(resume_text, skill):
    """
    Evidence levels:
    - Demonstrated: found in a project or work/internship experience section.
    - Listed: found in a technical or soft skills section.
    - Mentioned - Proficiency Unverified: found only in summary, education,
      certifications, or another non-experience section.
    - Partially Matched: MySQL appears when SQL is required.
    - Not Found: no evidence found.
    """
    current_section = "other"
    skill_section_evidence = []
    demonstrated_evidence = []
    mentioned_evidence = []
    partial_evidence = []

    for raw_line in resume_text.splitlines():
        line = normalize_line(raw_line)
        if not line:
            continue

        heading = get_section_name(line)
        if heading:
            current_section = heading

            # If a heading and its content share one line, inspect the content
            # after the heading instead of discarding the entire line.
            lower_line = line.lower()
            heading_match = None
            for heading_text in sorted(
                [
                    "technical skills", "skills", "core competencies",
                    "technologies", "technical expertise", "soft skills",
                    "projects", "project experience", "education",
                    "internship", "internships", "experience",
                    "work experience", "professional experience",
                    "certifications", "certificates", "languages",
                    "professional summary", "summary", "profile", "objective"
                ],
                key=len,
                reverse=True
            ):
                match = re.match(
                    r"^" + re.escape(heading_text) + r"\s*[:\-|]\s*(.+)$",
                    lower_line
                )
                if match:
                    heading_match = (heading_text, match.end())
                    break

            if heading_match:
                line = line[heading_match[1]:].strip()
                if not line:
                    continue
            else:
                continue

        # MySQL is related to SQL, but is not an exact SQL demonstration.
        if skill == "SQL" and contains_skill(line, "MySQL") and not contains_skill(line, "SQL"):
            partial_evidence.append(line)
            continue

        if not contains_skill(line, skill):
            continue

        if current_section in {"projects", "experience"}:
            demonstrated_evidence.append(line)
        elif current_section in {"technical_skills", "soft_skills"}:
            skill_section_evidence.append(line)
        else:
            mentioned_evidence.append(line)

    if demonstrated_evidence:
        return "Demonstrated", demonstrated_evidence[0]

    if skill_section_evidence:
        return "Listed - Proficiency Unverified", skill_section_evidence[0]

    if partial_evidence:
        return "Partially Matched", partial_evidence[0]

    if mentioned_evidence:
        return "Mentioned - Proficiency Unverified", mentioned_evidence[0]

    return "Not Found", ""


# -----------------------------------
# EXTRACT REQUIRED AND PREFERRED SKILLS
# -----------------------------------

def normalize_jd_heading(line):
    """Normalize Markdown/bulleted section headings from job descriptions."""
    value = line.strip().lower()
    value = re.sub(r"^\s*#+\s*", "", value)
    value = value.replace("**", "").replace("__", "").replace("`", "")
    value = re.sub(r"^\s*[-*•]+\s*", "", value)
    value = re.sub(r"\s*:\s*$", "", value)
    return re.sub(r"\s+", " ", value).strip()


def extract_job_requirements(job_description):
    """
    Read the job description line by line so headings still work when they
    are Markdown-formatted (for example, '## **Preferred Skills:**').
    Skills before a preferred heading are required; skills inside the
    preferred section are preferred until the next major section.
    """
    preferred_headings = {
        "preferred skills", "preferred qualifications",
        "nice to have", "good to have", "bonus skills",
        "desired skills", "additional skills"
    }
    stop_headings = {
        "responsibilities", "key responsibilities", "what you will do",
        "what you'll do", "job description", "qualifications",
        "required qualifications", "about the role", "about you",
        "who you are", "benefits", "what we offer", "requirements"
    }

    required_lines = []
    preferred_lines = []
    current_section = "required"

    for line in job_description.splitlines():
        heading = normalize_jd_heading(line)

        if heading in preferred_headings:
            current_section = "preferred"
            continue

        if heading in stop_headings:
            current_section = "stop"
            continue

        if current_section == "required":
            required_lines.append(line)
        elif current_section == "preferred":
            preferred_lines.append(line)

    required_text = "\n".join(required_lines)
    preferred_text = "\n".join(preferred_lines)

    required_skills = []
    preferred_skills = []

    for skill in SKILL_DATABASE:
        in_required = contains_skill(required_text, skill)
        in_preferred = contains_skill(preferred_text, skill)

        if in_required:
            required_skills.append(skill)
        elif in_preferred:
            preferred_skills.append(skill)

    return required_skills, preferred_skills


def build_skill_comparison(resume_text, job_description):

    required, preferred = extract_job_requirements(
        job_description
    )

    required_results = []
    preferred_results = []

    for skill in required:

        status, evidence = get_skill_status(
            resume_text,
            skill
        )

        required_results.append({
            "skill": skill,
            "status": status,
            "evidence": evidence
        })

    for skill in preferred:

        status, evidence = get_skill_status(
            resume_text,
            skill
        )

        preferred_results.append({
            "skill": skill,
            "status": status,
            "evidence": evidence
        })

    return required_results, preferred_results


# -----------------------------------
# AI ANALYSIS
# -----------------------------------

def analyze_resume(resume_text, job_description):

    prompt = f"""
You are a professional resume analysis assistant.

Analyze the resume and job description.

IMPORTANT:
Python has already performed skill matching.
Do not calculate or modify any ATS score.
Do not generate skill classifications.

Return ONLY valid JSON.

Use this exact structure:

{{
    "projects": [
        {{
            "name": "Project name",
            "description": "Evidence from resume"
        }}
    ],
    "education": [
        {{
            "qualification": "Degree",
            "evidence": "Education details from resume"
        }}
    ],
    "experience": [
        {{
            "role": "Job or internship title",
            "evidence": "Relevant responsibilities stated in resume"
        }}
    ],
    "strengths": [
        "Evidence-based strength"
    ],
    "weaknesses": [
        "Genuine resume weakness"
    ],
    "suggestions": [
        "Specific improvement suggestion"
    ],
    "recommendation": "Overall candidate suitability"
}}

RULES:

1. Only include projects actually mentioned in the resume.
2. Only include education actually mentioned in the resume.
3. Only include jobs or internships actually mentioned in the resume.
4. Do not invent experience, dates, skills, metrics, or qualifications.
5. Mention genuine gaps against the job description.
6. Provide specific, actionable improvement suggestions.
7. If a section has no evidence, return an empty array for it.
8. Keep descriptions concise and grounded in the resume.
9. Return valid JSON only.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}
"""

    data = {
        "model": "llama3.2:3b",
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    request = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=900
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    report = json.loads(result.get("response", "{}"))

    if not isinstance(report, dict):
        raise ValueError("The AI response was not a JSON object.")

    expected_lists = [
        "projects", "education", "experience",
        "strengths", "weaknesses", "suggestions"
    ]
    for key in expected_lists:
        if not isinstance(report.get(key), list):
            report[key] = []
        else:
            # Small local models sometimes return empty strings or nulls.
            report[key] = [
                item for item in report[key]
                if (isinstance(item, dict) and any(str(v).strip() for v in item.values() if v is not None))
                or (isinstance(item, str) and item.strip())
            ]

    if not isinstance(report.get("recommendation"), str):
        report["recommendation"] = "No recommendation was generated."

    return report


# -----------------------------------
# SCORE CALCULATION
# -----------------------------------

def calculate_score(report):

    status_points = {
        "Demonstrated": 1.0,
        "Partially Matched": 0.5,
        "Listed - Proficiency Unverified": 0.25,
        "Mentioned - Proficiency Unverified": 0.15,
        "Not Found": 0.0
    }

    required = report.get("required_skills", [])
    preferred = report.get("preferred_skills", [])

    def category_score(skills, maximum):

        if not skills:
            return 0

        earned = sum(
            status_points.get(item.get("status"), 0)
            for item in skills
        )

        return (earned / len(skills)) * maximum

    required_score = category_score(required, 60)
    preferred_score = category_score(preferred, 15)

    projects = report.get("projects", [])
    experience = report.get("experience", [])

    valid_projects = [
        p for p in projects
        if isinstance(p, dict)
        and str(p.get("name", "")).strip()
        and str(p.get("description", "")).strip()
    ]

    valid_experience = [
        item for item in experience
        if isinstance(item, dict)
        and str(item.get("role", "")).strip()
        and str(item.get("evidence", "")).strip()
    ]

    # Up to two verified resume entries (projects or work/internship roles)
    # earn the 15-point category. This is a simple coverage proxy, not a
    # semantic assessment of project quality.
    project_score = min((len(valid_projects) + len(valid_experience)) / 2, 1) * 15

    education = report.get("education", [])

    valid_education = [
        e for e in education
        if isinstance(e, dict)
        and str(e.get("qualification", "")).strip()
        and str(e.get("evidence", "")).strip()
    ]

    education_score = min(len(valid_education), 1) * 10

    # Round each displayed category first, then calculate the total from
    # those exact displayed values so the breakdown and headline agree.
    displayed = {
        "required": round(required_score, 1),
        "preferred": round(preferred_score, 1),
        "projects": round(project_score, 1),
        "education": round(education_score, 1),
    }
    displayed_sum = sum(displayed.values())
    total_score = math.floor(displayed_sum + 0.5)

    return {
        **displayed,
        "total": min(100, total_score)
    }


# -----------------------------------
# CIRCULAR SCORE DISPLAY
# -----------------------------------

def display_ats_score(score):

    if score >= 80:
        color = "#22c55e"
        label = "Excellent Match"

    elif score >= 60:
        color = "#f59e0b"
        label = "Moderate Match"

    else:
        color = "#ef4444"
        label = "Needs Improvement"

    fig = go.Figure(
        data=[
            go.Pie(
                values=[score, 100 - score],
                hole=0.78,
                marker=dict(
                    colors=[color, "#e5e7eb"]
                ),
                textinfo="none",
                hoverinfo="skip",
                sort=False
            )
        ]
    )

    fig.update_layout(
        showlegend=False,
        annotations=[
            dict(
                text=f"<b>{score}%</b>",
                x=0.5,
                y=0.5,
                font=dict(
                    size=36,
                    color=color
                ),
                showarrow=False
            )
        ],
        height=280,
        margin=dict(t=10, b=10, l=10, r=10)
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.markdown(
            f"<h3 style='text-align:center;color:{color};'>"
            f"{label}</h3>",
            unsafe_allow_html=True
        )


# -----------------------------------
# REPORT DISPLAY
# -----------------------------------

def display_report(report, scores):

    st.subheader("📊 Score Breakdown")

    st.write(
        f"Required Skills: {scores['required']} / 60"
    )

    st.write(
        f"Preferred Skills: {scores['preferred']} / 15"
    )

    st.write(
        f"Projects and Experience: {scores['projects']} / 15"
    )

    st.write(
        f"Education and Qualifications: {scores['education']} / 10"
    )

    st.divider()

    st.subheader("1. Required Skills Comparison")

    st.caption("Demonstrated = found in a project or work/internship section; Listed = appears in a skills section; Mentioned = appears in a summary, education or certification but does not prove practical use; Partially Matched = related but non-exact evidence. Equivalent wording is matched only where a clear alias is defined.")

    for item in report.get("required_skills", []):

        st.markdown(
            f"**{item['skill']}** — {item['status']}"
        )

        if item.get("evidence"):
            st.caption(item["evidence"])

    st.divider()

    st.subheader("2. Preferred Skills Comparison")

    for item in report.get("preferred_skills", []):

        st.markdown(
            f"**{item['skill']}** — {item['status']}"
        )

        if item.get("evidence"):
            st.caption(item["evidence"])

    st.divider()

    st.subheader("3. Missing or Unverified Skills")

    missing = []

    for item in (
        report.get("required_skills", [])
        + report.get("preferred_skills", [])
    ):

        if item["status"] in [
            "Not Found",
            "Listed - Proficiency Unverified",
            "Mentioned - Proficiency Unverified"
        ]:

            missing.append(item["skill"])

    if missing:

        for skill in dict.fromkeys(missing):
            st.write(f"• {skill}")

    else:

        st.success(
            "No missing or unverified requirements identified."
        )

    st.divider()

    st.subheader("4. Projects and Experience")

    for project in report.get("projects", []):

        st.markdown(
            f"**{project.get('name', 'Project')}**"
        )

        st.write(project.get("description", ""))

    st.divider()

    st.subheader("5. Work and Internship Experience")

    experience_items = report.get("experience", [])
    if experience_items:
        for item in experience_items:
            st.markdown(f"**{item.get('role', 'Experience')}**")
            st.write(item.get("evidence", ""))
    else:
        st.write("No work or internship experience was identified in the resume.")

    st.divider()

    st.subheader("6. Education and Qualifications")

    for item in report.get("education", []):

        st.markdown(
            f"**{item.get('qualification', 'Qualification')}**"
        )

        st.write(item.get("evidence", ""))

    st.divider()

    st.subheader("7. Resume Strengths")

    for item in report.get("strengths", []):
        if str(item).strip():
            st.write(f"• {item}")

    st.divider()

    st.subheader("8. Resume Weaknesses")

    weaknesses = report.get("weaknesses", [])

    weaknesses = [item for item in weaknesses if str(item).strip()]

    if weaknesses:

        for item in weaknesses:
            st.write(f"• {item}")

    else:

        st.write("No specific weaknesses identified by the AI.")

    st.divider()

    st.subheader("9. Improvement Suggestions")

    suggestions = report.get("suggestions", [])

    suggestions = [item for item in suggestions if str(item).strip()]

    if suggestions:

        for item in suggestions:
            st.write(f"• {item}")

    else:

        st.write("No suggestions returned by the AI.")

    st.divider()

    st.subheader("10. Overall Recommendation")

    st.write(
        report.get(
            "recommendation",
            "No recommendation provided."
        )
    )

    st.caption(
        "This is an illustrative score based on this application's matching rules, "
        "not an official ATS result or a prediction of hiring. Project/experience "
        "points count resume entries and do not judge their quality."
    )


# -----------------------------------
# PDF REPORT GENERATOR
# -----------------------------------

def create_pdf_report(report, scores):

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        spaceAfter=20
    )

    section_heading_style = ParagraphStyle(
        "ReportSectionHeading",
        parent=styles["Heading2"],
        spaceBefore=10,
        spaceAfter=7,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        leading=14,
        spaceAfter=6
    )

    content = []

    content.append(Paragraph("AI Resume Analysis Report", title_style))
    content.append(
        Paragraph(
            f"ATS Compatibility Score: {scores['total']}%",
            styles["Heading1"]
        )
    )
    content.append(Spacer(1, 0.2 * inch))
    content.append(Paragraph("Score Breakdown", styles["Heading2"]))

    for key, label, maximum in [
        ("required", "Required Skills", 60),
        ("preferred", "Preferred Skills", 15),
        ("projects", "Projects and Experience", 15),
        ("education", "Education and Qualifications", 10)
    ]:
        content.append(
            Paragraph(f"{label}: {scores[key]} / {maximum}", body_style)
        )

    sections = [
        ("Required Skills", report.get("required_skills", [])),
        ("Preferred Skills", report.get("preferred_skills", [])),
        ("Projects", report.get("projects", [])),
        ("Work and Internship Experience", report.get("experience", [])),
        ("Education", report.get("education", [])),
        ("Resume Strengths", report.get("strengths", [])),
        ("Resume Weaknesses", report.get("weaknesses", [])),
        ("Improvement Suggestions", report.get("suggestions", []))
    ]

    for heading, items in sections:
        content.append(Spacer(1, 0.12 * inch))
        content.append(Paragraph(escape(heading), section_heading_style))

        valid_items = [
            item for item in (items or [])
            if item is not None and str(item).strip()
        ]

        if not valid_items:
            if heading == "Resume Weaknesses":
                empty_message = "No specific weaknesses identified."
            else:
                empty_message = "No information provided."
            content.append(Paragraph(escape(empty_message), body_style))
            continue

        for item in valid_items:
            if isinstance(item, dict):
                line = " | ".join(
                    str(value).strip()
                    for value in item.values()
                    if value is not None and str(value).strip()
                )
            else:
                line = str(item).strip()

            if line:
                content.append(Paragraph(escape(line), body_style))

    content.append(Spacer(1, 0.18 * inch))
    content.append(
        Paragraph("Overall Recommendation", section_heading_style)
    )

    recommendation = str(report.get("recommendation", "")).strip()
    content.append(
        Paragraph(
            escape(recommendation or "No recommendation provided."),
            body_style
        )
    )

    document.build(content)
    buffer.seek(0)
    return buffer.getvalue()


# -----------------------------------
# ANALYZE BUTTON
# -----------------------------------

if st.button("🔍 Analyze Resume", type="primary"):

    if uploaded_file is None:

        st.warning("Please upload your resume.")

    elif uploaded_file.size > 10 * 1024 * 1024:

        st.warning("Please upload a PDF smaller than 10 MB.")

    elif not job_description.strip():

        st.warning("Please enter a job description.")

    else:

        try:

            pdf_reader = PdfReader(uploaded_file)

            if len(pdf_reader.pages) > 20:
                st.warning("Please upload a resume with 20 pages or fewer.")
                st.stop()

            resume_text = ""

            for page in pdf_reader.pages:
                resume_text += page.extract_text() or ""

            if not resume_text.strip():

                st.warning(
                    "No readable text found in this PDF. If it is a scanned image, run OCR and upload a searchable PDF."
                )

            elif len(resume_text) < 80:

                st.warning("Very little text was extracted. Please check that the PDF contains selectable text.")

            else:

                with st.spinner(
                    "Matching skills and reviewing your resume..."
                ):

                    # Python performs skill matching
                    required_results, preferred_results = (
                        build_skill_comparison(
                            resume_text,
                            job_description
                        )
                    )

                    # Ollama reviews projects, education and suggestions
                    report = analyze_resume(
                        resume_text,
                        job_description
                    )

                    # Add Python-generated skill comparisons
                    report["required_skills"] = required_results
                    report["preferred_skills"] = preferred_results

                    # Python calculates the score
                    scores = calculate_score(report)

                st.success("Resume analysis completed!")

                with st.expander("View extracted resume text"):
                    st.text(resume_text[:12000])
                    if len(resume_text) > 12000:
                        st.caption("Preview limited to the first 12,000 characters.")

                st.divider()

                st.subheader("🎯 Your ATS Compatibility")

                display_ats_score(scores["total"])

                st.divider()

                display_report(report, scores)

                st.divider()

                pdf_file = create_pdf_report(
                    report,
                    scores
                )

                st.download_button(
                    label="📥 Download Analysis Report",
                    data=pdf_file,
                    file_name="Resume_Analysis_Report.pdf",
                    mime="application/pdf"
                )

        except urllib.error.HTTPError as error:
            st.error(f"Ollama returned an HTTP error ({error.code}). Check that the local model server is running.")

        except urllib.error.URLError:
            st.error("Cannot connect to Ollama. Open another terminal and run: ollama serve")

        except TimeoutError:
            st.error("The AI analysis timed out. Try again or use a shorter resume/job description.")

        except json.JSONDecodeError:

            st.error(
                "The AI returned an invalid response. "
                "Please try analyzing again."
            )

        except Exception as error:

            st.error("Analysis could not be completed.")
            st.write(str(error))
