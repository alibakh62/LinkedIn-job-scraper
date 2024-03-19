# LinkedIn-job-scraper
This script helps you speed up your job searching process by fully automating the job search and data collection part. It searches for a job, collects the search results, evaluates your resume against each job description and gives you a score that indicates your match with a job. It also highlights things you need to improve for a specific job.

# Installation
- First, install the required libraries by running

```bash
pip install -r requirements.txt
```

- Run `playwright install` in your command line if you don't have Playwright already installed.
- Rename the `.env.example` to `.env` and fill in the required configs.
- Go to the `run.py` and replace the values of `SEARCH_KEYWORD` and `LOCATION_KEYWORD` for what you are searching for. Note that `SEARCH_KEYWORD` refers to the job title and `LOCATION_KEYWORD` refers to the location.
- **Optional:** If you want to evaluate your resume for each job, upload a PDF version of your resume to the same folder where all the code is. Make sure the PDF file name is: "resume.pdf". 
- Start scraping by running `python run.py`.

# Important Notes
- **Very important:** We added a few measures to avoid your account being detected as a bot. However, in order to avoid your LinkedIn account being suspended due to bot detection, we strongly recommend you to create a LinkedIn account just for the purpose of running this scraper. We bear no responsibility if your account gets suspended.
- To run this code, you need to get an AgentQL API key. To get the API key, refer to their website: https://docs.agentql.com/
- You also need to have an OpenAI API key. Support for using open source models will come soon.

# Future
- Support for open source model
- Guide for scheduled run
- Navigating to next pages on search results
