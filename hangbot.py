#!/usr/bin/python

import httplib2

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run

import base64
import time
import random
import sys

class Hangbot():

    # Path to the client_secret.json file downloaded from the Developer Console
    CLIENT_SECRET_FILE = 'client_secret.json'

    # Check https://developers.google.com/gmail/api/auth/scopes for all
    # available scopes
    OAUTH_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'

    # Location of the credentials storage file
    STORAGE = Storage('gmail.storage')

    MAX_BATCH_REQUESTS = 100

    # cost of a single unit, see
    # https://developers.google.com/gmail/api/v1/reference/quota
    sleep = 1.0/25

    def __init__(self, msg_f, meta_f, label):
        self.msg_f = msg_f
        self.meta_f = meta_f
        self.gmail = self.get_gmail()

        self.hangout_label = label

        self.messages = []

    def get_gmail(self):
        # Start the OAuth flow to retrieve credentials
        flow = flow_from_clientsecrets(self.CLIENT_SECRET_FILE,
                scope=self.OAUTH_SCOPE)

        http = httplib2.Http()

        # Try to retrieve credentials from storage or run the flow to generate
        # them
        credentials = self.STORAGE.get()
        if credentials is None or credentials.invalid:
            credentials = run(flow, self.STORAGE, http=http)

        # Authorize the httplib2.Http object with our credentials
        http = credentials.authorize(http)

        # Build the Gmail service from discovery
        return build('gmail', 'v1', http=http)

    def execute(self, request, units=1):
        response = False

        sleep = self.sleep * units

        for n in range(0, 5):
            try:
                time.sleep(sleep + random.random())
                response = request.execute()
                break
            except HttpError as e:
                if int(e.resp.status) in [429]:
                    # exponential backoff
                    sleep *= 2
                    response = False
                    print 'Error %s. retrying in %f seconds ...' % (e.resp.status, sleep)
                else:
                    raise e

        return response

    def handle_message(self, req_id, response, err):
        if err is not None:
            self.messages = []
            raise err
            return

        payload = response['payload']
        if payload['mimeType'] != 'text/html':
            return

        msg = {}

        # some really old messages don't have a header
        # the ones who do, extract the user
        if 'headers' in payload:
            for header in payload['headers']:
                if header['name'] != 'From':
                    return

            msg['user'] = header['value']

        msg['text'] = payload['body']['data'].encode('UTF-8')
        msg['historyId'] = response['historyId']

        self.messages.append(msg)


    def get_messages(self):


        gmail = self.gmail

        response = self.execute(gmail.users().labels().list(userId="me"))

        # Print ID for each thread
        if not response['labels']:
            return

        chat_label_id = ''
        for label in response['labels']:
            if label['name'] == self.hangout_label:
                chat_label_id = label['id']

        stop = False
        pageToken = ''
        meta = {'current': 0}

        while not stop:
            response = gmail.users().messages()
            if pageToken:
                response = response.list(userId="me",
                        labelIds=chat_label_id, pageToken=pageToken)
            else:
                response = response.list(userId="me", labelIds=chat_label_id)
            response = self.execute(response)

            # Print ID for each thread
            if not response['messages']:
                break

            # no next page. stop after this
            stop = 'nextPageToken' not in response
            stop = stop or len(response['nextPageToken']) == 0

            if not stop:
                pageToken = response['nextPageToken']
            meta['labelId'] = chat_label_id
            meta['pageToken'] = pageToken
            meta['estimate'] = response['resultSizeEstimate']
            meta['current'] += len(response['messages'])

            self.meta_f.write(str(meta) + ",\n")
            print str(meta) + ","

            # Get messages in batches.

            message_ids = []

            for message in response['messages']:
                message_ids.append(message['id'])

            for i in xrange(0, len(message_ids), self.MAX_BATCH_REQUESTS):
                batch = BatchHttpRequest(callback=self.handle_message)

                chunk = message_ids[i:i+self.MAX_BATCH_REQUESTS]

                for i in chunk:
                    batch.add(gmail.users().messages().get(userId="me", id=i))

                self.execute(batch, len(chunk) * 5)

                for msg in self.messages:
                    self.msg_f.write(str(msg) + ",\n")
                self.messages = []

            self.msg_f.flush()
            self.meta_f.flush()




if __name__ == "__main__":

    with open("/data/messages", "w") as msg_f:
        with open("/data/meta", "w") as meta_f:
            hb = Hangbot(msg_f, meta_f, label="test")
            hb.get_messages()


    #{u'historyId': u'7588366', u'id': u'147ad1042d9efd02', u'snippet': u'test2',
    #u'sizeEstimate': 100, u'threadId': u'147ac31f93448bcc', u'labelIds':
    #[u'Label_38'], u'payload': {u'mimeType': u'text/html', u'headers': [{u'name':
    #u'From', u'value': u'Denys Pavlov <denys.pavlov@gmail.com>'}], u'body':
    #{u'data': u'dGVzdDI=', u'size': 5}, u'partId': u'', u'filename': u''}}


