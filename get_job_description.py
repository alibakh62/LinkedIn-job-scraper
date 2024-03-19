import logging
import os
import time
import json
from datetime import datetime

import fitz
import webql
from dotenv import load_dotenv
from openai import OpenAI
from webql.sync_api import close_all_popups_handler
from webql.sync_api.session import Session
from webql.sync_api.web import PlaywrightWebDriver

from login import *

load_dotenv()

# Configure logging
today = datetime.today().strftime("%Y_%m_%d")
log_filename = f"job_description_logs_{today}.log"
logging.basicConfig(
    filename=log_filename,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)

CSV_FILE = f"jobs_postings_{today}.csv"


def extract_text_from_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text


def get_job_description_text(session):
    javascript_code = """
    (() => {
        const containers = Array.from(document.querySelectorAll('.description__text'));
        return containers.map(container => container.innerText.trim()).join('\\n');
    })();
    """
    return session.current_page.evaluate(
        javascript_code
    )  # This should return the text from the containers


def process_job_description(job_description, max_retry=3):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = f"""Please extract the following details from the job description provided. If information about a specific item is not found, return 'No Information Found'.

    Job Description:
    {job_description}

    1. Qualifications:
    2. Preferred Qualifications:
    3. Responsibilities:
    4. Project or job duty description:
    5. Whether they offer a bonus:
    6. Whether they offer equity:
    7. Medical benefits:
    8. Any other useful information:
    
    Return the extracted information in the JSON format where the keys are the items listed above and the values are the extracted information.
    """
    completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an expert data science and machine learning expert. Your task is to extract information from job descriptions based on the user instructions.",
            },
            {"role": "user", "content": prompt},
        ],
        model="gpt-3.5-turbo",
    )

    return completion.choices[0].message.content


def evaluate_resume(resume_str, job_description_str, job_title):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = f"""Please evaluate the resume based on the job description and the job title provided. \
    Provide a final evaluation score between 0 and 100 where 0 indicates no match and 100 indicates a perfect match. \
    Also, provide a brief explanation of the evaluation score and highlight the key areas in terms of matches and mismatches. \
    Job Description: \
    {job_description_str} \
    Resume: \
    {resume_str} \
    Job Title: \
    {job_title} \

    Return the evaluation score and the short explanation in the JSON format where the keys are 'evaluation_score', 'matches' and 'mismatches'. \
    Make sure your explanations are brief and bullet-pointed. Limit the bullet points to 3 for both matches and mismatches.
    """
    completion = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {
                "role": "system",
                "content": """You are an expert in human resources. \
                Your task is to evaluate a resume based on the job description provided. \
                Follow the user instructions to complete the task.""",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return completion.choices[0].message.content


def collect_job_description(url, login_first=False, max_retry=3, headless=True):
    # Stealth mode settings
    vendor_info = "Google Inc. (Apple)"
    renderer_info = "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)"
    user_agent_info = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    session_name = os.getenv("JOB_DESC_SESSION_NAME")
    # Login
    if login_first:
        try:
            # Login
            if os.path.exists(f"{session_name}.json"):
                login_session_state = Session.load_user_session_state(
                    f"{session_name}.json"
                )
            else:
                driver = PlaywrightWebDriver(headless=headless)
                driver.enable_stealth_mode(
                    webgl_vendor=vendor_info,
                    webgl_renderer=renderer_info,
                    nav_user_agent=user_agent_info,
                )
                email = os.getenv("EMAIL")
                password = os.getenv("PASSWORD")
                login_session = webql.start_session(url, web_driver=driver)
                login(login_session, email, password, session_name)
                login_session_state = Session.load_user_session_state(
                    f"{session_name}.json"
                )
            # Given the login session state, start a new session
            driver = PlaywrightWebDriver(headless=headless)
            # Enable stealth mode to avoid bot detection
            driver.enable_stealth_mode(
                webgl_vendor=vendor_info,
                webgl_renderer=renderer_info,
                nav_user_agent=user_agent_info,
            )
            session = webql.start_session(
                url, web_driver=driver, storage_state=login_session_state
            )
        except AttributeError as e:
            logging.error(
                "Login was not successful ...\nLaunching the session without login ...\n"
            )
            driver = PlaywrightWebDriver(headless=headless)
            driver.enable_stealth_mode(
                webgl_vendor=vendor_info,
                webgl_renderer=renderer_info,
                nav_user_agent=user_agent_info,
            )
            session = webql.start_session(url, web_driver=driver)
    else:
        driver = PlaywrightWebDriver(headless=headless)
        driver.enable_stealth_mode(
            webgl_vendor=vendor_info,
            webgl_renderer=renderer_info,
            nav_user_agent=user_agent_info,
        )
        session = webql.start_session(url, web_driver=driver)
        try:
            resume_str = extract_text_from_pdf("resume.pdf")
            logging.info(f"Resume Reading Successful:\n\n {resume_str[:100]}")
        except Exception as e:
            logging.error(f"Resume Reading Error: {e}")
            resume_str = ""
        for i in range(max_retry):
            try:
                logging.info(f"Attempt {i + 1}/{max_retry}")
                # Expand the job description
                response = session.query("""{ see_more }""")
                logging.info("Clicking on the 'See more' button")
                session.on("popup", close_all_popups_handler)
                time.sleep(5)
                response.see_more.click(force=True)
                time.sleep(5)

                # Get the job description
                # Job description is different for logged in and logged out users
                if login_first:
                    # TODO: The query for the logged in user is not working, don't use it.
                    QUERY = """
                    {
                        job_title
                        company_name
                        location
                        posted_how_long_ago
                        number_of_applicants
                        required_skills_identified_by_linkedin
                        show_all_skills
                        text_description
                    }
                    """
                else:
                    QUERY = """
                    {
                        job_title
                        company_name
                        location
                        posted_how_long_ago
                        number_of_applicants
                        text_description
                        employment_type
                        job_function
                    }
                    """
                logging.info("Getting the job description")
                response = session.query(QUERY)
                time.sleep(5)
                data = response.to_data()
                logging.info(f"Data:\n\n {data}")
                # Sometimes page doesn't load up correctly.
                # Retry to ensure the job description is collected
                # If the job title is None, then retry
                if data.get("job_title", "") is not None:
                    # text_desc = data.get("text_description", "")
                    # logging.info(f"Text Description:\n\n{text_desc}")
                    text_desc = get_job_description_text(session)
                    logging.info(f"Job Description from LinkedIn:\n\n{text_desc}")
                    # Get specific details from the job description
                    job_description = process_job_description(str(text_desc))
                    logging.info(f"Job Description from chatgpt:\n\n{job_description}")
                    # Get specific details from the job description
                    data["text_description"] = job_description
                    # Evaluate the resume
                    if resume_str:
                        evaluation = evaluate_resume(
                            resume_str, job_description, data.get("job_title", "")
                        )
                        logging.info(f"Resume Evaluation:\n\n{evaluation}")
                        evaluation = evaluation.replace("```", "")
                        evaluation = evaluation.replace("json", "")
                        evals = json.loads(evaluation)
                        print(f"Evals score: {evals['evaluation_score']}")
                        data["evaluation_score"] = evals["evaluation_score"]
                        data["matches"] = evals["matches"]
                        data["mismatches"] = evals["mismatches"]
                    else:
                        logging.info("No resume provided for evaluation")
                        data["evaluation_score"] = "No resume provided for evaluation"
                        data["matches"] = "No resume provided for evaluation"
                        data["mismatches"] = "No resume provided for evaluation"
                    logging.info(f"Data:\n\n {data}")
                    session.stop()
                    return data
                elif i < max_retry - 1:
                    logging.info("Retrying to get the job description")
                else:
                    logging.error("Failed to get the job description")
                    session.stop()
                    return {}
            except Exception as e:
                logging.error(f"Error: {e}")
                if i < max_retry - 1:
                    logging.info("Retrying to get the job description")
                    continue
                else:
                    logging.error("Failed to get the job description")
                    session.stop()
                    return {}


# url = "www.linkedin.com/jobs/view/3827219715/?eBP=CwEAAAGOPvvLHUV5eEv5-LYp7h9SJqa1c_exttkIgVPMJ1OGc3aQ_fyoUnwFdXgr4aM59M3RsckdzvJyhS2sav6n_9HxK8mmqoF_aXvTMdl7-PCEjeUp4a5msVqH37CiMW2DT4aHsfXPUxE_pCELMpaLW-lbkfHehWbRRgOS9gH21kJgqk7fsxZPnxbBSiPDHoocD5PquGxG0dW81mIpu8iybJS0bFtyZXeJzQKk4fcNPR0OyPVJrxBN1aTeHNJZLTLvzwGqHzSBsG_Ve5ouvwKX3BsfeCy8CjcvR-3vW1bVH0bgwz7vLOgDdHKfKDwCb39qHQqXJLmdpEuPrpDE3-Vm89gQyeQWOArHjEwNkOgG4ozDc8de-pl5yShYQjCO4FgGEvQQLeqc08nY9G1A0r2H8LejAFAN&refId=NGdHb6XKchtZPU%2FKHYt5GQ%3D%3D&trackingId=vCjYCXlT%2FMbmgQbsw25O2A%3D%3D&trk=flagship3_search_srp_jobs"
# print(collect_job_description(url))
