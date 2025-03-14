import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama.embeddings import OllamaEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct  

# Initialize Qdrant (in-memory for testing)
client = QdrantClient(":memory:")

# Create a Qdrant collection (ensure vector size matches embeddings)
client.recreate_collection(
    collection_name="mhealth_vectors",
    vectors_config=VectorParams(size=4096, distance=Distance.COSINE)
)

# Function to load PDF documents
def load_documents(pdf_path=None):
    docs = []
    
    if pdf_path:  # If a specific file is provided (uploaded file)
        loader = PyPDFLoader(pdf_path)
        docs.extend(loader.load())
    else:  # If processing all PDFs in `data/`
        for file in os.listdir("data"):
            if file.endswith(".pdf"):
                loader = PyPDFLoader(os.path.join("data", file))
                docs.extend(loader.load())
    
    return docs


# Function to split text into chunks
def split_documents(documents):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_documents(documents)

# Function to store embeddings in Qdrant
def store_embeddings(text_chunks):
    embedding_model = OllamaEmbeddings(model="mistral")  # ✅ Always use Mistral for document embeddings
    vector_data = [embedding_model.embed_query(chunk.page_content) for chunk in text_chunks]

    points = [
        PointStruct(
            id=i,
            vector=vector,
            payload={"text": text_chunks[i].page_content}
        )
        for i, vector in enumerate(vector_data)
    ]

    client.upsert(collection_name="mhealth_vectors", points=points)

# Function to query Qdrant
def query_qdrant(query_text):
    print("in rag pipeline")
    embedding_model = OllamaEmbeddings(model="mistral")  # ✅ Match storage embeddings (4096-dim)
    query_vector = embedding_model.embed_query(query_text)

    search_results = client.search(collection_name="mhealth_vectors", query_vector=query_vector, limit=3)
    print("completed query qdrant")

    return [result.payload["text"] for result in search_results]
