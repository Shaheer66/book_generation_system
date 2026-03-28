import re
import logging
from core.database import get_supabase_client

logger = logging.getLogger(__name__)

def parse_and_seed_chapters(book_id: str, outline_text: str, editor_email: str):
    """
    Parses a Markdown outline and creates individual rows in the 'chapters' table.
    Expected format: 'Chapter 1: The Beginning', '## Chapter 2: The Middle', etc.
    """
    db = get_supabase_client()
    
    # Regex to find "Chapter X: Title" or "## Chapter X: Title"
    chapter_pattern = re.compile(r"(?:Chapter|## Chapter)\s*(\d+)[:.-]\s*(.*)", re.IGNORECASE)
    
    matches = chapter_pattern.findall(outline_text)
    
    if not matches:
        logger.warning(f"No chapters found in outline for Book ID {book_id}. Check AI output format.")
        return False

    chapters_to_insert = []
    for match in matches:
        chapter_num = int(match[0])
        chapter_title = match[1].strip()
        
        chapters_to_insert.append({
            "book_id": book_id,
            "chapter_number": chapter_num,
            "title": chapter_title,
            "status": "pending_generation", # Sets the gate for main.py to start writing
            "editor_email": editor_email
        })

    try:
        # Batch insert into Supabase
        db.table("chapters").insert(chapters_to_insert).execute()
        
        # Update Book status to move it out of the outline phase
        db.table("books").update({"status": "chapters_seeded"}).eq("id", book_id).execute()
        
        logger.info(f"Successfully seeded {len(chapters_to_insert)} chapters for Book {book_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to seed chapters: {e}")
        return False