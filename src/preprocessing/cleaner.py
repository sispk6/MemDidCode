"""
Text preprocessing and cleaning utilities.
Path: src/preprocessing/cleaner.py
"""
import re
from typing import Dict, Any
from bs4 import BeautifulSoup


class MessageCleaner:
    """Clean and preprocess messages for embedding"""
    
    @staticmethod
    def clean_html(html_text: str) -> str:
        """
        Convert HTML to plain text.
        
        Args:
            html_text: HTML string
            
        Returns:
            Plain text string
        """
        if not html_text:
            return ""
        
        # Parse HTML
        soup = BeautifulSoup(html_text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean plain text by removing extra whitespace and special characters.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 512) -> str:
        """
        Truncate text to maximum length while preserving word boundaries.
        
        Args:
            text: Input text
            max_length: Maximum character length
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        # Truncate at word boundary
        truncated = text[:max_length].rsplit(' ', 1)[0]
        return truncated + "..."
    
    @staticmethod
    def prepare_for_embedding(message: Dict[str, Any]) -> str:
        """
        Prepare message text for embedding.
        Combines subject and body intelligently.
        
        Args:
            message: Message dictionary
            
        Returns:
            Text ready for embedding
        """
        subject = message.get('subject', '')
        content = message.get('content', '')
        
        # Clean HTML if present
        if '<html' in content.lower() or '<body' in content.lower():
            content = MessageCleaner.clean_html(content)
        
        # Clean text
        subject = MessageCleaner.clean_text(subject)
        content = MessageCleaner.clean_text(content)
        
        # Combine subject and content (NO truncation - chunking handles this)
        combined = f"{subject}\n\n{content}" if subject else content
        
        return combined
    
    @staticmethod
    def extract_email_addresses(text: str) -> list:
        """
        Extract email addresses from text.
        
        Args:
            text: Input text
            
        Returns:
            List of email addresses
        """
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(pattern, text)
    
    @staticmethod
    def remove_quoted_text(text: str) -> str:
        """
        Remove quoted reply text from emails (lines starting with >).
        
        Args:
            text: Email body text
            
        Returns:
            Text with quotes removed
        """
        lines = text.split('\n')
        non_quoted = [line for line in lines if not line.strip().startswith('>')]
        return '\n'.join(non_quoted)