from dotenv import load_dotenv
import os
import re
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
import pickle

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Define paths
training_folder = Path("Training")
faiss_folder = Path("FAISS")
faiss_folder.mkdir(exist_ok=True)  # Ensure FAISS directory exists

# Initialize embedding function
embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Create Document object
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

# Generate Vector store for a pdf
def generate_vector_store(pdf_path):
    # Extract text from PDF
    pdfreader = PdfReader(pdf_path)
    pdf_text = "\n".join(filter(None, (page.extract_text() for page in pdfreader.pages)))

    split_docs = text_splitter.split_documents([Document(page_content=pdf_text, metadata={"source": pdf_path})])
    texts = [doc.page_content for doc in split_docs]

    # Create FAISS index
    faiss_vector_store = FAISS.from_texts(texts, embedding_function)

    return faiss_vector_store

#=============Processing Weekly Data==================

# Process WeekX.pdf files
for filename in os.listdir(training_folder):
    match = re.match(r"Week(\d+)\.pdf", filename)  # Match 'WeekX.pdf' files only
    if match:
        week_number = int(match.group(1))  # Extract week number
        pdf_path = os.path.join(training_folder, filename)

        faiss_vector_store = generate_vector_store(pdf_path)
        faiss_index_path = faiss_folder / f"faiss_index_week{week_number}.pkl"

        with open(faiss_index_path, "wb") as f:
            pickle.dump(faiss_vector_store, f)

        print(f"Stored FAISS index for Week {week_number}")

#=============Processing Combined Data==================

pdf_path = os.path.join(training_folder, "all_weeks.pdf")
faiss_vector_store = generate_vector_store(pdf_path)
faiss_index_path = faiss_folder / f"faiss_index_all_weeks.pkl"

with open(faiss_index_path, "wb") as f:
    pickle.dump(faiss_vector_store, f)

print(f"Stored FAISS index for combined data")