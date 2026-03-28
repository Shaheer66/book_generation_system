# import os
# from google.oauth2 import service_account
# from googleapiclient.discovery import build
# from core.database import get_supabase_client

# # Constants
# SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# SERVICE_ACCOUNT_FILE = 'service_account.json' 
# SPREADSHEET_ID = '1gKbalKpK9Uk-5L2FF91umRld25wqfYL4tszdbwQUKU'

# def get_sheets_service():
#     creds = service_account.Credentials.from_service_account_file(
#         SERVICE_ACCOUNT_FILE, scopes=SCOPES)
#     return build('sheets', 'v4', credentials=creds)

# def sync_new_books_to_db():
#     service = get_sheets_service()
#     sheet = service.spreadsheets()
    
#     # Read Books_Overview (assuming it's the first sheet)
#     result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Books_Overview!A2:C").execute()
#     rows = result.get('values', [])
    
#     supabase = get_supabase_client()
    
#     for row in rows:
#         # Check if Book ID (Col A) is empty - that means it's a new entry
#         if len(row) < 1 or not row[0]:
#             title = row[1]
#             notes = row[2] if len(row) > 2 else ""
            
#             # 1. Insert into Supabase
#             data = supabase.table("books").insert({
#                 "title": title, 
#                 "pre_outline_notes": notes,
#                 "status": "drafting_outline"
#             }).execute()
            
#             # 2. Update the Sheet with the new UUID (to prevent double-sync)
#             new_id = data.data[0]['id']
#             # Logic to write new_id back to Column A...
#             print(f"Synced new book: {title} with ID {new_id}")

# if __name__ == "__main__":
#     sync_new_books_to_db()

import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from core.database import get_supabase_client

logger = logging.getLogger(__name__)

# Constants
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'service_account.json' 
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", '1gKbalKpK9Uk-5L2FF91umRld25wqfYL4tszdbwQUKU')

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def sync_new_books_to_db():
    """Pulls new books from Google Sheets and writes back the Supabase UUID."""
    service = get_sheets_service()
    sheet = service.spreadsheets()
    supabase = get_supabase_client()
    
    # Read A to G to capture the new Editor Email column
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Books_Overview!A2:G").execute()
    rows = result.get('values', [])
    
    for i, row in enumerate(rows):
        # If Column A (ID) is empty, it's a new book
        if not row or len(row) == 0 or row[0].strip() == "":
            title = row[1] if len(row) > 1 else "Untitled"
            notes = row[2] if len(row) > 2 else ""
            # Get email from Column G (Index 6), fallback to admin if missing
            editor_email = row[6] if len(row) > 6 else os.getenv("ADMIN_EMAIL", "admin@example.com")
            
            try:
                # 1. Insert into Supabase
                data = supabase.table("books").insert({
                    "title": title, 
                    "pre_outline_notes": notes,
                    "editor_email": editor_email,
                    "status": "drafting_outline"
                }).execute()
                
                new_id = data.data[0]['id']
                
                # 2. Immediately write new_id back to Column A to prevent double-syncing
                row_number = i + 2 # +2 because we skip header and 0-index
                sheet.values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f"Books_Overview!A{row_number}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [[new_id]]}
                ).execute()
                
                logger.info(f"Synced new book: {title} with ID {new_id}")
            except Exception as e:
                logger.error(f"Failed to sync new book '{title}': {e}")

def sync_db_to_sheets():
    """Pushes AI-generated outlines and statuses from Supabase back to Google Sheets."""
    try:
        supabase = get_supabase_client()
        service = get_sheets_service()
        sheet = service.spreadsheets()

        # Fetch current Sheet Data to map Row Numbers
        sheet_result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Books_Overview!A2:G").execute()
        rows = sheet_result.get('values', [])
        
        if not rows: return
            
        # Fetch ground-truth state from Supabase
        db_books = supabase.table("books").select("id, outline_content, status").execute().data
        db_book_map = {book['id']: book for book in db_books if book.get('id')}

        batch_data = []
        
        for i, row in enumerate(rows):
            if not row or not row[0]: continue 
            
            book_id = row[0]
            if book_id in db_book_map:
                db_record = db_book_map[book_id]
                row_number = i + 2
                
                # Update Column D (Outline) and Column E (Status)
                range_name = f"Books_Overview!D{row_number}:E{row_number}"
                values = [[
                    db_record.get('outline_content', ''),
                    db_record.get('status', '')
                ]]
                
                batch_data.append({
                    "range": range_name,
                    "values": values
                })

        # Execute single batch API call for performance
        if batch_data:
            sheet.values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID, 
                body={"valueInputOption": "USER_ENTERED", "data": batch_data}
            ).execute()
            logger.info("Successfully pushed database updates back to Google Sheets.")

    except Exception as e:
        logger.error(f"Critical failure syncing DB back to Sheets: {e}")

if __name__ == "__main__":
    # Test the scripts locally
    sync_new_books_to_db()
    sync_db_to_sheets()