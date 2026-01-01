"""
Gmail API connector for fetching emails.
Path: src/ingest/gmail_connector.py
"""
import os
import base64
from typing import List, Dict, Any
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import io
from pypdf import PdfReader
import docx

from .base_connector import BaseConnector


class GmailConnector(BaseConnector):
    """Connector for Gmail API"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service = None
        self.creds = None
    
    def _get_platform_name(self) -> str:
        return "gmail"
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth2.
        Creates token.json on first run.
        """
        creds = None
        token_file = self.config.get('token_file', 'token.json')
        creds_file = self.config.get('credentials_file', 'credentials.json')
        
        # Check if token.json exists
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_file):
                    print(f"[ERROR] {creds_file} not found!")
                    print("Please download it from Google Cloud Console")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.creds = creds
        self.service = build('gmail', 'v1', credentials=creds)
        print("[OK] Gmail authentication successful!")
        return True
    
    def fetch_messages(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of normalized message dictionaries
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        print(f"[INFO] Fetching up to {max_results} emails from Gmail...")
        
        try:
            # Get message IDs
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                print("No messages found.")
                return []
            
            print(f"Found {len(messages)} messages. Fetching details...")
            
            # Fetch full message details
            detailed_messages = []
            for i, msg in enumerate(messages, 1):
                try:
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    normalized = self.normalize_message(full_msg)
                    detailed_messages.append(normalized)
                    
                    if i % 10 == 0:
                        print(f"  Processed {i}/{len(messages)} messages...")
                        
                except Exception as e:
                    print(f"  [WARN] Error fetching message {msg['id']}: {e}")
                    continue
            
            print(f"[OK] Successfully fetched {len(detailed_messages)} messages")
            return detailed_messages
            
        except Exception as e:
            print(f"[ERROR] Error fetching messages: {e}")
            return []
    
    def _extract_id(self, raw_message: Dict[str, Any]) -> str:
        return f"gmail_{raw_message['id']}"
    
    def _extract_type(self, raw_message: Dict[str, Any]) -> str:
        return "email"
    
    def _extract_sender(self, raw_message: Dict[str, Any]) -> Dict[str, str]:
        headers = raw_message['payload']['headers']
        from_header = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
        
        # Parse "Name <email@example.com>" format
        if '<' in from_header:
            name = from_header.split('<')[0].strip().strip('"')
            email = from_header.split('<')[1].strip('>')
        else:
            name = from_header
            email = from_header
        
        return {"name": name, "email": email}
    
    def _extract_recipients(self, raw_message: Dict[str, Any]) -> List[Dict[str, str]]:
        headers = raw_message['payload']['headers']
        to_header = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
        
        recipients = []
        if to_header:
            # Split by comma for multiple recipients
            for recipient in to_header.split(','):
                recipient = recipient.strip()
                if '<' in recipient:
                    name = recipient.split('<')[0].strip().strip('"')
                    email = recipient.split('<')[1].strip('>')
                else:
                    name = recipient
                    email = recipient
                recipients.append({"name": name, "email": email})
        
        return recipients
    
    def _extract_date(self, raw_message: Dict[str, Any]) -> str:
        timestamp = int(raw_message['internalDate']) / 1000
        return datetime.fromtimestamp(timestamp).isoformat()
    
    def _extract_subject(self, raw_message: Dict[str, Any]) -> str:
        headers = raw_message['payload']['headers']
        return next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
    
    def _extract_attachments(self, raw_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and parse attachments from Gmail message"""
        msg_id = raw_message['id']
        payload = raw_message.get('payload', {})
        attachments = []
        
        self._find_attachments(payload, msg_id, attachments)
        return attachments

    def _find_attachments(self, part: Dict[str, Any], msg_id: str, attachments: List[Dict[str, Any]]):
        """Recursively find attachments in message parts"""
        filename = part.get('filename')
        body = part.get('body', {})
        attachment_id = body.get('attachmentId')
        
        if filename and attachment_id:
            mime_type = part.get('mimeType', '')
            print(f"  [INFO] Found attachment: {filename} ({mime_type})")
            
            # Fetch attachment data
            try:
                attachment_data = self.service.users().messages().attachments().get(
                    userId='me',
                    messageId=msg_id,
                    id=attachment_id
                ).execute()
                
                raw_content = base64.urlsafe_b64decode(attachment_data['data'])
                
                # Parse content based on file extension or mime type
                content = ""
                if filename.lower().endswith('.pdf'):
                    content = self._parse_pdf(raw_content)
                elif filename.lower().endswith('.docx'):
                    content = self._parse_docx(raw_content)
                elif mime_type == 'text/plain':
                    content = raw_content.decode('utf-8', errors='ignore')
                
                if content:
                    attachments.append({
                        "filename": filename,
                        "mime_type": mime_type,
                        "content": content
                    })
                    print(f"  [OK] Extracted {len(content)} chars from {filename}")
                else:
                    print(f"  [WARN] Could not extract text from {filename} (unsupported format or empty)")
                    
            except Exception as e:
                print(f"  [ERROR] Failed to fetch/parse attachment {filename}: {e}")

        # Recurse through sub-parts
        if 'parts' in part:
            for subpart in part['parts']:
                self._find_attachments(subpart, msg_id, attachments)

    def _parse_pdf(self, content_bytes: bytes) -> str:
        """Extract text from PDF bytes"""
        try:
            reader = PdfReader(io.BytesIO(content_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"    [ERROR] PDF parsing failed: {e}")
            return ""

    def _parse_docx(self, content_bytes: bytes) -> str:
        """Extract text from DOCX bytes"""
        try:
            doc = docx.Document(io.BytesIO(content_bytes))
            return "\n".join([para.text for para in doc.paragraphs]).strip()
        except Exception as e:
            print(f"    [ERROR] DOCX parsing failed: {e}")
            return ""
    
    def _extract_content(self, raw_message: Dict[str, Any]) -> str:
        """Extract email body (plain text preferred, HTML as fallback)"""
        payload = raw_message['payload']
        
        # Try to get plain text body
        body = self._get_body_from_parts(payload)
        
        if not body:
            # Fallback to snippet if body not found
            body = raw_message.get('snippet', '')
        
        return body
    
    def _get_body_from_parts(self, payload: Dict[str, Any]) -> str:
        """Recursively extract body from email parts"""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        if 'parts' in payload:
            for part in payload['parts']:
                # Prefer plain text
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                
                # Recursive search
                body = self._get_body_from_parts(part)
                if body:
                    return body
        
        return ""
    
    def _extract_thread_id(self, raw_message: Dict[str, Any]) -> str:
        return raw_message.get('threadId', '')
    
    def _generate_url(self, raw_message: Dict[str, Any]) -> str:
        msg_id = raw_message['id']
        return f"https://mail.google.com/mail/u/0/#inbox/{msg_id}"