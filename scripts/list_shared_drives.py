from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes and credentials
SCOPES = ['https://www.googleapis.com/auth/drive']
creds_file = 'scripts/misc/analytics/drive_credentials.json'

# Authentication
flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
creds = flow.run_local_server(port=0)

# Build the Drive service
service = build('drive', 'v3', credentials=creds)

# List all shared drives
page_token = None
print("Available Shared Drives:")
print("-" * 80)

while True:
    results = service.drives().list(
        pageSize=100,
        fields='nextPageToken, drives(id, name)',
        pageToken=page_token
    ).execute()
    
    drives = results.get('drives', [])
    
    if not drives:
        print("No shared drives found.")
        break
    
    for drive in drives:
        print(f"Name: {drive['name']}")
        print(f"ID:   {drive['id']}")
        print("-" * 80)
    
    page_token = results.get('nextPageToken', None)
    if page_token is None:
        break
