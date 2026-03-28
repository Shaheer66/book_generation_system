📖 Autonomous Book Generation Engine
This system is an end-to-end, state-driven orchestration engine that automates the research, outlining, and drafting of full-length books. It uses Google Sheets as a lightweight frontend, Supabase for robust state management, and Groq's Compound AI (Research + Generation) for high-speed, fact-checked writing.

🚀 Features
Google Sheets Sync: Bi-directional syncing allows editors to request books, review AI outputs, and approve text directly from a spreadsheet.

Agentic Research & Generation: Uses the Groq compound model to natively search the web, verify facts, and write comprehensive chapters without manual tool-calling.

State Machine Orchestration: A resilient Python loop (main.py) that handles API rate limits, polling, and auto-recovery.

Automated Email Alerts: Sends Gmail SMTP notifications to assigned editors when human review is required.

DOCX Compilation: Automatically stitches approved chapters into a styled, downloadable Word document.

🏗️ Project Structure
Plaintext
book_gen_system/
├── core/
│   ├── database.py       # Supabase connection & CRUD operations
│   ├── llm_compound.py   # Groq Compound logic (Native Research + Write)
│   └── mailer.py         # Gmail SMTP notification service
├── sync/
│   └── sheet_sync.py     # Bi-directional Google Sheets batch syncing
├── services/
│   ├── outline_svc.py    # Regex parser to split outlines into chapter rows
│   └── compiler_svc.py   # python-docx logic to generate final .docx files
├── exports/              # Directory where final .docx books are saved
├── .env                  # Secrets and API keys
├── service_account.json  # Google Cloud Service Account credentials
└── main.py               # The Orchestrator / State Machine Loop
🛠️ Setup & Prerequisites
1. Environment Variables (.env)
Create a .env file in the root directory with the following keys:

Code snippet
# Groq Setup
GROQ_API_KEY=your_groq_api_key

# Supabase Setup
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# Google Sheets Setup
SPREADSHEET_ID=your_google_sheet_id

# Mailer Setup (Gmail App Password)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password
ADMIN_EMAIL=admin_fallback@example.com

# Orchestrator Config
POLL_INTERVAL=30
2. Database Schema (Supabase)
Run these commands in your Supabase SQL editor to ensure your tables are ready:

SQL
CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    pre_outline_notes TEXT,
    outline_content TEXT,
    status TEXT DEFAULT 'drafting_outline',
    editor_email TEXT DEFAULT 'admin@example.com',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID REFERENCES books(id),
    chapter_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    status TEXT DEFAULT 'pending_generation',
    editor_email TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
3. Google Sheets Configuration
Your connected Google Sheet must have two tabs.

Tab 1: Books_Overview
| Column A | Column B | Column C | Column D | Column E | Column F | Column G |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Book ID | Title | Pre-Outline Notes | Outline Content | Book Status | Created At | Editor Email |
| (Leave Blank) | The Ocean | Focus on whales | (AI Output) | (AI Output) | (Auto) | editor@email.com |

Tab 2: Chapters
| Column A | Column B | Column C | Column D | Column E |
| :--- | :--- | :--- | :--- | :--- |
| Book ID | Chapter # | Title | Content | Status |
| (Auto-Sync) | (Auto-Sync) | (Auto-Sync) | (AI Output) | (AI Output) |

⚙️ The State Machine (How it works)
The orchestrator operates purely on Statuses pushed between the Sheet and Database:

drafting_outline: Triggered by a new row in Google Sheets. AI researches and writes the outline.

review_required: AI has finished drafting the outline or a chapter. The system emails the Editor.

approved: [Human Action] The editor changes the cell in Google Sheets to "approved".

If Outline is approved: The system splits the outline into individual chapter rows.

If Chapter is approved: The system waits until all chapters are approved.

pending_generation: Triggered automatically for Chapter 1, then Chapter 2, etc. The AI writes the full chapter text.

completed: All chapters are approved. The system compiles the .docx file and sends the final email.

▶️ Running the System
Install dependencies:

Bash
pip install groq supabase google-api-python-client google-auth-httplib2 google-auth-oauthlib python-docx python-dotenv
Start the Engine:

Bash
python main.py
The engine will continuously run, polling for updates every 30 seconds.