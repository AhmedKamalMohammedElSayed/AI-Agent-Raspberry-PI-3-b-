from datetime import datetime
from rag_pipeline import RAGPipeline
import numpy as np
import uuid
import chromadb

class ConversationSummarizer:
    def __init__(self, rag_pipeline: RAGPipeline):
        self.rag_pipeline = rag_pipeline
        self.collection = chromadb.PersistentClient(path="data/databases/chroma_db").get_or_create_collection(name="conversations")
        
    def process_conversation(self, conversation_count, conversation_count_threshold):
        """Process a new conversation and trigger summarization if needed"""
        if conversation_count >= conversation_count_threshold:
            print("\nSummarizing conversations...")
            self.summarize_conversations()
            
    def summarize_conversations(self):
        """Summarize and cluster recent conversations"""
        results = self.collection.get(
            include=["documents", "embeddings"],
            where={
                # "timestamp": {"$gte": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")},
                "type": {"$ne": "summary"}
            }
        )

        if not results["documents"]:
            print("No conversations to summarize!\n")
            return
            
        clusters = self._cluster_conversations(results["documents"], results["embeddings"].tolist())
        print("Clustering finished!")

        summaries = []
        for cluster in clusters:
            cluster_text = "\n\n".join(cluster)
            summary = self._summarize_cluster(cluster_text)
            summaries.append(summary)
        
        print("Summarizing of Clusters finished!")
        self._save_summaries(summaries)

    def _cluster_conversations(self, documents, embeddings):
        """Cluster conversations based on similarity with all previous documents"""
        clusters = []

        for doc, embedding in zip(documents, embeddings):
            added_to_cluster = False

            for cluster in clusters:
                similarities = [
                    self._calculate_similarity(prev_emb, embedding)
                    for prev_emb in cluster["embeddings"] #All embeddings in one cluster
                ]
                if any(sim >= 0.6 for sim in similarities):
                    cluster["documents"].append(doc)
                    cluster["embeddings"].append(embedding)
                    added_to_cluster = True
                    break

            if not added_to_cluster:
                # Create new cluster
                clusters.append({
                    "documents": [doc],
                    "embeddings": [embedding]
                })


        final_clusters = [cluster["documents"] for cluster in clusters]
        return final_clusters
        
    def _calculate_similarity(self, emb1, emb2):
        """Calculate cosine similarity between two embeddings"""
        emb1 = np.array(emb1)
        emb2 = np.array(emb2)
        
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        return dot_product / (norm1 * norm2)
        
    def _summarize_cluster(self, cluster_text):
        """Summarize a cluster of conversations"""
        prompt = f"""
            You are {self.rag_pipeline.user_name}'s helpful assistant. Summarize the following cluster of statements regarding {self.rag_pipeline.user_name} and mention the date IF mentioned:
            {cluster_text}
            
            Do not begin the summary with phrases like 'Here is a summary' or 'The main topic discussed is.' 
            Start directly with the content of the summary.
        """
        
        result = self.rag_pipeline.generator.run(prompt)
        return result["replies"][0]
        
    def _save_summaries(self, summaries):
        """Save summaries and update the document store"""
        try:
            client = chromadb.PersistentClient(path="data/databases/chroma_db")
            collection_name = "conversations"
            temp_collection_name = "conversations_temp"

            # Fetch all 'summary' documents from the old collection
            print("Fetching all summary documents from the old collection...")
            old_collection = client.get_or_create_collection(name=collection_name)
            summary_all_docs = old_collection.get(include=['metadatas', 'documents', 'embeddings'],
                                          where={"type": {"$eq": "summary"}})

            summary_docs = []
            for i, meta in enumerate(summary_all_docs['metadatas']):
                summary_docs.append({
                        'id': str(uuid.uuid4()),
                        'content': summary_all_docs['documents'][i],
                        'embedding': summary_all_docs['embeddings'][i],
                        'metadata': meta
                    })

            # Create a new collection
            print("Creating a new collection...")
            temp_collection = client.get_or_create_collection(name=temp_collection_name)

            # Copy existing summary docs to the new collection
            print("Copying existing summary docs to the new collection...")
            if summary_docs:
                temp_collection.add(
                    ids=[doc['id'] for doc in summary_docs],
                    embeddings=[doc['embedding'] for doc in summary_docs],
                    documents=[doc['content'] for doc in summary_docs],
                    metadatas=[doc['metadata'] for doc in summary_docs]
                )

            # Add new summaries to the new collection
            print("Adding new summaries to the new collection...")
            for summary in summaries:
                embedding = self.rag_pipeline.embedder.run(summary)
                document = {
                    "id": str(uuid.uuid4()),
                    "content": summary,
                    "embedding": embedding['embedding'],
                    "metadata": {
                        "type": "summary",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
                temp_collection.add(
                    ids=[document["id"]],
                    embeddings=[document["embedding"]],
                    documents=[document["content"]],
                    metadatas=[document["metadata"]]
                )

            # Delete the old collection
            print("Deleting the old collection...")
            old_collection.delete(where={"type": {"$ne": "ayhaga"}})
            client.delete_collection(name=collection_name)

            # Change the temp collection to be the new one
            temp_collection.modify(name=collection_name)

            print(f"Added {len(summaries)} summaries to database!")
            print("Summarized conversations!")
                
        except Exception as e:
            print(f"Error saving summaries or updating document store: {str(e)}")
