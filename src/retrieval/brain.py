"""
RAG Brain - LLM-powered answer generation.
Path: src/retrieval/brain.py
"""
import os
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class RAGBrain:
    """Generate answers using LLM and retrieved contexts"""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize RAG Brain with Gemini.
        
        Args:
            model_name: Gemini model to use. If None, loads from config.yaml
        """
        self.config = self._load_config()
        self.model_name = model_name or self.config.get('llm', {}).get('model_name', "gemini-2.0-flash")
        self.model = None
        self._initialize_model()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml"""
        try:
            # Assuming config.yaml is in the project root
            # src/retrieval/brain.py -> src/retrieval -> src -> root
            config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            print(f"[WARN] Failed to load config.yaml: {e}")
        return {}
    
    def _initialize_model(self):
        """Initialize Gemini model with API key"""
        try:
            import google.generativeai as genai
            
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError(
                    "GOOGLE_API_KEY not found in environment. "
                    "Please add it to your .env file."
                )
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"[INFO] Initialized RAG Brain with {self.model_name}")
            
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. "
                "Run: pip install google-generativeai"
            )
        except Exception as e:
            print(f"[ERROR] Failed to initialize Gemini: {e}")
            raise
    
    def generate_answer(self, query: str, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate an answer based on query and retrieved contexts.
        
        Args:
            query: User's question
            contexts: List of retrieved documents with metadata
            
        Returns:
            Dictionary with answer and metadata
        """
        if not contexts:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "confidence": "low",
                "sources_used": 0
            }
        
        # Build prompt with contexts
        prompt = self._build_prompt(query, contexts)
        
        try:
            # Generate response
            response = self.model.generate_content(prompt)
            answer = response.text
            
            return {
                "answer": answer,
                "confidence": "high" if len(contexts) >= 3 else "medium",
                "sources_used": len(contexts)
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to generate answer: {e}")
            return {
                "answer": f"Error generating answer: {str(e)}",
                "confidence": "error",
                "sources_used": len(contexts)
            }
    
    def _build_prompt(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        """
        Build prompt for LLM with query and contexts.
        
        Args:
            query: User's question
            contexts: Retrieved documents
            
        Returns:
            Formatted prompt string
        """
        # Format contexts
        context_texts = []
        for idx, ctx in enumerate(contexts[:5], 1):  # Limit to top 5
            metadata = ctx.get('metadata', {})
            doc_text = ctx.get('full_text', ctx.get('snippet', ''))
            
            # Build context with metadata
            context = f"[Source {idx}]\n"
            context += f"From: {metadata.get('sender_name', 'Unknown')} ({metadata.get('sender_email', '')})\n"
            context += f"Date: {metadata.get('date', 'Unknown')}\n"
            context += f"Subject: {metadata.get('subject', 'No subject')}\n"
            context += f"Platform: {metadata.get('platform', 'Unknown')}\n"
            context += f"Content: {doc_text}\n"
            
            context_texts.append(context)
        
        contexts_str = "\n---\n".join(context_texts)
        
        # Build final prompt
        prompt = f"""You are a personal memory assistant helping answer questions about past communications and events.

**Question:** {query}

**Retrieved Information:**
{contexts_str}

**Instructions:**
1. Answer the question directly based ONLY on the provided sources.
2. If the sources contain the answer, provide a clear, concise response.
3. Cite which source(s) you used (e.g., "According to Source 1...").
4. If multiple sources have relevant info, synthesize them naturally.
5. If the sources don't contain enough information, say so clearly.
6. Do not make up information or speculate beyond what's in the sources.

**Answer:**"""
        
        return prompt
    
    def generate_summary(self, documents: List[Dict[str, Any]], topic: Optional[str] = None) -> str:
        """
        Generate a summary of multiple documents.
        
        Args:
            documents: List of documents to summarize
            topic: Optional topic to focus the summary on
            
        Returns:
            Summary text
        """
        if not documents:
            return "No documents to summarize."
        
        # Build context from documents
        doc_texts = []
        for doc in documents[:10]:  # Limit to 10
            metadata = doc.get('metadata', {})
            text = doc.get('full_text', doc.get('snippet', ''))
            doc_texts.append(f"- {metadata.get('subject', 'No subject')}: {text[:200]}...")
        
        docs_str = "\n".join(doc_texts)
        
        topic_instruction = f" focusing on '{topic}'" if topic else ""
        
        prompt = f"""Summarize the following communications{topic_instruction}:

{docs_str}

Provide a concise summary highlighting key points, decisions, and action items."""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating summary: {e}"
