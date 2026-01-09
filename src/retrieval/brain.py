import os
import yaml
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.utils.config_loader import load_config


class RAGBrain:
    """Generate answers using LLM and retrieved contexts"""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize RAG Brain with configured provider.
        
        Args:
            model_name: Model to use. If None, loads from config.yaml
        """
        self.config = load_config()
        llm_config = self.config.get('llm', {})
        
        # Determine provider and model
        self.provider = llm_config.get('provider', 'gemini')
        self.model_name = model_name or llm_config.get('model_name', "gemini-2.0-flash")
        
        # Initialize generic "model" placeholder
        self.model = None 
        
        # Provider specific initialization
        if self.provider == 'gemini':
            self._initialize_gemini()
        elif self.provider == 'huggingface':
            self._initialize_huggingface(llm_config)
        else:
            print(f"[WARN] Unknown provider '{self.provider}'. Defaulting to Gemini.")
            self.provider = 'gemini'
            self._initialize_gemini()


    
    def _initialize_gemini(self):
        """Initialize Gemini model with API key"""
        try:
            import google.generativeai as genai
            
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                print("[WARN] GOOGLE_API_KEY not found. Gemini will fail if used.")
            else:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(self.model_name)
                print(f"[INFO] Initialized RAG Brain with Gemini: {self.model_name}")
            
        except ImportError:
            print("[ERROR] google-generativeai not installed.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Gemini: {e}")

    def _initialize_huggingface(self, config: Dict[str, Any]):
        """Initialize Hugging Face client"""
        self.hf_api_key = os.getenv(config.get('api_key_env_var', 'HUGGINGFACE_API_KEY'))
        # Using the standard OpenAI-compatible endpoint provided by HF Router
        self.hf_api_url = f"https://router.huggingface.co/hf-inference/models/{self.model_name}/v1/chat/completions"
        
        if not self.hf_api_key:
             print("[WARN] HUGGINGFACE_API_KEY not found. Inference will fail.")
        else:
             print(f"[INFO] Initialized RAG Brain with Hugging Face: {self.model_name}")

    def generate_answer(self, query: str, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate answer based on provider"""
        if not contexts:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "confidence": "low",
                "sources_used": 0
            }
        
        prompt = self._build_prompt(query, contexts)
        
        try:
            if self.provider == 'gemini':
                return self._generate_gemini(prompt, len(contexts))
            elif self.provider == 'huggingface':
                return self._generate_huggingface(prompt, len(contexts))
            
        except Exception as e:
            print(f"[ERROR] Failed to generate answer: {e}")
            return {
                "answer": f"Error generating answer: {str(e)}",
                "confidence": "error",
                "sources_used": len(contexts)
            }
        return {"answer": "Provider error", "confidence": "error", "sources_used": 0}

    def _generate_gemini(self, prompt: str, num_sources: int) -> Dict[str, Any]:
         if not self.model:
             raise ValueError("Gemini model not initialized")
         
         response = self.model.generate_content(prompt)
         return {
            "answer": response.text,
            "confidence": "high" if num_sources >= 3 else "medium",
            "sources_used": num_sources
        }

    def _generate_huggingface(self, prompt: str, num_sources: int) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json"
        }
        
        # OpenAI Chat Completion format
        messages = [
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.7
        }
        
        # Note: The base URL for chat completions is often slightly different.
        # Let's try the standard /v1/chat/completions on the router base
        url = "https://router.huggingface.co/v1/chat/completions"
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Hugging Face API Error ({response.status_code}): {response.text}")
            
        result = response.json()
        
        # Parse OpenAI-format response
        if 'choices' in result and len(result['choices']) > 0:
            answer = result['choices'][0]['message']['content']
        else:
            answer = str(result)

        return {
            "answer": answer.strip(),
            "confidence": "high" if num_sources >= 3 else "medium",
            "sources_used": num_sources
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
            if self.provider == 'gemini':
                # Gemini returns the object, need to extract text
                 if not self.model:
                     return "Gemini model not initialized"
                 response = self.model.generate_content(prompt)
                 return response.text
            elif self.provider == 'huggingface':
                # Re-use the generation logic
                result = self._generate_huggingface(prompt, len(documents))
                return result.get('answer', 'Error generating summary')
                
        except Exception as e:
            return f"Error generating summary: {e}"
        return "Provider error"

    def generate_raw(self, prompt: str) -> str:
        """
        Generate raw text completion without predefined templates.
        Used for evaluation and synthetic data generation.
        """
        try:
            if self.provider == 'gemini' and self.model:
                response = self.model.generate_content(prompt)
                return response.text.strip()
            elif self.provider == 'huggingface':
                # Re-use HF inference logic but with custom prompt
                result = self._generate_huggingface(prompt, 0)
                return result.get('answer', '').strip()
        except Exception as e:
            print(f"[DEBUG] Raw generation failed: {e}")
            return ""
        return ""
