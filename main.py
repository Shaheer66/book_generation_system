import os
import time
import logging
from dotenv import load_dotenv

# Import our custom modules
from core.database import get_supabase_client
from core.llm_compound import BookCompoundAI
# Assuming you will create these based on our structure:
# from core.mailer import send_notification 
# from sync.sheet_sync import sync_new_books_to_db, sync_db_to_sheets
# from services.compiler_svc import compile_to_docx

# Production Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BookOrchestrator")

load_dotenv()

class BookOrchestrator:
    def __init__(self):
        logger.info("Initializing Book Orchestrator...")
        self.db = get_supabase_client()
        self.ai = BookCompoundAI()
        self.poll_interval = 30 # Seconds between checks

    def process_outlines(self):
        """Find books waiting for an outline and generate them."""
        response = self.db.table("books").select("*").eq("status", "drafting_outline").execute()
        books = response.data

        for book in books:
            logger.info(f"Generating outline for Book: {book['title']}")
            try:
                prompt = f"Title: {book['title']}\nNotes: {book['pre_outline_notes']}\nTask: Generate a detailed, chapter-by-chapter outline."
                outline_content = self.ai.generate_with_research(
                    system_role="You are a Master Book Architect.",
                    user_prompt=prompt
                )

                # Update DB: We temporarily store outline in 'pre_outline_notes' or a new column if you added it, 
                # but let's assume you added 'outline_content' based on our sheet sync discussion.
                self.db.table("books").update({
                    "status": "review_required",
                    # "outline_content": outline_content # Uncomment if column exists in DB
                }).eq("id", book['id']).execute()

                # Notify Editor
                # send_notification(to="editor@example.com", subject=f"Outline Ready: {book['title']}", body="Please review in Google Sheets.")
                logger.info(f"Outline complete for {book['title']}. Awaiting review.")

            except Exception as e:
                logger.error(f"Failed to generate outline for {book['title']}: {e}")

    def process_chapters(self):
        """Find chapters marked for generation and write them using past context."""
        response = self.db.table("chapters").select("*").eq("status", "pending_generation").execute()
        chapters = response.data

        for chapter in chapters:
            logger.info(f"Generating Chapter {chapter['chapter_number']} for Book ID: {chapter['book_id']}")
            try:
                # 1. Fetch Context (Previous Summaries)
                prev_chapters = self.db.table("chapters").select("summary")\
                    .eq("book_id", chapter['book_id'])\
                    .lt("chapter_number", chapter['chapter_number']).order("chapter_number").execute()
                
                context = "\n".join([c['summary'] for c in prev_chapters.data if c.get('summary')])

                # 2. Build Prompt
                prompt = f"""
                Chapter Title: {chapter['title']}
                Previous Story Context: {context}
                Editor Notes for this iteration: {chapter.get('editor_notes', 'None')}
                Task: Write the full chapter content.
                """

                # 3. Generate Content
                content = self.ai.generate_with_research("You are an expert author.", prompt)
                
                # 4. Generate Summary (for next chapter's context)
                summary = self.ai.generate_with_research(
                    "You are a summarizer.", 
                    f"Summarize this chapter in 200 words focusing on plot progression: {content}"
                )

                # 5. Update DB
                self.db.table("chapters").update({
                    "content": content,
                    "summary": summary,
                    "status": "review_required"
                }).eq("id", chapter['id']).execute()

                # Notify Editor
                # send_notification(to="editor@example.com", subject=f"Chapter {chapter['chapter_number']} Ready", body="Review required.")
                logger.info(f"Chapter {chapter['chapter_number']} completed.")

            except Exception as e:
                logger.error(f"Failed to generate chapter {chapter['id']}: {e}")

    def run(self):
        """Main Loop: Syncs, Processes, and Sleeps."""
        logger.info("Starting Orchestrator Loop...")
        while True:
            try:
                # 1. Pull new inputs from Google Sheets to Supabase
                # sync_new_books_to_db()

                # 2. Process AI Tasks
                self.process_outlines()
                self.process_chapters()

                # 3. Push updated statuses/content back to Google Sheets
                # sync_db_to_sheets()

                # 4. Check for Final Compilation
                # check_and_compile_books()

            except Exception as e:
                logger.error(f"Critical error in main loop: {e}")
            
            # Sleep to prevent rate limiting / high CPU usage
            time.sleep(self.poll_interval)

if __name__ == "__main__":
    orchestrator = BookOrchestrator()
    orchestrator.run()