import os
import shutil
import chromadb
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---

# --- MODIFICATION: Make the .env path absolute to this file's location ---
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv(dotenv_path=dotenv_path)

# 1. Define the path to your source documents (the "Assets" folder)
SOURCE_DOCUMENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Assets'))

# 2. Define the path where the ChromaDB will be stored
PERSIST_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), 'chroma_db'))

# 3. Define the name for your RAG collection
COLLECTION_NAME = "RAGdataset"

# 4. Configure chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

# --- --- ---

def generate_rag_dataset():
    """
    Loads PDF documents from the SOURCE_DOCUMENTS_DIR,
    splits them, creates embeddings, and stores
    them in a persistent ChromaDB collection.
    """
    
    # Configure the Gemini embedding model
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        # Add a check to see if the .env file was even found
        if not os.path.exists(dotenv_path):
            print(f"Error: .env file not found at {dotenv_path}")
            return
        raise ValueError("GOOGLE_API_KEY not found in .env file. Please check spelling inside the file.")
    
    genai.configure(api_key=google_api_key)
    embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # --- 1. Load Documents ---
    print(f"Loading documents from: {SOURCE_DOCUMENTS_DIR}")
    
    if not os.path.exists(SOURCE_DOCUMENTS_DIR):
        print(f"Error: Source directory not found: {SOURCE_DOCUMENTS_DIR}")
        print("Please make sure you have an 'Assets' folder at the root of your project.")
        return

    loader = DirectoryLoader(
        SOURCE_DOCUMENTS_DIR,
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True,
        use_multithreading=True
    )
    
    try:
        documents = loader.load()
    except Exception as e:
        print(f"Error loading documents: {e}")
        return

    if not documents:
        print("No PDF documents found to process.")
        return

    print(f"Loaded {len(documents)} PDF document(s).")

    # --- 2. Split Documents ---
    print(f"Splitting documents into chunks (Chunk size: {CHUNK_SIZE})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    docs = text_splitter.split_documents(documents)
    
    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]

    print(f"Created {len(docs)} text chunks.")

    # --- 3. Initialize ChromaDB & Store ---
    
    if os.path.exists(PERSIST_DIRECTORY):
        print(f"Removing old database at: {PERSIST_DIRECTORY}")
        shutil.rmtree(PERSIST_DIRECTORY)

    print(f"Initializing persistent ChromaDB at: {PERSIST_DIRECTORY}")
    client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)

    print(f"Creating or getting collection: {COLLECTION_NAME}")
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"} 
    )

    print("Generating embeddings and adding documents to ChromaDB...")
    
    embedded_texts = embedding_model.embed_documents(texts)
    
    ids = [f"doc_chunk_{i}" for i in range(len(docs))]

    collection.add(
        embeddings=embedded_texts,
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )

    print("\n--- Success! ---")
    print(f"RAG dataset generation complete.")
    print(f"Total chunks added: {len(docs)}")
    print(f"Collection '{COLLECTION_NAME}' created in {PERSIST_DIRECTORY}")


if __name__ == "__main__":
    generate_rag_dataset()