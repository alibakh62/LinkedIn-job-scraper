import csv
import json
import os
import re
import time
from datetime import datetime

import uuid
import pandas as pd
import webql
from dotenv import load_dotenv
from webql.sync_api.session import Session
from webql.sync_api.web import PlaywrightWebDriver

from login import login

load_dotenv()

today = datetime.today().strftime("%Y_%m_%d")
CSV_FILE = f"jobs_postings_{today}.csv"

URL = "https://www.linkedin.com/jobs"
EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
LOGIN_SESSION_NAME = os.environ.get("LOGIN_SESSION_NAME")
SEARCH_SESSION_NAME = os.environ.get("SEARCH_SESSION_NAME")


def clean_text(text):
    # Check if the input is not a string (e.g., NaN or float)
    if not isinstance(text, str):
        return text  # Return the input as-is if it's not a string

    # Proceed with cleaning if the input is a string
    cleaned_text = re.sub(r"[^\w$/.()]+", ".", text)
    return cleaned_text


def collect_data(session):
    JOB_QUERY = """
    {
        jobs[] {
            job_title
            company_name
            city
            salary_range
            job_url
        }
    }
    """
    response = session.query(JOB_QUERY)
    jobs_url = []
    for i in range(len(response.jobs)):
        try:
            jobs_url.extend(
                ["www.linkedin.com" + response.jobs[i].job_url.get_attribute("href")]
            )
        except Exception as e:
            print("~" * 100)
            print(f"Error: {e}")
            print(f"Response jobs: {response.jobs}")
            print("~" * 100)
            jobs_url.extend([""])
    return response.jobs.to_data(), jobs_url


def scroll_down(session):
    javascript_code = """
        (async () => {
          const resultsList = document.querySelector('div.jobs-search-results-list');
          resultsList.scrollTop += resultsList.clientHeight; // Scrolls down one viewport height
        })();
        """
    session.current_page.evaluate(javascript_code)


def check_end_of_page(session):
    javascript_code = """
    (() => {
        const resultsList = document.querySelector('div.jobs-search-results-list');
        const atBottom = resultsList.scrollTop + resultsList.clientHeight >= resultsList.scrollHeight;
        return atBottom;
    })();
    """

    # Returns True if at the bottom, False otherwise
    return session.current_page.evaluate(javascript_code)


def search_and_collect_jobs(search_keyword, location_keyword, headless=True):

    # Login
    if os.path.exists(f"{LOGIN_SESSION_NAME}.json"):
        login_session_state = Session.load_user_session_state(
            f"{LOGIN_SESSION_NAME}.json"
        )
    else:
        driver = PlaywrightWebDriver(headless=headless)
        login_session = webql.start_session(URL, web_driver=driver)
        login(login_session, EMAIL, PASSWORD)
        login_session_state = Session.load_user_session_state(
            f"{LOGIN_SESSION_NAME}.json"
        )

    # Search for jobs
    driver = PlaywrightWebDriver(headless=headless)
    search_session = webql.start_session(
        URL, web_driver=driver, storage_state=login_session_state
    )

    SEARCH_QUERY = """
    {
        search_box
        search_btn
    }
    """

    response = search_session.query(SEARCH_QUERY)
    response.search_box.fill(search_keyword)
    response.search_box.press("Enter")

    time.sleep(5)

    LOCATION_QUERY = """
    {
        location_search_box
    }
    """

    response = search_session.query(LOCATION_QUERY)
    response.location_search_box.fill(location_keyword)
    response.location_search_box.press("Enter")

    time.sleep(5)

    # Collect jobs data
    all_data = []
    all_jobs_url = []
    reached_end = False

    while not reached_end:
        current_data, jobs_url = collect_data(search_session)
        # print(f"Current data:\n\n {current_data}")
        # print("-" * 100)
        # print(f"Jobs URL:\n\n {jobs_url}")
        # print("-" * 100)
        if current_data:
            all_data.extend(current_data)
            all_jobs_url.extend(jobs_url)

        scroll_down(search_session)
        time.sleep(2)

        # Check if we reached the end of the page
        reached_end = check_end_of_page(search_session)

    # Now `all_data` contains the information of all jobs loaded during the scrolling
    # Save the collected data to JSON and CSV as in your original code
    with open("search_scraped_jobs.json", "w") as json_file:
        json.dump(all_data, json_file)

    with open(CSV_FILE, "w", newline="") as csv_file:
        writer = csv.writer(csv_file)

        # Write the headers to the CSV file
        headers = list(all_data[0].keys()) + ["job_link"] + ["ID"]
        writer.writerow(headers)

        for i, job in enumerate(all_data):
            # Prepare a list for the row's data, filling it with empty strings for each header initially
            row_data = [""] * len(headers)

            # Fill in the row's data based on the job's data
            for header in job.keys():
                # Find the index of this header and replace the empty string with actual data
                header_index = headers.index(header)
                row_data[header_index] = job[header]

            # Add the job URL at the end
            row_data[-2] = all_jobs_url[i]

            # Add a unique ID for each job
            row_data[-1] = str(uuid.uuid4())

            writer.writerow(row_data)

    search_session.stop()

    data = pd.read_csv(CSV_FILE)
    data = data.drop_duplicates(
        subset=["job_title", "company_name", "city", "salary_range"]
    ).copy()
    # Clean the salary_range column
    data["salary_range"] = data["salary_range"].apply(clean_text)
    data.to_csv(CSV_FILE, index=False)
    print(f"Data saved to {CSV_FILE}")


# search_and_collect_jobs("Data Scientist", "California, CA")
