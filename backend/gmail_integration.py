# Gmail Integration for Tatva.ai
# Reads emails and can transcribe audio attachments

import os
import base64
import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("Warning: Gmail API libraries not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'  # To mark as read/processed
]

class GmailIntegration:
    """Gmail integration for reading emails and processing audio attachments"""
    
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        
        if not GMAIL_AVAILABLE:
            raise ImportError("Gmail API libraries not installed")
        
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Google Cloud credentials not found at {self.credentials_path}. "
                        "Download from Google Cloud Console > APIs & Services > Credentials"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save token for future runs
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        print("✓ Gmail authentication successful")
    
    def get_unread_emails(self, max_results: int = 10, query: str = "") -> List[Dict]:
        """
        Fetch unread emails
        
        Args:
            max_results: Maximum number of emails to fetch
            query: Gmail search query (e.g., "from:boss@company.com has:attachment")
        
        Returns:
            List of email dictionaries
        """
        try:
            # Build query for unread emails
            search_query = "is:unread"
            if query:
                search_query += f" {query}"
            
            results = self.service.users().messages().list(
                userId='me',
                q=search_query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                email_data = self._get_email_details(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except HttpError as error:
            print(f"Error fetching emails: {error}")
            return []
    
    def _get_email_details(self, msg_id: str) -> Optional[Dict]:
        """Get full email details by message ID"""
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=msg_id,
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            
            # Extract headers
            subject = self._get_header(headers, 'Subject')
            sender = self._get_header(headers, 'From')
            date = self._get_header(headers, 'Date')
            
            # Extract body
            body = self._get_body(message['payload'])
            
            # Check for attachments
            attachments = self._get_attachments(message['payload'], msg_id)
            
            return {
                'id': msg_id,
                'threadId': message['threadId'],
                'subject': subject,
                'from': sender,
                'date': date,
                'body': body,
                'attachments': attachments,
                'has_audio': any(att['is_audio'] for att in attachments),
                'labelIds': message.get('labelIds', [])
            }
            
        except Exception as e:
            print(f"Error getting email {msg_id}: {e}")
            return None
    
    def _get_header(self, headers: List[Dict], name: str) -> str:
        """Extract header value by name"""
        for header in headers:
            if header['name'] == name:
                return header['value']
        return ""
    
    def _get_body(self, payload: Dict) -> str:
        """Extract email body text"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    # Could convert HTML to text here
                    pass
                elif 'parts' in part:
                    body += self._get_body(part)
        else:
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    def _get_attachments(self, payload: Dict, msg_id: str) -> List[Dict]:
        """Extract attachment information"""
        attachments = []
        
        if 'parts' not in payload:
            return attachments
        
        audio_types = ['audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/mp3', 
                       'audio/mp4', 'audio/x-m4a', 'audio/ogg', 'audio/flac']
        
        for part in payload['parts']:
            if 'filename' in part and part['filename']:
                attachment_id = part['body'].get('attachmentId')
                mime_type = part['mimeType']
                size = part['body'].get('size', 0)
                
                attachments.append({
                    'filename': part['filename'],
                    'mimeType': mime_type,
                    'size': size,
                    'attachmentId': attachment_id,
                    'messageId': msg_id,
                    'is_audio': mime_type in audio_types or 
                               any(part['filename'].lower().endswith(ext) 
                                   for ext in ['.mp3', '.wav', '.m4a', '.ogg', '.flac'])
                })
        
        return attachments
    
    def download_attachment(self, message_id: str, attachment_id: str, 
                           filename: str, save_dir: str = "./email_attachments") -> Optional[str]:
        """
        Download email attachment
        
        Returns:
            Path to downloaded file or None
        """
        try:
            # Create save directory
            save_path = Path(save_dir)
            save_path.mkdir(exist_ok=True)
            
            # Get attachment data
            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            # Decode and save
            file_data = base64.urlsafe_b64decode(attachment['data'])
            file_path = save_path / filename
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            print(f"✓ Downloaded: {file_path}")
            return str(file_path)
            
        except Exception as e:
            print(f"Error downloading attachment: {e}")
            return None
    
    def mark_as_read(self, msg_id: str):
        """Mark email as read"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            print(f"✓ Marked as read: {msg_id}")
        except Exception as e:
            print(f"Error marking as read: {e}")
    
    def mark_as_processed(self, msg_id: str, label_name: str = "TatvaProcessed"):
        """Add custom label to mark as processed"""
        try:
            # Create label if doesn't exist
            labels = self.service.users().labels().list(userId='me').execute()
            label_id = None
            
            for label in labels.get('labels', []):
                if label['name'] == label_name:
                    label_id = label['id']
                    break
            
            if not label_id:
                # Create new label
                label = self.service.users().labels().create(
                    userId='me',
                    body={'name': label_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
                ).execute()
                label_id = label['id']
            
            # Apply label
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            print(f"✓ Marked as processed: {msg_id}")
            
        except Exception as e:
            print(f"Error marking as processed: {e}")

# FastAPI endpoint integration
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/gmail", tags=["Gmail Integration"])

gmail_client = None

class GmailConfig(BaseModel):
    credentials_path: str = "credentials.json"
    token_path: str = "token.json"

@router.post("/connect")
async def connect_gmail(config: GmailConfig):
    """Initialize Gmail connection"""
    global gmail_client
    try:
        gmail_client = GmailIntegration(
            credentials_path=config.credentials_path,
            token_path=config.token_path
        )
        return {"status": "connected", "message": "Gmail integration active"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/emails")
async def get_emails(max_results: int = 10, query: str = ""):
    """Fetch unread emails"""
    if not gmail_client:
        raise HTTPException(status_code=503, detail="Gmail not connected. Call /connect first.")
    
    emails = gmail_client.get_unread_emails(max_results=max_results, query=query)
    return {"emails": emails, "count": len(emails)}

@router.get("/emails/{msg_id}/attachment/{att_id}")
async def download_email_attachment(msg_id: str, att_id: str, filename: str):
    """Download specific attachment"""
    if not gmail_client:
        raise HTTPException(status_code=503, detail="Gmail not connected")
    
    path = gmail_client.download_attachment(msg_id, att_id, filename)
    if path:
        return {"status": "downloaded", "path": path}
    else:
        raise HTTPException(status_code=500, detail="Download failed")

@router.post("/emails/{msg_id}/mark-read")
async def mark_email_read(msg_id: str):
    """Mark email as read"""
    if not gmail_client:
        raise HTTPException(status_code=503, detail="Gmail not connected")
    
    gmail_client.mark_as_read(msg_id)
    return {"status": "marked as read"}

# Standalone usage example
if __name__ == "__main__":
    # Setup instructions
    print("""
=== Gmail Integration Setup ===

1. Go to https://console.cloud.google.com
2. Create a new project or select existing
3. Enable Gmail API: APIs & Services > Enable APIs & Services > Gmail API
4. Create OAuth2 credentials:
   - APIs & Services & Credentials > Create Credentials > OAuth client ID
   - Application type: Desktop app
   - Download JSON and save as 'credentials.json' in this directory
5. Run this script and authenticate when prompted
6. Token will be saved for future runs

First run will open browser for Google authentication.
    """)
    
    # Example usage
    try:
        gmail = GmailIntegration()
        
        # Get unread emails with audio attachments
        print("\n=== Fetching unread emails with audio ===")
        emails = gmail.get_unread_emails(max_results=5, query="has:attachment")
        
        for email in emails:
            print(f"\nFrom: {email['from']}")
            print(f"Subject: {email['subject']}")
            print(f"Has audio: {email['has_audio']}")
            
            if email['has_audio']:
                for att in email['attachments']:
                    if att['is_audio']:
                        print(f"  → Audio: {att['filename']} ({att['size']} bytes)")
                        # Download
                        path = gmail.download_attachment(
                            email['id'], 
                            att['attachmentId'], 
                            att['filename']
                        )
                        if path:
                            print(f"    Downloaded to: {path}")
                            # Here you would call Tatva.ai transcribe on this file
            
            # Mark as read (optional)
            # gmail.mark_as_read(email['id'])
            
    except Exception as e:
        print(f"Error: {e}")
