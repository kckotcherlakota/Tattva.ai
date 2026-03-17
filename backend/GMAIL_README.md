# Gmail Integration for Tatva.ai

Read emails and automatically transcribe audio attachments using Telugu/Sanskrit ASR.

## Features

- ✅ Read unread emails
- ✅ Detect audio attachments (MP3, WAV, M4A, OGG, FLAC)
- ✅ Download attachments automatically
- ✅ Mark emails as read/processed
- ✅ REST API endpoints for integration
- ✅ Custom labels for workflow tracking

## Setup

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. **Enable Gmail API**:
   - APIs & Services > Enable APIs & Services
   - Search "Gmail API" > Click Enable

4. **Create OAuth2 Credentials**:
   - APIs & Services > Credentials
   - Click "Create Credentials" > OAuth client ID
   - Application type: **Desktop app**
   - Name: "Tatva.ai Gmail Integration"
   - Click Create
   - Download JSON file

5. **Save Credentials**:
   ```bash
   # Move downloaded file to backend directory
   mv ~/Downloads/client_secret_*.json backend/credentials.json
   ```

### 2. Install Dependencies

```bash
cd backend
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 3. First Authentication

```bash
python gmail_integration.py
```

This will:
- Open browser for Google sign-in
- Ask permission to read Gmail
- Save token.json for future use

## API Endpoints

### Connect Gmail
```bash
POST /gmail/connect
{
  "credentials_path": "credentials.json",
  "token_path": "token.json"
}
```

### Get Unread Emails
```bash
GET /gmail/emails?max_results=10&query=has:attachment
```

### Download Attachment
```bash
GET /gmail/emails/{msg_id}/attachment/{att_id}?filename=audio.mp3
```

### Mark as Read
```bash
POST /gmail/emails/{msg_id}/mark-read
```

## Usage Example

```python
from gmail_integration import GmailIntegration

# Initialize
gmail = GmailIntegration()

# Get unread emails with audio attachments
emails = gmail.get_unread_emails(max_results=5, query="has:attachment")

for email in emails:
    print(f"From: {email['from']}")
    print(f"Subject: {email['subject']}")
    
    if email['has_audio']:
        for att in email['attachments']:
            # Download audio
            path = gmail.download_attachment(
                email['id'], 
                att['attachmentId'], 
                att['filename']
            )
            
            # Now transcribe with Tatva.ai
            # ... call transcribe endpoint with this file ...
            
        # Mark as processed
        gmail.mark_as_read(email['id'])
        gmail.mark_as_processed(email['id'])
```

## Gmail Search Queries

You can use Gmail search syntax:

| Query | Description |
|-------|-------------|
| `has:attachment` | Emails with attachments |
| `filename:mp3` | MP3 attachments |
| `from:boss@company.com` | From specific sender |
| `subject:meeting` | Subject contains "meeting" |
| `newer_than:2d` | Last 2 days |
| `has:attachment subject:recording` | Attachments + subject |

## Workflow Automation

Set up a cron job to check emails every 15 minutes:

```bash
# Add to crontab
*/15 * * * * cd /path/to/Tattva.ai/backend && python process_gmail.py
```

## Security Notes

- `credentials.json` - **Never commit to git** (add to .gitignore)
- `token.json` - OAuth token, also keep private
- Uses read-only Gmail scope by default
- Can modify to add `gmail.modify` scope for marking as read

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `credentials.json not found` | Download from Google Cloud Console |
| `Token expired` | Delete `token.json` and re-authenticate |
| `Access denied` | Check Gmail API is enabled in Cloud Console |
| `No module named 'google'` | Install requirements: `pip install google-api-python-client` |

---

*Automate your audio transcription workflow from Gmail.*
