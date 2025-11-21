import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from email.header import decode_header
from datetime import datetime
import re
from typing import List, Optional
from models.email import Email
# DBManager is imported in ingest_data.py/main.py, but not strictly needed here

# Scopes required for read access and modify actions
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = 'client_secret.json'
TOKEN_PICKLE = 'token.pickle'

class GmailClient:
    def __init__(self):
        self.service = self.authenticate()
        self.user_id = 'me'

    def authenticate(self):
        """Handles the OAuth flow, storing and refreshing tokens."""
        creds = None
        # The file token.pickle stores the user's access and refresh tokens
        if os.path.exists(TOKEN_PICKLE):
            with open(TOKEN_PICKLE, 'rb') as token:
                creds = pickle.load(token)

        # If no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                # Since this is a standalone script, use the installed app flow
                try:
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print("OAuth authorization failed. Ensure the authorization URL is opened and consent is granted.")
                    print("Error details:", repr(e))
                    raise

            # Save the credentials for the next run
            with open(TOKEN_PICKLE, 'wb') as token:
                pickle.dump(creds, token)

        return build('gmail', 'v1', credentials=creds)

    def fetch_emails(self, max_results=100, existing_ids: set = None) -> List[Email]:
        """Fetches the latest emails from the Inbox.

        If `existing_ids` is provided, message IDs present in that set will be
        skipped to avoid unnecessary API calls and re-fetching already-stored messages.
        """
        emails_list = []
        try:
            # 1. Get a list of message IDs from the INBOX
            response = self.service.users().messages().list(
                userId=self.user_id, 
                labelIds=['INBOX'], 
                maxResults=max_results
            ).execute()
            
            messages = response.get('messages', [])
            
            # 2. Fetch the full content for each message
            for message in messages:
                mid = message['id']
                if existing_ids and mid in existing_ids:
                    # Skip fetching message body for already stored messages
                    continue

                msg = self.service.users().messages().get(
                    userId=self.user_id,
                    id=mid,
                    format='full'
                ).execute()

                email = self._parse_message(msg)
                if email:
                    emails_list.append(email)

        except Exception as e:
            print(f"An error occurred while fetching emails: {e}")
        
        return emails_list

    def _get_header_value(self, headers, name):
        """Helper to safely extract and decode a specific header value."""
        for header in headers:
            if header['name'] == name:
                # Decode potential MIME encoded headers (like Subject)
                decoded = decode_header(header['value'])
                # Join parts and convert to string
                value = ' '.join([
                    part.decode(charset or 'utf-8', errors='ignore') 
                    if isinstance(part, bytes) else part 
                    for part, charset in decoded
                ])
                return value.strip()
        return None

    def _get_message_body(self, payload):
        """Helper to extract the plain text body from the message payload."""
        # Try to find the plain text part of the message
        parts = payload.get('parts', [])
        
        # Priority 1: Check parts for text/plain
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part['body'].get('data')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        # Priority 2: Check main body data if no parts (simple message)
        if payload.get('body') and payload['body'].get('data'):
            data = payload['body']['data']
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
        return ""

    def _parse_message(self, msg: dict) -> Optional[Email]:
        """Converts raw Gmail API dict into the standardized Email dataclass."""
        try:
            message_id = msg['id']
            thread_id = msg['threadId']
            headers = msg['payload']['headers']
            
            # Extract required header values
            from_address = self._get_header_value(headers, 'From')
            subject = self._get_header_value(headers, 'Subject')
            
            # Date is tricky; fetch as a header string first
            date_str = self._get_header_value(headers, 'Date')
            # Use python-dateutil to parse the complex email date format
            from dateutil.parser import parse
            received_at = parse(date_str)
            
            # Extract body content
            body_text = self._get_message_body(msg['payload'])
            
            # Check read status using labelIds
            is_read = 'UNREAD' not in msg.get('labelIds', [])

            return Email(
                id=message_id, 
                thread_id=thread_id, 
                from_address=from_address, 
                subject=subject, 
                body_text=body_text, 
                received_at=received_at, 
                is_read=is_read
            )
        except Exception as e:
            print(f"Error parsing message {msg.get('id', 'Unknown')}: {e}")
            return None

    def mark_as_read_unread(self, email_id: str, mark_as_read: bool):
        """Marks an email as read or unread via Gmail API."""
        try:
            body = {}
            if mark_as_read:
                body['removeLabelIds'] = ['UNREAD']
            else:
                body['addLabelIds'] = ['UNREAD']
                
            self.service.users().messages().modify(
                userId=self.user_id, 
                id=email_id, 
                body=body
            ).execute()
            # print(f"Successfully marked email {email_id} as {'read' if mark_as_read else 'unread'}")
            return True
        except Exception as e:
            print(f"Error modifying read status for {email_id}: {e}")
            return False

    def move_message(self, email_id: str, new_label_name: str):
        """Moves a message to a new mailbox (label) via Gmail API."""
        # Note: In Gmail, moving a message is done by adding a new label and 
        # removing the old system labels (like INBOX).
        try:
            # Resolve the label name to a Gmail label ID. System labels
            # (INBOX, TRASH, SPAM, SENT, DRAFT) are used as-is. For user
            # labels, fetch/create the label and use its ID.
            system_labels = {'INBOX', 'TRASH', 'SPAM', 'SENT', 'DRAFT'}
            if new_label_name in system_labels:
                label_id = new_label_name
            else:
                label_id = self._get_or_create_label_id(new_label_name)

            body = {
                'addLabelIds': [label_id],
                'removeLabelIds': ['INBOX']
            }
            
            self.service.users().messages().modify(
                userId=self.user_id, 
                id=email_id, 
                body=body
            ).execute()
            # print(f"Successfully moved email {email_id} to {new_label_name}")
            return True
        except Exception as e:
            print(f"Error moving message {email_id}: {e}")
            return False

    def _get_or_create_label_id(self, label_name: str) -> str:
        """Return the Gmail label ID for `label_name`, creating the label if missing."""
        try:
            resp = self.service.users().labels().list(userId=self.user_id).execute()
            labels = resp.get('labels', [])
            # Try exact match first, then case-insensitive match
            for lbl in labels:
                if lbl.get('name') == label_name:
                    print(f"Found existing label (exact): {label_name} -> {lbl.get('id')}")
                    return lbl.get('id')
            for lbl in labels:
                if lbl.get('name', '').lower() == label_name.lower():
                    print(f"Found existing label (case-insensitive): {label_name} -> {lbl.get('id')}")
                    return lbl.get('id')

            # Label not found: create it
            body = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            created = self.service.users().labels().create(userId=self.user_id, body=body).execute()
            print(f"Created label '{label_name}' -> {created.get('id')}")
            return created.get('id')
        except Exception as e:
            print(f"Error resolving/creating label '{label_name}': {e}")
            return label_name