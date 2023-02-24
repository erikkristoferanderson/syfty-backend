import praw
import time
from datetime import datetime, timezone
import psycopg2
import smtplib
import ssl
import db_creds
import email_creds

SEARCH_WAIT_TIME = 60 * 1000 + 5


def main():
    # Connect to the database
    print('opening database connection')
    conn = psycopg2.connect(host=db_creds.db_endpoint, user=db_creds.db_username,
                            password=db_creds.db_password, database=db_creds.db_database,
                            port=db_creds.db_port)
    sql = ("SELECT s.subreddit, s.search_term, u.email FROM syfty_search as s "
           " join auth_user as u on s.owner_id = u.id "
           " where u.is_active")
    # sql = "SELECT * FROM information_schema.columns where table_name='auth_user';"
    # sql = "SELECT * FROM information_schema.tables;"
    # Open a cursor to execute SQL statements
    cur = conn.cursor()
    cur.execute(sql)
    results = cur.fetchall()
    # print(results)
    for result in results:
        print('result', result)
        subreddit_name = result[0]
        print('subreddit_name', subreddit_name)
        search_phrase = result[1]
        print('search_phrase', search_phrase)
        user_email = result[2]
        print('user_email', user_email)
        submissions = get_posts(subreddit_name, search_phrase)
        print(submissions)
        for submission in submissions:
            print(submission.title)
            send_email(submission, subreddit_name, search_phrase, user_email)
            break
    # Close the cursor and connection
    cur.close()
    conn.close()
    print('connection closed')
    # time.sleep(SEARCH_WAIT_TIME)


def get_posts(subreddit_name: str, search_phrase: str):
    reddit = praw.Reddit("bot")
    subreddit = reddit.subreddit(subreddit_name)
    submissions = []
    for submission in subreddit.new(limit=30):
        now = datetime.now(timezone.utc)
        now_epoch = time.mktime(now.timetuple())
        if search_phrase.lower() in submission.title.lower() and int(now_epoch - submission.created_utc) < SEARCH_WAIT_TIME:
            submissions.append(submission)
    return submissions


def send_email(submission, subreddit_name, search_phrase, user_email):
    port = 587  # For TLS
    smtp_server = "smtp.zeptomail.com"

    sender_email = "hello@syfty.net"
    receiver_email = user_email
    login_name = email_creds.EMAIL_HOST_USER
    password = email_creds.EMAIL_HOST_PASSWORD
    message = (f"Subject: New post on r/{subreddit_name} about {search_phrase}\n\n" + f"Reddit Post Title: {submission.title}\n" +
               f"Reddit Post URL: {submission.url}\n" + f"\nThis message is sent from Python.")
    print(message)
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.ehlo()  # Can be omitted
        server.starttls(context=context)
        server.ehlo()  # Can be omitted
        server.login(login_name, password)
        server.sendmail(sender_email, receiver_email, message)


if __name__ == '__main__':
    main()
