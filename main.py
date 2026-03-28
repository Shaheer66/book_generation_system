import os
import time
import logging
from dotenv import load_dotenv

# Internal Core Services
from core.database import get_supabase_client
from core.llm_compound import BookCompoundAI
from core.mailer import send_notification

# Sync & Processing Services
from sync.sheet_sync import sync_new_books_to_db, sync_db_to_sheets, sync_chapters_to_sheets
from services.outline_svc import parse_and_seed_chapters
from services.compiler_svc import compile_book_to_docx

# Production Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BookOrchestrator")

load_dotenv()

class BookOrchestrator:
    def __init__(self):
        self.db = get_supabase_client()
        self.ai = BookCompoundAI()
        self.poll_interval = int(os.getenv("POLL_INTERVAL", 30))
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    def process_new_outlines(self):
        """Generates outlines for new books."""
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
                send_notification(email_target, f"Outline Ready: {book['title']}", "Review the outline in Google Sheets and mark Book Status as 'approved' to proceed.")
            except Exception as e:
                logger.error(f"Outline generation failed for {book['title']}: {e}")

    def process_approved_outlines(self):
        """Seeds individual chapter rows once an outline is approved."""
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
        """Generates content for individual chapters."""
        response = self.db.table("chapters").select("*").eq("status", "pending_generation").execute()
        
        for chapter in response.data:
            logger.info(f"Generating Chapter {chapter['chapter_number']} for Book ID: {chapter['book_id']}")
            try:
                # Fetch rolling context from previous chapters
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
                send_notification(email_target, f"Chapter {chapter['chapter_number']} Ready", f"Chapter '{chapter['title']}' is ready for review in the Chapters tab.")
            except Exception as e:
                logger.error(f"Chapter generation failed for ID {chapter['id']}: {e}")

    def check_and_compile_books(self):
        """Compiles the book to DOCX if all seeded chapters are approved."""
        # Find books that are currently in the writing phase
        response = self.db.table("books").select("*").eq("status", "chapters_seeded").execute()
        
        for book in response.data:
            try:
                # Get all chapters for this book
                chapters_resp = self.db.table("chapters").select("*").eq("book_id", book['id']).order("chapter_number").execute()
                chapters = chapters_resp.data
                
                if not chapters:
                    continue

                # Check if every single chapter is marked as 'approved'
                all_approved = all(ch.get('status') == 'approved' for ch in chapters)
                
                if all_approved:
                    logger.info(f"All chapters approved. Compiling Book: {book['title']}")
                    
                    filepath = compile_book_to_docx(book['title'], chapters)
                    
                    self.db.table("books").update({"status": "completed"}).eq("id", book['id']).execute()
                    
                    email_target = book.get('editor_email', self.admin_email)
                    send_notification(
                        to_email=email_target, 
                        subject=f"Book Completed: {book['title']}", 
                        body=f"Your book has been successfully compiled!\nFile saved locally at: {filepath}"
                    )
            except Exception as e:
                logger.error(f"Failed to compile book {book['title']}: {e}")

    def run(self):
        """The main continuous execution loop."""
        logger.info("Starting Orchestrator Loop...")
        while True:
            try:
                # 1. Pull new inputs
                sync_new_books_to_db()
                
                # 2. Process AI Pipeline Stages
                self.process_new_outlines()
                self.process_approved_outlines()
                self.process_pending_chapters()
                self.check_and_compile_books()
                
                # 3. Push updates back to Frontend (Google Sheets)
                sync_db_to_sheets()
                sync_chapters_to_sheets()
                
            except Exception as e:
                logger.error(f"Critical orchestrator loop error: {e}")
            
            time.sleep(self.poll_interval)

if __name__ == "__main__":
    orchestrator = BookOrchestrator()
    orchestrator.run()