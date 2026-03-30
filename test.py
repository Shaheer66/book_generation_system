
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = 'service_account.json'
# YOUR ACTUAL SHEET ID
SPREADSHEET_ID = '1fXm7IOnulEJ_NShPbo-kHRcP1ZfrX89-rudsYA144Vw' 
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def test_connection():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        
        # Test 1: Can we see the file metadata?
        sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        print("✅ SUCCESS: Found the Spreadsheet!")
        
        # Test 2: Can we see the specific tab?
        titles = [s['properties']['title'] for s in sheet_metadata.get('sheets', [])]
        print(f"Tabs found in your sheet: {titles}")
        
        if 'Books_Overview' in titles:
            print("✅ SUCCESS: 'Books_Overview' tab found!")
        else:
            print("❌ ERROR: 'Books_Overview' tab NOT found. Please rename your tab.")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_connection()