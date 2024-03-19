import time
from webql.sync_api import close_all_popups_handler

from dotenv import load_dotenv

load_dotenv()


def login(session, email, password, session_name="linkedin_login_session"):

    sign_in_query = """
    {
        sign_in_btn
    }
    """

    credentials_query = """
    {
        email_input
        password_input
        sign_in_with_password_btn
    }
    """

    skip_query = """
    {
        skip_btn
    }
    """

    response_sign_in = session.query(sign_in_query)
    response_sign_in.sign_in_btn.click(force=True)

    response_credentials = session.query(credentials_query)
    response_credentials.email_input.fill(email)
    response_credentials.password_input.fill(password)
    response_credentials.sign_in_with_password_btn.click(force=True)
    session.on("popup", close_all_popups_handler)
    response_skip = session.query(skip_query)
    response_skip.skip_btn.click(force=True)
    response_skip_promos = session.query(skip_query)
    response_skip_promos.skip_btn.click(force=True)

    time.sleep(5)

    # Save the user session state to a file
    session.save_user_session_state(f"{session_name}.json")

    session.stop()
