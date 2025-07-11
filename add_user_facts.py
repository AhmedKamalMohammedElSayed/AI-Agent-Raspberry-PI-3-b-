import chromadb
from datetime import datetime
from haystack.components.embedders import OpenAITextEmbedder
import uuid
from dotenv import load_dotenv
from rag_config import USER_NAME

load_dotenv()
chroma_client = chromadb.PersistentClient(path="data/databases/chroma_db")
collection = chroma_client.create_collection(name="conversations")
# collection = chroma_client.create_collection(name="conversations", configuration={"hnsw": {"space": "cosine"}})

def add_user_facts():
    try:
        embedder = OpenAITextEmbedder(model="text-embedding-3-large")
        facts = [
            f"{USER_NAME} is a male, married, and the father of two children.",
            f"{USER_NAME} is 44 years old and was born on February 2, 1979.",
            f"{USER_NAME} has a Bachelor of Science in Computer Science from the University of California, Berkeley."
        ]
        
        embeddings = [embedder.run(fact) for fact in facts]
        documents = []
        for i, fact in enumerate(facts):
            documents.append({
                "id": str(uuid.uuid4()),
                "content": fact,
                "embedding": embeddings[i]['embedding'],
                "metadata": {
                    "type": "fact",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        
        collection.add(
            ids=[doc["id"] for doc in documents],
            embeddings=[doc["embedding"] for doc in documents],
            documents=[doc["content"] for doc in documents],
            metadatas=[doc["metadata"] for doc in documents]
        )
        
        print("User facts added to ChromaDB successfully!")
        
    except Exception as e:
        raise RuntimeError(f"Error adding user facts: {str(e)}")

add_user_facts()