
# CV Evaluation Application

## Overview

This repository provides an application for **automated CV evaluation and email-based reporting**. The solution uses AI and NLP to evaluate candidates' CVs against job descriptions, generating structured feedback and scores based on customizable criteria. It simplifies and accelerates the recruitment process by integrating with job posting APIs and supporting various document formats.

---

## Features

1. **Job Description Integration**: Fetches active job openings from Base.vn and uses their descriptions as evaluation benchmarks.
2. **CV Parsing**: Extracts text from CVs in `.pdf`, `.docx`, and `.doc` formats via provided URLs.
3. **AI-Powered Scoring**: Utilizes Google's Gemini AI model to rate candidates on:
   - Job Fit
   - Technical Skills
   - Experience
   - Educational Background
   - Soft Skills
4. **JSON-Based Schema**: Ensures structured and detailed feedback for each candidate.
5. **Email Automation**: Sends evaluation results via email in CSV format.

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/cv-evaluation.git
   cd cv-evaluation
   ```

2. **Install Required Libraries**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Environment Variables**:
   Configure the following variables in your environment:
   - `BASE_API_KEY`: API key for accessing Base.vn.
   - `GOOGLE_API_KEY`: API key for the Gemini AI model.
   - `EMAIL`: Sender's email address for results.
   - `PASSWORD`: Application-specific password for the sender's email.

---

## Usage

1. **Run the Application**:
   ```bash
   python app.py
   ```

2. **Workflow**:
   - Fetch active job descriptions from Base.vn.
   - Parse recent candidates' CVs.
   - Evaluate each CV based on the corresponding job description.
   - Save results to a CSV file.
   - Send the evaluation results to specified recipients via email.

---

## Evaluation Criteria

The CV evaluation follows this scoring schema:

| **Criteria**         | **Description**                                                                 |
|-----------------------|---------------------------------------------------------------------------------|
| **Job Fit**           | Overall match to the job's requirements, cultural fit, and potential for growth.|
| **Technical Skills**  | Proficiency with required tools, knowledge application, and relevant projects. |
| **Experience**        | Years of experience, complexity of past projects, and roles in previous jobs.  |
| **Education**         | Relevant degrees, certifications, and academic achievements.                   |
| **Soft Skills**       | Communication, teamwork, adaptability, and problem-solving abilities.          |

Scores are averaged for an overall rating.

---

## Example Results

The output CSV includes the following fields:

- Job ID and Name
- Candidate ID and Name
- CV URL
- Application Date
- Individual Scores (Job Fit, Technical Skills, etc.)
- Overall Score
- Summary Feedback

---

## Contact

For any issues or suggestions, please reach out to:  
**Your Name**  
Email: your-email@example.com  
