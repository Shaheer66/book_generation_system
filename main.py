import os
import time
import logging
from dotenv import load_dotenv

from core.database import get_supabase_client
from core.llm_compound import BookCompoundAI
from core.mailer import send_notification
from sync.sheet_sync import sync_new_books_to_db, sync_db_to_sheets
from services.outline_svc import parse_and_seed_chapters

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BookOrchestrator")

load_dotenv()

class BookOrchestrator:
    def __init__(self):
        self.db = get_supabase_client()
        self.ai = BookCompoundAI()
        self.poll_interval = 30
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    def process_new_outlines(self):
        response = self.db.table("books").select("*").eq("status", "drafting_outline").execute()
        
        for book in response.data:
            logger.info(f"Generating outline for: {book['title']}")
            try:
                prompt = f"Title: {book['title']}\nNotes: {book.get('pre_outline_notes', '')}\nTask: Generate a detailed, chapter-by-chapter outline in Markdown."
                outline_content = self.ai.generate_with_research("You are a Master Book Architect.", prompt)

                self.db.table("books").update({
                    "status": "review_required",
                    "outline_content": outline_content
                }).eq("id", book['id']).execute()

                email_target = book.get('editor_email', self.admin_email)
                send_notification(email_target, f"Outline Ready: {book['title']}", "Review in Google Sheets and mark as 'approved' to proceed.")
            except Exception as e:
                logger.error(f"Outline generation failed for {book['title']}: {e}")

    def process_approved_outlines(self):
        response = self.db.table("books").select("*").eq("status", "approved").execute()
        
        for book in response.data:
            logger.info(f"Seeding chapters for approved book: {book['title']}")
            try:
                success = parse_and_seed_chapters(book['id'], book['outline_content'], book.get('editor_email', self.admin_email))
                if not success:
                    self.db.table("books").update({"status": "outline_parsing_failed"}).eq("id", book['id']).execute()
            except Exception as e:
                logger.error(f"Chapter seeding failed for {book['title']}: {e}")

    def process_pending_chapters(self):
        response = self.db.table("chapters").select("*").eq("status", "pending_generation").execute()
        
        for chapter in response.data:
            logger.info(f"Generating Chapter {chapter['chapter_number']} for Book ID: {chapter['book_id']}")
            try:
                prev_chapters = self.db.table("chapters").select("summary")\
                    .eq("book_id", chapter['book_id'])\
                    .lt("chapter_number", chapter['chapter_number']).order("chapter_number").execute()
                
                context = "\n".join([c['summary'] for c in prev_chapters.data if c.get('summary')])

                prompt = f"Chapter Title: {chapter['title']}\nPrevious Context: {context}\nEditor Notes: {chapter.get('editor_notes', 'None')}\nTask: Write the full chapter."
                content = self.ai.generate_with_research("You are an expert author.", prompt)
                
                summary = self.ai.generate_with_research("You are a summarizer.", f"Summarize this chapter in 200 words: {content}")

                self.db.table("chapters").update({
                    "content": content,
                    "summary": summary,
                    "status": "review_required"
                }).eq("id", chapter['id']).execute()

                email_target = chapter.get('editor_email', self.admin_email)
                send_notification(email_target, f"Chapter {chapter['chapter_number']} Ready", f"Chapter '{chapter['title']}' is ready for review in Google Sheets.")
            except Exception as e:
                logger.error(f"Chapter generation failed for ID {chapter['id']}: {e}")

    def run(self):
        logger.info("Starting Orchestrator Loop...")
        while True:
            try:
                sync_new_books_to_db()
                
                self.process_new_outlines()
                self.process_approved_outlines()
                self.process_pending_chapters()
                
                sync_db_to_sheets()
            except Exception as e:
                logger.error(f"Critical orchestrator error: {e}")
            
            time.sleep(self.poll_interval)

if __name__ == "__main__":
    orchestrator = BookOrchestrator()
    orchestrator.run()