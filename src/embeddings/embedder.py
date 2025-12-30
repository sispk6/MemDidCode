"""
Embedding generator using sentence-transformers.
Path: src/embeddings/embedder.py
"""
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:
    """Generate embeddings for text using sentence-transformers"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedder with specified model.
        
        Args:
            model_name: Name of sentence-transformers model
        """
        self.model_name = model_name
        print(f"[INFO] Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"[OK] Model loaded successfully!")
        print(f"   Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text string
            
        Returns:
            Numpy array of embedding vector
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            dim = self.model.get_sentence_embedding_dimension()
            return np.zeros(dim)
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def embed_batch(self, texts: List[str], batch_size: int = 32, show_progress: bool = True) -> np.ndarray:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of text strings
            batch_size: Number of texts to process at once
            show_progress: Show progress bar
            
        Returns:
            Numpy array of shape (n_texts, embedding_dim)
        """
        if not texts:
            return np.array([])
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def embed_messages(self, messages: List[dict], text_key: str = 'embedding_text') -> List[dict]:
        """
        Add embeddings to message dictionaries.
        
        Args:
            messages: List of message dictionaries
            text_key: Key in message dict containing text to embed
            
        Returns:
            List of messages with 'embedding' field added
        """
        if not messages:
            return []
        
        print(f"[INFO] Generating embeddings for {len(messages)} messages...")
        
        # Extract texts
        texts = [msg.get(text_key, '') for msg in messages]
        
        # Generate embeddings in batch
        embeddings = self.embed_batch(texts, show_progress=True)
        
        # Add embeddings to messages
        for msg, emb in zip(messages, embeddings):
            msg['embedding'] = emb.tolist()  # Convert to list for JSON serialization
        
        print(f"[OK] Generated {len(embeddings)} embeddings")
        return messages
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        return self.model.get_sentence_embedding_dimension()
    
    def similarity(self, embedding1: Union[np.ndarray, List[float]], 
                   embedding2: Union[np.ndarray, List[float]]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between -1 and 1
        """
        # Convert to numpy if needed
        if isinstance(embedding1, list):
            embedding1 = np.array(embedding1)
        if isinstance(embedding2, list):
            embedding2 = np.array(embedding2)
        
        # Cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)