# AI Resume Analyzer

A local Streamlit application that compares a PDF resume with a job description.

## Features

- Extracts selectable text from PDF resumes using pypdf.
- Matches job-description skills against resume evidence.
- Classifies evidence as Demonstrated, Listed, Mentioned, Partially Matched, or Not Found.
- Separates required and preferred skills when the job description uses recognizable headings.
- Uses a local Ollama model (`llama3.2:3b`) to summarize projects, education, work/internship experience, strengths, weaknesses, suggestions, and a recommendation.
- Calculates an illustrative score with a visible category breakdown.
- Exports a PDF analysis report.

## Requirements

- Python 3.10 or newer
- Ollama installed and running
- Ollama model `llama3.2:3b`

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama pull llama3.2:3b
ollama serve
```

Open a second terminal in the project folder, activate the virtual environment, then run:

```powershell
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Important notes

- The application currently expects a text-selectable PDF. Scanned/image-only PDFs need OCR before upload.
- Ollama runs locally; GitHub stores the source code but does not host the local Ollama model.
- Do not commit `.env`, API keys, personal resumes, or generated reports.
- The score is an illustrative rule-based estimate, not an official ATS score or a hiring prediction.
- Project/experience points count extracted resume entries; they do not judge project quality.
- Skill recognition uses a finite skill dictionary and explicit aliases, so it will not recognize every possible technology or phrasing.

## Project structure

```text
ai-resume-analyzer/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── .env.example
```
