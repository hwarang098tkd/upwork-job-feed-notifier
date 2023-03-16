import time

import feedparser
import pyodbc
import schedule
import logging
from datetime import datetime
from win10toast_click import ToastNotifier
import webbrowser
import json
import os
import sys
import pyttsx3

logging.basicConfig(filename='upwork_rss.log', level=logging.INFO)  # Set up logging
toaster = ToastNotifier()  # initialize


def login_sql():
    # get the json data from file settings
    with open(os.path.join(sys.path[0], "settings.json"), "r") as f:
        data = json.load(f)
    urls = data["urls"]

    # Connect to the Microsoft SQL Server database
    server = data["credentials"]["server"]
    database = data["credentials"]["database"]
    username = data["credentials"]["username"]
    password = data["credentials"]["password"]

    try:
        cnxn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = cnxn.cursor()
        return urls, cursor, cnxn
    except:
        print("The connection to the database failed. Please check the credentials.")


def logging_info(message, current_datetime):
    logging.info(f"{message} - {current_datetime}")  # Log the success


def open_url(link):
    try:
        # Try to open the link in a new web browser tab
        webbrowser.open_new(link)
        print('Opening URL...')
    except:
        # If there is an error, print a message indicating that the URL could not be opened
        print('Failed to open URL. Unsupported variable type.')

#
# def display_alert(title, link):
#     # showcase
#     toaster.show_toast(
#         title,  # title
#         "Click to open URL! >>",  # message
#         icon_path=None,  # 'icon_path'
#         duration=5,  # for how many seconds toast should be visible; None = leave notification in Notification Center
#         threaded=True,
#         # True = run other code in parallel; False = code execution will wait till notification disappears
#         callback_on_click=lambda: open_url(link)  # click notification to run function
#     )


def play_announcing(count):
    engine = pyttsx3.init()
    engine.say(f"{str(count)} new jobs found")
    engine.runAndWait()


# Define the function to parse and store the RSS feed data
def parse_and_store(audio, browse):
    print("New search...")
    count_jobs = 0
    new_dict = {}
    current_datetime = str(datetime.now())
    result = login_sql()
    if result is None:
        print("The connection to the database failed. Please check the credentials.")
        logging_info(current_datetime, "The connection to the database failed. Please check the credentials.")
        new_dict["Error"] = "The connection to the database failed. Please check the credentials."
        return new_dict
    else:
        urls, cursor, cnxn = result
        for title, url in urls.items():
            print(f"Checking: {title}")
            # Parse the RSS feed

            feed = feedparser.parse(url)
            print(f"Jobs found in upwork: {len(feed.entries)}")

            feed_entries_links = [entry.link for entry in feed.entries]
            select_query = """
            SELECT link FROM (VALUES {}) AS temp_table (link)
            EXCEPT
            SELECT link FROM jobs;
            """.format(', '.join(['(?)' for i in feed_entries_links]), feed_entries_links)

            cursor.execute(select_query, feed_entries_links)
            no_existing_jobs = cursor.fetchall()
            print(f"New Jobs that not found in database: {len(no_existing_jobs)}")
            if len(no_existing_jobs) != 0:
                links = []
                for item in no_existing_jobs:
                    links.append(item[0])

                for item in feed.entries:
                    if item.link in links:
                        new_dict[item.title] = [item.link,
                                                datetime.strptime(item.published, '%a, %d %b %Y %H:%M:%S %z')]
                        if browse:
                            open_url( item.link)
                print(f"New Jobs that will insert to database: {len(new_dict.keys())}")
                insert_query = "INSERT INTO jobs (title, link, published) VALUES (?, ?, ?)"

                # Use a list comprehension to convert the dictionary to a list of tuples
                last_data = [(k, v[0], v[1]) for k, v in new_dict.items()]

                # Execute the query with the list of tuples
                cursor.executemany(insert_query, last_data)
                cnxn.commit()

            print(40 * "-")
        if len(new_dict.keys()) != 0 and audio:
            count_jobs += len(new_dict.keys())
            play_announcing(count_jobs)

        # Log the success
        logging_info(current_datetime, "RSS feed parsed and data stored successfully")
        print(f"Time: {datetime.now()}")
        print(50 * "#")
        return new_dict
