import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Optional, List, Dict

load_dotenv()
logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    url: Optional[str] = os.environ.get("SUPABASE_URL")
    key: Optional[str] = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")
    return create_client(url, key)

def fetch_books_by_status(status: str) -> List[Dict]:
    client = get_supabase_client()
    response = client.table("books").select("*").eq("status", status).execute()
    return response.data

def fetch_chapters_for_generation() -> List[Dict]:
    client = get_supabase_client()
    # Logic: Get chapters that are pending or need revision
    response = client.table("chapters").select("*").in_("status", ["pending_generation"]).execute()
    return response.data