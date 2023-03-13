from prefect import flow, task

import praw
import time
from datetime import datetime, timezone
import psycopg2
import smtplib
import ssl
from env import db_creds
from env import email_creds

import time

SEARCH_WAIT_TIME = 60 * 10 + 5


@flow(name="Main Syfty Flow", log_prints=True)
def main():
    # Connect to the database
    results = read_from_db()
    print('len(results)', len(results))

    for result in results:
        try:
            subreddit_name = result[0]
            search_phrase = result[1]
            user_email = result[2]
            submissions = get_posts(subreddit_name, search_phrase)
            # print(submissions)
            for submission in submissions:
                try:
                    send_email(submission, subreddit_name,
                               search_phrase, user_email)
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)


@task
def read_from_db():
    print('opening database connection')
    conn = psycopg2.connect(host=db_creds.db_endpoint, user=db_creds.db_username,
                            password=db_creds.db_password, database=db_creds.db_database,
                            port=db_creds.db_port)
    sql = ("SELECT s.subreddit, s.search_term, u.email FROM syfts_syft as s "
           " join accounts_customuser as u on s.owner_id = u.id "
           " where u.is_active=True")

    cur = conn.cursor()
    cur.execute(sql)
    results = cur.fetchall()
    # Close the cursor and connection
    cur.close()
    conn.close()
    print('connection closed')
    return results


@task(log_prints=True)
def get_posts(subreddit_name: str, search_phrase: str):
    reddit = praw.Reddit("bot")
    subreddit = reddit.subreddit(subreddit_name)
    submissions = []
    for submission in subreddit.new(limit=30):
        # print('submission', submission)
        now_epoch = time.time()
        # print('now_epoch', now_epoch)
        # print('submission.created_utc', submission.created_utc)
        # print('search_phrase.lower()', search_phrase.lower())
        # print('submission.title.lower()', submission.title.lower())
        if search_phrase.lower() in submission.title.lower() and int(now_epoch - submission.created_utc) < SEARCH_WAIT_TIME:
            submissions.append(submission)
            # print('yes')
        else:
            pass
            # print('search_phrase.lower() in submission.title.lower()',
            #       search_phrase.lower() in submission.title.lower())
            # print('int(now_epoch - submission.created_utc) < SEARCH_WAIT_TIME',
            #       int(now_epoch - submission.created_utc) < SEARCH_WAIT_TIME)
    return submissions


@task
def send_email(submission, subreddit_name, search_phrase, user_email):
    port = 587  # For TLS
    smtp_server = "smtp.zeptomail.com"

    sender_email = 'Hello from Syfty <hello@syfty.net>'
    receiver_email = user_email
    login_name = email_creds.EMAIL_HOST_USER
    password = email_creds.EMAIL_HOST_PASSWORD
    cleaned_title = ''.join(
        [i if ord(i) < 128 else '??' for i in submission.title])
    message = (f"Subject: New post on r/{subreddit_name} about {search_phrase}\n\n" + f"Reddit Post Title: {cleaned_title}\n" +
               f"Reddit Post URL: {submission.url}\n" + f"\nThis message is sent from Python.")
    # print(message)
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.ehlo()  # Can be omitted
        server.starttls(context=context)
        server.ehlo()  # Can be omitted
        server.login(login_name, password)
        server.sendmail(sender_email, receiver_email, message)


if __name__ == '__main__':
    main()
