# Hangout Bot

## Setup

1. Clone this repo
2. Follow this guide to get the Google API credentials: https://developers.google.com/gmail/api/quickstart/quickstart-python
3. This is the important step. Create a Gmail filter to catch the hangouts like
   described below. Make sure to apply the filter to all the matched messages
   otherwise the script won't have anything to run.

        Subject: Name of the Hangout you want to parse. Has the words: is:chats

        Apply some label to it

4. Run the script!

