import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from core.database import get_supabase_client

# Constants
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'service_account.json' 
SPREADSHEET_ID = '1gKbalKpK9Uk-5L2FF91umRld25wqfYL4tszdbwQUKU'

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def sync_new_books_to_db():
    service = get_sheets_service()
    sheet = service.spreadsheets()
    
    # Read Books_Overview (assuming it's the first sheet)
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Books_Overview!A2:C").execute()
    rows = result.get('values', [])
    
    supabase = get_supabase_client()
    
    for row in rows:
        # Check if Book ID (Col A) is empty - that means it's a new entry
        if len(row) < 1 or not row[0]:
            title = row[1]
            notes = row[2] if len(row) > 2 else ""
            
            # 1. Insert into Supabase
            data = supabase.table("books").insert({
                "title": title, 
                "pre_outline_notes": notes,
                "status": "drafting_outline"
            }).execute()
            
            # 2. Update the Sheet with the new UUID (to prevent double-sync)
            new_id = data.data[0]['id']
            # Logic to write new_id back to Column A...
            print(f"Synced new book: {title} with ID {new_id}")

if __name__ == "__main__":
    sync_new_books_to_db()