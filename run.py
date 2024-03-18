import logging

from get_job_description import *
from search import *

today = datetime.today().strftime("%Y_%m_%d")
CSV_FILE = f"jobs_postings_{today}.csv"
SEARCH_KEYWORD = "Data Scientist"
LOCATION_KEYWORD = "California, CA"
MAX_RETRY = 3

log_filename = f"run_logs_{today}.log"
logging.basicConfig(
    filename=log_filename,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)

# Collect jobs postings for the search keyword
if not os.path.exists(CSV_FILE):
    search_and_collect_jobs(SEARCH_KEYWORD, LOCATION_KEYWORD)

# Collect job descriptions for the collected job postings
df = pd.read_csv(CSV_FILE)
df["posted_how_long_ago"] = pd.NA
df["number_of_applicants"] = pd.NA
df["job_description"] = pd.NA
df["employment_type"] = pd.NA
df["job_function"] = pd.NA
df["evaluation_score"] = pd.NA
df["matches"] = pd.NA
df["mismatches"] = pd.NA

for idx, row in df.iterrows():
    job_url = row["job_link"]
    job_title = row["job_title"]
    company_name = row["company_name"]
    if not isinstance(job_url, str):
        print("Job URL is not a string or it doesn't exist!")
        continue
    for i in range(MAX_RETRY):
        print(f"Attempt {i+1} of {MAX_RETRY}")
        try:
            print(f"Collecting job description for {job_title} at {company_name}")
            print(f"Job URL: {job_url}")
            data = collect_job_description(job_url)
            print(f"Collected jobs description data:\n\n {data}")

            # Save the job description to a file
            df.at[idx, "posted_how_long_ago"] = data["posted_how_long_ago"]
            df.at[idx, "number_of_applicants"] = data["number_of_applicants"]
            df.at[idx, "job_description"] = data["text_description"]
            df.at[idx, "employment_type"] = data["employment_type"]
            df.at[idx, "job_function"] = data["job_function"]
            print(f"Job description collected for {job_title} at {company_name}")
            print("~" * 100)
            break
        except Exception as e:
            print(f"Error: {e}")
            print(
                f"Retrying job description collection for {job_title} at {company_name}"
            )
            continue

df.to_csv(CSV_FILE, index=False)
