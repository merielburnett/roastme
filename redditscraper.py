import praw
import csv
import re
from datetime import datetime, timezone, timedelta

# PRAW API credentials
client_id = '..........'
client_secret = '.........'
user_agent = 'testscript by u/........'
username = '..........'
password = '.............'


#define the subreddit and date range
subreddit_name = 'RoastMe'

#auth with Reddit
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    user_agent=user_agent,
    username=username,
    password=password
)

#function to convert year, month, and week to UTC timestamp
def string_to_utc(year, month, week):
    start_of_week = datetime(year, month, 1, tzinfo=timezone.utc) + timedelta(weeks=week - 1)
    return start_of_week.timestamp()

#functin to extract age and gender from the post title
def extract_age_gender(title):
    # look for a 2-digit number in the title
    age_match = re.search(r'\b(\d{2})\b', title)
    age = age_match.group(1) if age_match else None
    
    # determine gender based on rules
    gender = None
    if age:
        # look for 'M' or 'F' near age
        if re.search(rf"\b{age}(M|F)\b|\b(M|F){age}\b", title, re.IGNORECASE):
            gender = re.search(r"(?<=\d{2})[MF]|[MF](?=\d{2})", title, re.IGNORECASE).group(0)
        # look for standalone 'M' or 'F' if not directly near age
        elif re.search(r"\bM\b", title, re.IGNORECASE):
            gender = "M"
        elif re.search(r"\bF\b", title, re.IGNORECASE):
            gender = "F"
        # check for specific gender terms
        elif re.search(r"\b(male|man)\b", title, re.IGNORECASE):
            gender = "M"
        elif re.search(r"\b(female|woman)\b", title, re.IGNORECASE):
            gender = "F"
        
    # convert gender to full text
    if gender in ["M", "m"]:
        gender = "male"
    elif gender in ["F", "f"]:
        gender = "female"
    else:
        gender = None

    return age, gender

# Function to filter valid comments
def is_valid_comment(comment_body):
    # filter out invalid comments
    if not comment_body or "[removed]" in comment_body.lower() or "giphy" in comment_body.lower():
        return False
    # remove non-ASCII characters, allowing standard punctuation, and reject strings with >3 consecutive non-ASCII chars
    if re.search(r"[^\x00-\x7F]{3,}", comment_body):
        return False
    return True

#function to scrape posts and comments within a time range
def scrape_reddit(start_time, end_time, output_file):
    subreddit = reddit.subreddit(subreddit_name)
    
    # Open CSV file for writing
    with open(output_file, 'w', newline='', encoding="utf-8") as file:
        file_writer = csv.writer(file)
        # Write header
        file_writer.writerow(['Title', 'Age', 'Gender', 'Thread Link', 'Comment', 'Comment UTC Timestamp', 'Thread Upvotes', 'Comment Upvotes'])
        
        num_rows = 0
        for submission in subreddit.new(limit=None):  # iterate over all new posts
            post_time = submission.created_utc

            # only process posts within the date range
            if post_time < start_time:
                print("Reached posts older than the specified start time. Stopping.")
                break
            if post_time > end_time:
                continue

            # get age and gender
            age, gender = extract_age_gender(submission.title)
            if not age or not gender:  # skip posts missing age or gender
                continue

            # get post details
            post_title = submission.title
            post_text = submission.selftext
            permalink = submission.permalink
            post_upvotes = submission.score

            # iterate through comments
            submission.comments.replace_more(limit=None)
            for comment in submission.comments.list():
                comment_body = comment.body
                comment_time = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                comment_upvotes = comment.score

                # apply comment filters
                if not is_valid_comment(comment_body):
                    continue

                # write data to CSV
                file_writer.writerow([post_title, age, gender, f'https://www.reddit.com{permalink}', comment_body, comment_time, post_upvotes, comment_upvotes])
                num_rows += 1

            print(f"Scraped {num_rows} comments so far...")

#get user input for the start and end time
year = int(input("Enter the year (e.g., 2024):")) 
start_month = int(input("Enter the start month (e.g., 9 for September):"))
start_week = int(input("Enter the start week of the month (e.g., 1 for week 1):"))
end_month = int(input("Enter the end month (e.g., 10 for October):"))
end_week = int(input("Enter the end week of the month (e.g., 1 for week 1):"))

#get UTC timestamps for the start and end of the range
start_time = string_to_utc(year, start_month, start_week)
end_time = string_to_utc(year, end_month, end_week)

#generate output file name based on subreddit and date range
output_file = f"{subreddit_name}_{year}_month{start_month}_week{start_week}_to_month{end_month}_week{end_week}_data.csv"

#runn the scraper
scrape_reddit(start_time, end_time, output_file)
