import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

# Configuration
KB_DIR = "knowledge_base"
DB_DIR = "chroma_db"
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

def ingest_knowledge_base():
    print(f"--- STARTING INGESTION FROM {KB_DIR} ---")
    
    # 1. Load documents
    # Load Markdown files
    md_loader = DirectoryLoader(KB_DIR, glob="**/*.md", loader_cls=TextLoader)
    md_docs = md_loader.load()
    print(f"Loaded {len(md_docs)} Markdown documents.")
    
    # Load PDF files
    pdf_docs = []
    for file in os.listdir(KB_DIR):
        if file.endswith(".pdf"):
            pdf_path = os.path.join(KB_DIR, file)
            loader = PyPDFLoader(pdf_path)
            pdf_docs.extend(loader.load())
    print(f"Loaded {len(pdf_docs)} PDF pages.")
    
    all_docs = md_docs + pdf_docs
    
    # 2. Chunk documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(all_docs)
    print(f"Split into {len(chunks)} chunks.")
    
    # 3. Create embeddings and store in Chroma
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=GOOGLE_API_KEY
    )
    
    print(f"Creating vector store in {DB_DIR}...")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    
    print("--- INGESTION COMPLETED ---")

if __name__ == "__main__":
    if not GOOGLE_API_KEY:
        print("Error: GEMINI_API_KEY not found in .env")
    else:
        ingest_knowledge_base()
