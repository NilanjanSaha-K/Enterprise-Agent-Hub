import os
import logging
import subprocess
import sys
import re
import json
import datetime
import csv
import io
from flask import Flask, jsonify, request, session
from dotenv import load_dotenv
import json

# --- Pypdf Imports ---

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from werkzeug.utils import secure_filename

# --- Imports for mail service ---
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Imports for Gemini Agents ---
import google.generativeai as Genai
from google import genai
from google.genai import types
# --- Import for CORS ---
from flask_cors import CORS  # <--- ADD THIS

# --- Imports for RAG Service ---
import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- Imports for Google Cloud & Firebase ---
try:
    from google.cloud import bigquery, storage
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaInMemoryUpload
    
    
    # --- NEW IMPORTS FOR FIREBASE ---
    import firebase_admin
    from firebase_admin import credentials, auth, firestore
except ImportError:
    print("ERROR: Google Cloud/Firebase libraries not found.")
    print("Please run: pip install google-cloud-bigquery google-cloud-storage google-auth google-api-python-client google-auth-httplib2 google-auth-oauthlib firebase-admin")
    # We don't exit here to allow the server to start even if tools fail, but logs will show errors

# --- 1. Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.env'))
if not os.path.exists(dotenv_path):
    logging.error(f".env file not found at {dotenv_path}")
else:
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f".env file loaded from {dotenv_path}")

# Get Credentials
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID") 
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
# In app.py, we get user email from session usually, but fallback to env for testing
DEFAULT_USER_EMAIL = os.getenv("USER_EMAIL_ADDRESS") 

# --- 2. Initialize Google Gemini ---
if not GOOGLE_API_KEY:
    logging.warning("GOOGLE_API_KEY not found in .env file. Most services will fail.")
else:
    try:
        Genai.configure(api_key=GOOGLE_API_KEY)
        logging.info("Google GenAI configured successfully.")
    except Exception as e:
        logging.error(f"Error configuring Google GenAI: {e}")

# --- 3a. Initialize RAG Service ---
PERSIST_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), 'chroma_db'))
COLLECTION_NAME = "RAGdataset"
embedding_model = None
chroma_client = None
rag_collection = None
if GOOGLE_API_KEY:
    try:
        embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", 
            task_type="retrieval_query"
        )
        logging.info("Gemini Embedding Model initialized.")
        if not os.path.exists(PERSIST_DIRECTORY):
            logging.error(f"ChromaDB directory not found at: {PERSIST_DIRECTORY}")
        else:
            chroma_client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
            rag_collection = chroma_client.get_collection(name=COLLECTION_NAME)
            logging.info(f"Loaded ChromaDB collection '{COLLECTION_NAME}' from {PERSIST_DIRECTORY}")
    except Exception as e:
        logging.error(f"Error initializing RAG service: {e}")

# --- 3b. Initialize Worker Agent Client ---
genai_client = None
if GOOGLE_API_KEY:
    try:
        genai_client = genai.Client(api_key=GOOGLE_API_KEY)
        logging.info("Gemini Client (for Worker Agent) initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing Gemini Client: {e}")

# --- 3c. Initialize Specialist Agent Models ---
customer_support_model = None
hr_assistant_model = None
marketing_agent_model = None
analytics_agent_model = None
admin_agent_model = None
general_agent_model = None

if GOOGLE_API_KEY:
    try:
        # Customer Support
        customer_support_model = Genai.GenerativeModel(
            'gemini-2.5-flash-preview-09-2025',
            system_instruction=(
                "You are a helpful customer support assistant. Your job is to answer the user's question "
                "using *only* the context provided. Do not use your own knowledge. "
                "If the context provided does not contain the answer to the question, "
                "you MUST respond with the exact phrase: "
                "I'm sorry, I could not find that information in our knowledge base."
            )
        )

        # HR Assistant
        hr_assistant_model = Genai.GenerativeModel(
            'gemini-2.5-flash-preview-09-2025',
            system_instruction=(
                "You are a helpful HR assistant. "
                "First, try to answer using the provided context. "
                "If the context is missing, you MUST respond with 'I'm sorry, I could not find that information in our knowledge base.' "
                "If you are asked to generate a general answer, be helpful, professional, and concise."
            )
        )

        # Marketing
        marketing_agent_model = Genai.GenerativeModel(
            'gemini-2.5-flash-preview-09-2025', 
            system_instruction="You are a creative marketing assistant. Generate compelling, engaging, and professional content as requested."
        )

        # Analytics (Upgraded)
        analytics_agent_model = Genai.GenerativeModel(
            'gemini-2.5-flash-preview-09-2025', 
            system_instruction=(
                "You are an Expert Data Analyst. Your primary goal is to output structured, quantitative data rather than descriptive text.\n"
                "1. **DATA OVER TEXT:** Prioritize Markdown tables, bulleted lists of metrics, and specific figures over paragraphs.\n"
                "2. **STRICT QUANTIFICATION:** Never use qualitative terms (e.g., 'high growth') without the backing number (e.g., '25% YoY growth').\n"
                "3. **TABULAR FORMAT:** Whenever comparing two or more entities/periods, you MUST use a Markdown table.\n"
                "4. **KEY METRICS:** Isolate key performance indicators (KPIs) at the top of your response.\n"
                "5. **CONCISE ANALYSIS:** Explanations should be brief footnotes to the data, not long narratives."
                
                "6. **CODING RULES:**\n"
                "   - You MUST explicitly `import pandas as pd` and `import numpy as np` if used.\n"
                "   - **NEVER use `pd.np`.** It is deprecated. Always use `np` directly (e.g., `np.nan`, `np.random`).\n"
                "   - **STYLE RULE:** Use `plt.style.use('ggplot')` or `plt.style.use('default')`. **NEVER** use `plt.style.use('matplotlib.rcParams')` as it causes a crash.\n"
                "   - Ensure all graphs use standard matplotlib styles.\n"
            )
        )

        # Admin
        admin_agent_model = Genai.GenerativeModel(
            'gemini-2.5-flash-preview-09-2025',
            system_instruction="You are an admin assistant. Follow the instructions precisely. Respond with only 'Task completed' or 'Error: [reason]'."
        )
        
        # General (Orchestrator)
        general_agent_model = Genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
        
        logging.info("All Agent Models initialized successfully.")

    except Exception as e:
        logging.error(f"Error initializing specialist agent models: {e}")

# --- 4. Initialize Flask App & Firebase ---
app = Flask(__name__)

# CRITICAL FIX for Firebase Hosting:
# Firebase strips all cookies except those named "__session".
app.config['SESSION_COOKIE_NAME'] = '__session' 
app.config['SESSION_COOKIE_SECURE'] = True       # Always True for HTTPS (Production)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'

CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["http://localhost:5173", "http://localhost:3000", "https://aiintensiveproject.web.app/"]}})# <--- ADD THIS (Allows React to send cookies/headers)
app.secret_key = 'srgugrk akkuyawgyawkuygak gfkuygseakhfakuykga'

# --- ROBUST FIREBASE INITIALIZATION ---
firebase_db = None

def init_firebase():
    global firebase_db
    try:
        # 1. Try Local File (Dev)
        if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
            if not firebase_admin._apps:
                cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
                firebase_admin.initialize_app(cred)
            firebase_db = firestore.client()
            logging.info("✅ Firebase initialized with JSON file (Local)")
            return

        # 2. Try Cloud Native (Production)
        # We explicitly fetch default credentials to ensure they exist
        import google.auth
        creds, project = google.auth.default()
        
        if not firebase_admin._apps:
            # Use the discovered project ID or fallback to env var
            pid = project or os.getenv("FIREBASE_PROJECT_ID")
            if not pid:
                raise ValueError("No Project ID found in environment or default credentials.")
                
            logging.info(f"Attempting Firebase init for Project ID: {pid}")
            firebase_admin.initialize_app(credentials.ApplicationDefault(), {
                'projectId': pid,
            })
            
        firebase_db = firestore.client()
        logging.info("✅ Firebase initialized with Default Credentials (Cloud)")

    except Exception as e:
        logging.critical(f"🔥 FATAL: Firebase Initialization Failed: {e}")
        # We intentionally do not raise e here to let the server start and print the error logs,
        # but we log it as critical so you can see it.

# Run the initialization
init_firebase()

# --- 5. HELPER FUNCTIONS (Tools & Logic) ---
# --- HELPER: Process & Ingest Document ---
def ingest_document(file_path, filename):
    try:
        text = ""
        # 1. Extract Text based on extension
        if filename.endswith('.pdf'):
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        else:
            # Assume text file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

        if not text.strip():
            return False, "Empty file"

        # 2. Split Text into Chunks (RAG Best Practice)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        chunks = text_splitter.split_text(text)
        
        # 3. Embed & Save to ChromaDB
        if not rag_collection or not embedding_model:
             return False, "RAG System not initialized"

        # Create unique IDs for chunks
        ids = [f"{filename}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": filename} for _ in range(len(chunks))]
        
        # Embed (Gemini does this automatically via the collection if configured, 
        # but here we pass text and let Chroma call the embedding function if set up, 
        # OR we embed explicitly. Your setup uses embedding_model separately.)
        
        # Explicit Embedding Loop (Robust method)
        embeddings = [embedding_model.embed_query(chunk) for chunk in chunks]
        
        rag_collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        return True, f"Successfully added {len(chunks)} chunks."

    except Exception as e:
        logging.error(f"Ingestion Error: {e}")
        return False, str(e)

# --- NEW: User Management Logic ---
ALLOWED_SUPER_ADMINS = ["nilanjansaha2345@gmail.com", "banerjeemeghamitra@gmail.com"]

def create_system_user(email, password, display_name):
    """
    Creates a user in Firebase Auth and Firestore with the correct role.
    """
    if not firebase_db:
        return {"error": "Firebase not initialized."}

    try:
        # 1. Determine Role
        role = "ADMIN" if email in ALLOWED_SUPER_ADMINS else "EMPLOYEE"
        
        # 2. Create User in Firebase Authentication
        user_record = auth.create_user(
            email=email,
            email_verified=False,
            password=password,
            display_name=display_name,
            disabled=False
        )
        logging.info(f"Successfully created new user: {user_record.uid}")

        # 3. Create User Document in Firestore
        user_data = {
            "uid": user_record.uid,
            "email": email,
            "displayName": display_name,
            "role": role,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "isActive": True
        }
        firebase_db.collection("users").document(user_record.uid).set(user_data)
        logging.info(f"User document created in Firestore for {email} as {role}")

        return {"success": True, "uid": user_record.uid, "role": role, "email": email}

    except Exception as e:
        logging.error(f"Error creating system user: {e}")
        return {"error": str(e)}

def extract_json(text_response):
    """Extracts a JSON object from a text string."""
    try:
        start_index = text_response.find('{')
        if start_index == -1: return None
        end_index = text_response.rfind('}')
        if end_index == -1: return None
        json_str = text_response[start_index:end_index+1]
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logging.error(f"JSON Decode Error: {e}")
        return None

def clean_rag_context(documents: list) -> str:
    full_text = " ".join(documents)
    cleaned_text = re.sub(r'\s+', ' ', full_text).strip()
    return cleaned_text

# --- 5a. Worker Agent Tools ---

def run_worker_agent_bigquery(sql_query: str) -> str:
    logging.info("Worker: Running BigQuery...")
    try:
        SCOPES = ['https://www.googleapis.com/auth/bigquery', 'https://www.googleapis.com/auth/drive.readonly']
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        client = bigquery.Client(credentials=creds, project=PROJECT_ID)
        query_job = client.query(sql_query)
        results = query_job.result()
        output = []
        header = [field.name for field in results.schema]
        output.append(",".join(header))
        for row in results:
            output.append(",".join([str(item) for item in row]))
        return "\n".join(output)
    except Exception as e:
        logging.error(f"BigQuery Error: {e}")
        return f"Error: {e}"

def run_worker_agent_search(instruction: str) -> str:
    logging.info(f"Worker: Searching Google for '{instruction}'...")
    try:
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[google_search_tool])
        
        system_instruction = (
            "You are an Expert Market Intelligence Analyst. Your job is to perform deep, strategic research. "
            "Search for financial data, product strategies, competitor news, market gaps, and launch plans as requested. "
            "Synthesize the search results into a detailed, comprehensive research summary."
        )
        contents = [
            {"role": "user", "parts": [{"text": "Your system prompt is: " + system_instruction}]},
            {"role": "model", "parts": [{"text": "Understood. I will conduct expert market intelligence research."}]},
            {"role": "user", "parts": [{"text": instruction}]}
        ]
        response = genai_client.models.generate_content(
            model="models/gemini-2.5-flash-preview-09-2025", 
            contents=contents,
            config=config
        )
        return response.text
    except Exception as e:
        logging.error(f"Search Error: {str(e)}")
        return f"Error: {str(e)}"

def run_worker_agent_code_execution(python_code: str) -> str:
    logging.info("Worker: Executing Python code...")
    try:
        process = subprocess.run(
            [sys.executable, "-c", python_code],
            capture_output=True, text=True, check=True
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Code execution failed: {e.stderr}")
        return f"Error in code execution: {e.stderr}"

def run_worker_agent_upload_gcs(local_file_path: str, gcs_file_name: str) -> str:
    logging.info(f"Worker: Uploading '{local_file_path}' to GCS...")
    try:
        # 1. Initialize Client (Handle both Local and Cloud)
        storage_client = None
        if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
            creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
            storage_client = storage.Client(credentials=creds, project=PROJECT_ID)
        else:
            # Use Default Cloud Credentials
            storage_client = storage.Client(project=PROJECT_ID)

        # 2. Upload
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_file_name)
        
        # Explicitly set cache control to prevent stale images
        blob.cache_control = "public, max-age=300"
        
        blob.upload_from_filename(local_file_path)
        
        # 3. Ensure it is public (Required for frontend <img> tag)
        # Note: If bucket has "Uniform Bucket Level Access", this specific line might do nothing,
        # but the bucket policy itself handles it.
        # blob.make_public() 

        return blob.public_url
        
    except Exception as e:
        logging.error(f"GCS Upload Error: {e}")
        # Return empty string on failure so frontend doesn't show a broken image icon
        return ""


def run_worker_agent_export_docs(text_content, report_title, user_email):
    logging.info(f"Worker: Creating Google Doc for {user_email}...")
    
    # 1. Validation
    if not SERVICE_ACCOUNT_FILE:
        return "Error: Service Account Credentials missing."
    if not user_email or "@" not in user_email:
        logging.error(f"Invalid email provided for export: {user_email}")
        return "Error: Invalid user email. Cannot share document."

    try:
        # 2. Setup Services
        SCOPES = ['https://www.googleapis.com/auth/documents', 
                  'https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        docs_service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        # 3. Create Document
        title = f"{report_title} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        doc = docs_service.documents().create(body={'title': title}).execute()
        document_id = doc.get('documentId')

        # 4. Insert Content
        requests = [{'insertText': {'location': {'index': 1}, 'text': text_content}}]
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

        # 5. SHARE PERMISSION (The Critical Fix)
        # We allow "writer" access so the user can edit their report
        try:
            drive_service.permissions().create(
                fileId=document_id,
                body={'type': 'user', 'role': 'writer', 'emailAddress': user_email},
                fields='id'
            ).execute()
            logging.info(f"Successfully shared Doc {document_id} with {user_email}")
        except Exception as share_error:
            logging.error(f"Failed to share document: {share_error}")
            return f"Error: Document created but sharing failed. Check server logs."

        return f"https://docs.google.com/document/d/{document_id}/edit"
        
    except Exception as e:
        logging.error(f"Error exporting to Docs: {e}")
        return f"Error: {str(e)}"

def run_worker_agent_export_sheets(csv_data, report_title, user_email):
    logging.info(f"Worker: Creating Google Sheet for {user_email}...")
    
    if not SERVICE_ACCOUNT_FILE: return "Error: Service Account Credentials missing."
    if not user_email or "@" not in user_email: return "Error: Invalid user email."

    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        sheets_service = build('sheets', 'v4', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        # Parse CSV Data
        try:
            f = io.StringIO(csv_data.strip())
            values = list(csv.reader(f))
        except:
            values = [[line] for line in csv_data.split('\n')]

        # Create Sheet
        title = f"{report_title} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        spreadsheet = sheets_service.spreadsheets().create(body={'properties': {'title': title}}).execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')

        # Write Data
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range="Sheet1!A1", valueInputOption="RAW", body={'values': values}
        ).execute()

        # SHARE PERMISSION (The Critical Fix)
        try:
            drive_service.permissions().create(
                fileId=spreadsheet_id,
                body={'type': 'user', 'role': 'writer', 'emailAddress': user_email},
                fields='id'
            ).execute()
            logging.info(f"Successfully shared Sheet {spreadsheet_id} with {user_email}")
        except Exception as share_error:
            logging.error(f"Failed to share sheet: {share_error}")
            return f"Error: Sheet created but sharing failed."

        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        
    except Exception as e:
        logging.error(f"Error exporting to Sheets: {e}")
        return f"Error: {str(e)}"
# --- 5b. Intent Parsing & Strategy ---

def parse_analytics_intent(user_query: str) -> dict:
    logging.info("🧠 Parser: Analyzing analytics intent...")
    prompt = (
        f"Analyze this user query: \"{user_query}\"\n"
        f"Extract the following fields into a JSON object:\n"
        f"1. 'companies': A list of strings of company names mentioned.\n"
        f"2. 'export_format': One of ['docs', 'sheets', 'none'].\n"
        f"3. 'needs_internal_data': Boolean. True if user implies using internal/SQL data.\n"
        f"Output ONLY the JSON."
    )
    try:
        response = analytics_agent_model.generate_content(prompt)
        return extract_json(response.text) or {"companies": [], "export_format": "none", "needs_internal_data": False}
    except Exception:
        return {"companies": [], "export_format": "none", "needs_internal_data": False}

def generate_search_strategy(user_query: str, entity_name: str) -> str:
    logging.info(f"Generating search strategy for '{entity_name}'...")
    prompt = (
        f"User Query: \"{user_query}\"\n"
        f"Target Entity: \"{entity_name}\"\n"
        f"Generate the SINGLE best Google Search query (max 10 words) to find data/strategy for this entity."
    )
    try:
        response = analytics_agent_model.generate_content(prompt)
        return response.text.strip().replace('"', '')
    except Exception:
        return f"{entity_name} financial data 2024"

# --- 5c. Advanced Analytics Pipeline (Ported Logic) ---

def run_analytics_agent_advanced(query: str, user_email: str, use_internal_data: bool = False, custom_sql: str = None):
    if not analytics_agent_model:
        return {"error": "Analytics Agent is not available. Check API Key."}
    
    logging.info(f"Analytics Agent: Starting advanced pipeline for '{query}'")
    
    try:
        # 1. Intent Parsing
        intent = parse_analytics_intent(query)
        companies = intent.get('companies', [])
        needs_internal = use_internal_data if use_internal_data else intent.get('needs_internal_data', False)
        
        data_source_1 = "No data found."
        data_source_2 = "No data found."
        
        # 2. Data Gathering (with Error Safety)
        try:
            if needs_internal:
                sql = custom_sql if custom_sql else "SELECT * FROM `aiintensiveproject.company_data.sales_trends`"
                data_source_1 = run_worker_agent_bigquery(sql)
                if len(companies) >= 1:
                    rival = companies[0]
                    q = generate_search_strategy(query, rival)
                    data_source_2 = run_worker_agent_search(q)
            else:
                if len(companies) >= 1:
                    q1 = generate_search_strategy(query, companies[0])
                    data_source_1 = run_worker_agent_search(q1)
                if len(companies) >= 2:
                    q2 = generate_search_strategy(query, companies[1])
                    data_source_2 = run_worker_agent_search(q2)
                elif len(companies) == 0:
                    # Fallback for general queries
                    data_source_1 = run_worker_agent_search(query)

        except Exception as tool_err:
            logging.error(f"Tool Execution Failed: {tool_err}")
            data_source_1 = f"Error gathering data: {str(tool_err)}"

        # 3. Analysis & Graphing & CSV Extraction
        local_graph_file = f"temp_app_graph_{datetime.datetime.now().timestamp()}.png"
        
        # UPDATED PROMPT: Explicitly asks for csv_data
        prompt = (
            f"You are a world-class data analyst. Perform analysis.\n"
            f"USER QUERY: \"{query}\"\n"
            f"DATA SOURCE 1:\n{data_source_1}\n"
            f"DATA SOURCE 2:\n{data_source_2}\n"
            f"TASKS:\n"
            f"1. Summarize findings quantitatively in Markdown.\n"
            f"2. EXTRACT the key data points into a clean CSV string (headers and rows) suitable for Excel.\n"
            f"3. Write Python code (pandas/matplotlib) to plot charts IF data allows. Save as '{local_graph_file}'. Do NOT add data labels.\n"
            f"Respond JSON: {{ \"text_summary\": \"...\", \"csv_data\": \"...\", \"python_graph_code\": \"...\" }}"
        )
        
        response = analytics_agent_model.generate_content(prompt)
        
        # Safety Check
        if not response.parts:
            return {"error": "AI Safety Filter triggered. Please rephrase your query."}

        report = extract_json(response.text)
        
        # Fallback if JSON extraction fails
        if not report: 
            logging.error("Failed to extract JSON from model response")
            return {
                "summary": response.text, 
                "graph_url": "", 
                "csv_data": "", 
                "raw_data_1": str(data_source_1)
            }
        
        summary = report.get("text_summary", "No summary generated.")
        csv_data = report.get("csv_data", "") # <--- Extract CSV
        code = report.get("python_graph_code", "")
        
        graph_url = ""
        if "import" in code:
            try:
                exec_result = run_worker_agent_code_execution(code)
                if os.path.exists(local_graph_file):
                    gcs_name = f"analytics_{datetime.datetime.now().timestamp()}.png"
                    graph_url = run_worker_agent_upload_gcs(local_graph_file, gcs_name)
                    os.remove(local_graph_file)
                elif "Error" in exec_result:
                    logging.warning(f"Graph Code Execution Failed: {exec_result}")
            except Exception as graph_err:
                logging.error(f"Graph Generation Error: {graph_err}")

        return {
            "summary": summary,
            "graph_url": graph_url,
            "csv_data": csv_data, # <--- Return CSV to frontend
            "raw_data_1": str(data_source_1)[:1000] # Limit size
        }

    except Exception as e:
        logging.error(f"Analytics Pipeline Critical Failure: {e}")
        return {"error": f"Server Error: {str(e)}"}


# --- 5d. Agent Execution Functions (Existing) ---

def query_rag(query_text: str, n_results: int = 3):
    if not rag_collection or not embedding_model:
        return [], []
    try:
        query_embedding = embedding_model.embed_query(query_text)
        results = rag_collection.query(query_embeddings=[query_embedding], n_results=n_results)
        return results.get('documents', [[]])[0], results.get('metadatas', [[]])[0] 
    except Exception as e:
        logging.error(f"Error querying RAG: {e}")
        return [], []

def run_customer_support_agent(query: str):
    if not customer_support_model:
        return "Error: Agent unavailable."
    logging.info(f"Customer Agent: RAG search for '{query}'")
    documents, _ = query_rag(query)
    rag_response = ""
    
    if documents:
        context = clean_rag_context(documents)
        prompt = f"Context:\n{context}\n\nQuestion:\n{query}"
        try:
            rag_response = customer_support_model.generate_content(prompt).text
        except Exception as e:
            rag_response = f"Error: {e}"
    else:
        rag_response = "I'm sorry, I could not find that information in our knowledge base."

    if "i'm sorry" in rag_response.lower():
        logging.info("Customer Agent: Fallback to Search.")
        return run_worker_agent_search(query)
    return rag_response

def run_hr_assistant_agent(query: str):
    if not hr_assistant_model: return "Error: Agent unavailable."
    documents, _ = query_rag(query)
    rag_response = ""
    if documents:
        context = clean_rag_context(documents)
        prompt = f"Context:\n{context}\n\nQuestion:\n{query}"
        try:
            rag_response = hr_assistant_model.generate_content(prompt).text
        except: rag_response = "Error"
    else:
        rag_response = "I'm sorry..."
    
    if "i'm sorry" in rag_response.lower():
        logging.info("HR Agent: Fallback to Search.")
        search_res = run_worker_agent_search(query)
        return search_res
    return rag_response

def run_marketing_agent(query: str):
    if not marketing_agent_model: return "Error: Agent unavailable."
    return marketing_agent_model.generate_content(query).text

def run_admin_agent(query: str):
    if not admin_agent_model: return "Error: Agent unavailable."
    return admin_agent_model.generate_content(query).text

# --- 5e. General Agent (Orchestrator) ---
def run_general_agent_orchestrator(query: str, user_role: str, user_email: str, user_name: str):
    if not general_agent_model: return "Error: General Agent not initialized."

    # 1. Classification
    classification_prompt = (
        f"Classify the query into: HR_ASSISTANT, CUSTOMER_SUPPORT, MARKETING, ANALYTICS, ADMIN, GENERAL_CHAT.\n"
        f"Rules: 'sales', 'revenue', 'trends', 'competitor', 'compare' -> ANALYTICS.\n"
        f"Query: '{query}'\nResponse (Category only):"
    )
    try:
        intent = general_agent_model.generate_content(classification_prompt).text.strip().upper()
        logging.info(f"Orchestrator: Intent = {intent}")
    except: return "Error in classification."

    # 2. Access Control
    allowed = False
    if user_role == "PUBLIC": allowed = (intent in ["CUSTOMER_SUPPORT", "GENERAL_CHAT"])
    elif user_role == "EMPLOYEE": allowed = (intent in ["HR_ASSISTANT", "CUSTOMER_SUPPORT", "MARKETING", "ANALYTICS", "GENERAL_CHAT"])
    elif user_role == "ADMIN": allowed = True
    
    if not allowed: return f"Access Denied: {user_role} cannot access {intent}."

    # 3. Context Injection
    user_context_header = f"USER CONTEXT: Name='{user_name}', Email='{user_email}', Role='{user_role}'\n\n"

    # 4. Routing
    if intent == "ANALYTICS":
        result = run_analytics_agent_advanced(query, user_email)
        if isinstance(result, dict):
            final_text = f"{result['summary']}\n\n"
            if result.get('graph_url'): final_text += f"**Graph:** ![Graph]({result['graph_url']})"
            return final_text
        return str(result)
        
    elif intent == "CUSTOMER_SUPPORT": 
        return run_customer_support_agent(user_context_header + query)
    elif intent == "HR_ASSISTANT": 
        return run_hr_assistant_agent(user_context_header + query)
    elif intent == "MARKETING": 
        return run_marketing_agent(user_context_header + query)
    elif intent == "ADMIN": 
        return run_admin_agent(query)
    else: 
        # General Chat with Context
        return general_agent_model.generate_content(
            f"You are a helpful enterprise assistant. {user_context_header} Query: {query}"
        ).text
# --- HELPER: Send Welcome Email ---
def send_welcome_email(recipient_email, display_name, password, role):
    sender_email = os.getenv("EMAIL_SENDER_ADDRESS")
    sender_password = os.getenv("EMAIL_SENDER_APP_PASSWORD")
    
    if not sender_email or not sender_password:
        logging.error("Email credentials missing in .env")
        return False

    # Email Content (HTML)
    subject = "Welcome to Enterprise Agent Hub - Your Account Details"
    
    # Define access based on role
    access_list = "<li>General Chat Assistant</li>"
    if role == "EMPLOYEE" or role == "ADMIN":
        access_list += """
            <li>Analytics Studio (Market Research & Data Visualization)</li>
            <li>HR & Marketing Agents</li>
            <li>Document Generation Tools</li>
        """
    if role == "ADMIN":
        access_list += "<li><strong>Admin Dashboard (User Management)</strong></li>"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
          
          <div style="background-color: #2563eb; padding: 20px; text-align: center;">
            <h2 style="color: white; margin: 0;">Welcome to Enterprise Agent Hub</h2>
          </div>
          
          <div style="padding: 30px;">
            <p>Hello <strong>{display_name}</strong>,</p>
            <p>Your account has been successfully provisioned. You now have access to our AI-powered workforce platform.</p>
            
            <div style="background-color: #f8fafc; border-left: 4px solid #2563eb; padding: 15px; margin: 20px 0;">
              <p style="margin: 0 0 10px 0;"><strong>Your Login Credentials:</strong></p>
              <p style="margin: 5px 0;">📧 Email: {recipient_email}</p>
              <p style="margin: 5px 0;">🔑 Temporary Password: <strong>{password}</strong></p>
            </div>

            <p><strong>Your Access Level: {role}</strong></p>
            <ul>
              {access_list}
            </ul>

            <p>Please log in and change your password if necessary.</p>
            
            <div style="text-align: center; margin-top: 30px;">
              <a href="http://localhost:5173/login" style="background-color: #0f172a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Login to Dashboard</a>
            </div>
          </div>
          
          <div style="background-color: #f1f5f9; padding: 15px; text-align: center; font-size: 12px; color: #64748b;">
            &copy; 2025 Enterprise Agent Hub. All rights reserved.<br>
            This is an automated system message.
          </div>
        </div>
      </body>
    </html>
    """

    try:
        # Create Message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = recipient_email
        message.attach(MIMEText(html_content, "html"))

        # Send Email via Gmail SMTP
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        
        logging.info(f"Welcome email sent to {recipient_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False

# --- 6. API Endpoints ---

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Hello from Enterprise Agent Hub!"})

@app.route('/api/config', methods=['GET'])
def api_config():
    """
    Serves public configuration to the frontend.
    NEVER return your Client Secret or Service Account Keys here.
    """
    # Option A: If you have them in .env
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    
    # Option B: If you rely on client_secret.json, we can read it dynamically
    if not client_id and os.path.exists('client_secret.json'):
        try:
            with open('client_secret.json', 'r') as f:
                data = json.load(f)
                # Usually located at installed.client_id or web.client_id
                client_id = data.get('installed', {}).get('client_id') or \
                            data.get('web', {}).get('client_id')
        except Exception as e:
            logging.error(f"Error reading client_secret.json: {e}")

    return jsonify({
        "apiKey": os.getenv("GOOGLE_API_KEY"), 
        "clientId": client_id
    })

# --- NEW: Admin Endpoint to Create System User ---
@app.route('/api/admin/create-user', methods=['POST'])
def api_create_user():
    """
    Creates user and sends welcome email.
    Only ADMINs can call this.
    """
    # 1. Security Checks
    if 'user_role' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    if session['user_role'] != 'ADMIN':
        requester_email = session.get('user_email', '')
        if requester_email not in ALLOWED_SUPER_ADMINS:
            return jsonify({"error": "Forbidden"}), 403

    # 2. Parse Data
    data = request.json
    email = data.get('email')
    password = data.get('password')
    display_name = data.get('display_name')

    if not email or not password or not display_name:
        return jsonify({"error": "Missing fields"}), 400

    # 3. Create User in Firebase
    result = create_system_user(email, password, display_name)
    
    if "error" in result:
        return jsonify(result), 500

    # 4. SEND EMAIL (This is the part that was missing!)
    logging.info(f"Attempting to send email to {email}...") # <--- Debug Log
    email_sent = send_welcome_email(email, display_name, password, result['role'])
    
    if email_sent:
        logging.info(f"Email notification sent to {email}")
    else:
        logging.warning(f"Failed to send email to {email}")

    return jsonify({
        "success": True, 
        "uid": result['uid'], 
        "role": result['role'], 
        "email": result['email'],
        "email_sent": email_sent
    }), 201

# --- API: Upload Endpoint ---
@app.route('/api/admin/upload-knowledge', methods=['POST'])
def upload_knowledge():
    # Security Check
    if 'user_role' not in session or session['user_role'] != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)
        save_path = os.path.join("temp_uploads", filename)
        
        # Ensure temp directory exists
        if not os.path.exists("temp_uploads"):
            os.makedirs("temp_uploads")
            
        file.save(save_path)
        
        # Process in background (simplified here to synchronous for immediate feedback)
        success, message = ingest_document(save_path, filename)
        
        # Clean up
        os.remove(save_path)
        
        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"error": message}), 500


# --- UPDATED: Login Endpoint with Firestore Verification ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not data or 'email' not in data or 'uid' not in data:
        return jsonify({"error": "Missing email or uid"}), 400
    
    email = data['email']
    uid = data['uid']
    
    try:
        user_ref = firebase_db.collection("users").document(uid)
        user_doc = user_ref.get()
        
        display_name = "User" # Default
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            role = user_data.get("role", "PUBLIC")
            display_name = user_data.get("displayName", "User") # <--- Get Name
        else:
            role = "ADMIN" if email in ALLOWED_SUPER_ADMINS else "PUBLIC"
            display_name = email.split('@')[0]
            user_ref.set({
                "uid": uid,
                "email": email,
                "displayName": display_name,
                "role": role,
                "createdAt": firestore.SERVER_TIMESTAMP
            })
            
        session['user_role'] = role
        session['user_email'] = email
        session['user_uid'] = uid
        session['user_name'] = display_name # <--- SAVE TO SESSION
        
        return jsonify({"message": "Login successful", "role": role})

    except Exception as e:
        logging.error(f"Login error: {e}")
        return jsonify({"error": str(e)}), 500 

@app.route('/api/logout', methods=['POST'])
def logout_endpoint():
    session.clear() # This wipes user_uid, user_role, etc. from server memory
    return jsonify({"message": "Logged out"}), 200   

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'user_role' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    query = data.get('query')
    session_id = data.get('session_id')
    
    if not query: return jsonify({"error": "Missing query"}), 400
    
    # 1. Generate Response (Pass user_name from session)
    response_text = run_general_agent_orchestrator(
        query, 
        session['user_role'], 
        session.get('user_email'),
        session.get('user_name', 'User') # <--- NEW
    )
    
    # 2. Save to Firestore (Persistence)
    try:
        user_uid = session.get('user_uid')
        if user_uid:
            timestamp = firestore.SERVER_TIMESTAMP
            
            new_msgs = [
                {"role": "user", "content": query, "timestamp": datetime.datetime.now().isoformat()},
                {"role": "bot", "content": response_text, "timestamp": datetime.datetime.now().isoformat()}
            ]
            
            if session_id:
                ref = firebase_db.collection('chat_sessions').document(session_id)
                ref.update({
                    "messages": firestore.ArrayUnion(new_msgs),
                    "updated_at": timestamp
                })
            else:
                title = " ".join(query.split()[:5])
                new_doc = firebase_db.collection('chat_sessions').document()
                new_doc.set({
                    "user_id": user_uid,
                    "title": title,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "messages": new_msgs
                })
                session_id = new_doc.id

    except Exception as e:
        logging.error(f"DB Save Error: {e}")
    
    return jsonify({
        "query": query, 
        "response": response_text, 
        "session_id": session_id
    })        # We don't crash the chat if DB fails, we just log it
    
    return jsonify({
        "query": query, 
        "response": response_text, 
        "session_id": session_id # <--- Return this so Frontend can update URL
    })
# --- CHAT HISTORY ENDPOINTS ---

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    if 'user_uid' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        sessions_ref = firebase_db.collection('chat_sessions')
        query = sessions_ref.where('user_id', '==', session['user_uid']).order_by('updated_at', direction=firestore.Query.DESCENDING)
        docs = query.stream()
        
        history = []
        for doc in docs:
            data = doc.to_dict()
            history.append({
                "id": doc.id,
                "title": data.get('title', 'New Chat'),
                "date": data.get('updated_at'),
                "type": data.get('type', 'chat') # <--- NEW: Send the type
            })
            
        return jsonify(history)
    except Exception as e:
        logging.error(f"Fetch History Error: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/chat/session/<session_id>', methods=['GET'])
def get_chat_session(session_id):
    if 'user_uid' not in session: return jsonify({"error": "Unauthorized"}), 401

    try:
        doc_ref = firebase_db.collection('chat_sessions').document(session_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({"error": "Session not found"}), 404
            
        data = doc.to_dict()
        # Security check: Ensure this session belongs to the logged-in user
        if data.get('user_id') != session['user_uid']:
            return jsonify({"error": "Forbidden"}), 403
            
        return jsonify(data) # Returns { messages: [...], title: ... }
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/session/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    if 'user_uid' not in session: return jsonify({"error": "Unauthorized"}), 401
    try:
        firebase_db.collection('chat_sessions').document(session_id).delete()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- NEW ANALYTICS ENDPOINTS ---

@app.route('/api/analytics/analyze', methods=['POST'])
def analytics_analyze():
    if 'user_role' not in session: return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    query = data.get('query')
    use_internal = data.get('use_internal_data', False)
    sql_query = data.get('sql_query')
    user_email = session.get('user_email') or DEFAULT_USER_EMAIL
    user_uid = session.get('user_uid') # Need this to save session

    # 1. Run the existing analysis logic
    result = run_analytics_agent_advanced(query, user_email, use_internal_data=use_internal, custom_sql=sql_query)
    
    if "error" in result:
        return jsonify(result), 500

    # 2. AUTO-SAVE: Save this report as a Chat Session
    try:
        if user_uid:
            # Construct the "Bot Message" using Markdown
            # We embed the graph as a Markdown Image so the Chat UI can render it
            markdown_content = f"{result['summary']}\n\n"
            if result.get('graph_url'):
                markdown_content += f"![Generated Graph]({result['graph_url']})\n\n"
            if result.get('raw_data_1'):
                markdown_content += f"**Source Data Preview:**\n```csv\n{result['raw_data_1'][:300]}...\n```"

            timestamp = firestore.SERVER_TIMESTAMP
            
            new_msgs = [
                {"role": "user", "content": f"Run analysis: {query}", "timestamp": datetime.datetime.now().isoformat()},
                {"role": "bot", "content": markdown_content, "timestamp": datetime.datetime.now().isoformat()}
            ]
            
            # Create Session with type='analytics'
            new_doc = firebase_db.collection('chat_sessions').document()
            new_doc.set({
                "user_id": user_uid,
                "title": f"📊 {query[:40]}...", # Add emoji to title for flair
                "created_at": timestamp,
                "updated_at": timestamp,
                "messages": new_msgs,
                "type": "analytics" # <--- Special Flag
            })
            
            # We return the session_id so the UI could optionally redirect there
            result['saved_session_id'] = new_doc.id

    except Exception as e:
        logging.error(f"Failed to auto-save analytics session: {e}")
        # Don't fail the request, just log it

    return jsonify(result)

@app.route('/api/analytics/export', methods=['POST'])
def analytics_export():
    if 'user_role' not in session: return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    export_type = data.get('export_type')
    content = data.get('content')
    user_email = session.get('user_email') or DEFAULT_USER_EMAIL
    
    link = ""
    if export_type == 'docs':
        link = run_worker_agent_export_docs(content, "Analytics Export", user_email)
    elif export_type == 'sheets':
        link = run_worker_agent_export_sheets(content, "Analytics Data", user_email)
    
    return jsonify({"link": link})


# --- NEW: Get All Users (Admin Only) ---
@app.route('/api/admin/users', methods=['GET'])
def get_all_users():
    if session.get('user_role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Fetch all users from Firestore
        users_ref = firebase_db.collection('users')
        docs = users_ref.stream()
        
        users_list = []
        for doc in docs:
            data = doc.to_dict()
            # Clean up data for frontend
            users_list.append({
                "uid": data.get('uid'),
                "email": data.get('email'),
                "display_name": data.get('displayName', 'Unknown'),
                "role": data.get('role', 'EMPLOYEE'),
                "created_at": data.get('createdAt')
            })
            
        return jsonify(users_list)
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        return jsonify({"error": str(e)}), 500

# --- NEW: Delete User (Admin Only) ---
@app.route('/api/admin/users/<uid>', methods=['DELETE'])
def delete_system_user_endpoint(uid):
    if session.get('user_role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    # Prevent Admin from deleting themselves
    if uid == session.get('user_uid'):
        return jsonify({"error": "You cannot delete your own account."}), 400

    try:
        # 1. Delete from Firebase Authentication (Login)
        try:
            auth.delete_user(uid)
            logging.info(f"Deleted user {uid} from Auth")
        except Exception as auth_error:
            # If user not found in Auth, continue to delete DB record anyway
            logging.warning(f"User {uid} not found in Auth or already deleted: {auth_error}")

        # 2. Delete from Firestore (Profile Data)
        firebase_db.collection('users').document(uid).delete()
        
        # 3. Optional: Delete their Chat History to clean up
        # (This is a heavy operation, so usually we skip it or do it in background, 
        # but here is how you would do it simply)
        chats = firebase_db.collection('chat_sessions').where('user_id', '==', uid).stream()
        for chat in chats:
            chat.reference.delete()

        logging.info(f"Successfully deleted user {uid} and their data.")
        return jsonify({"success": True})

    except Exception as e:
        logging.error(f"Delete User Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)