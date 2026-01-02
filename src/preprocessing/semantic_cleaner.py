"""
Fast semantic cleaner for attachments.
Path: src/preprocessing/semantic_cleaner.py
"""
import re
from typing import List, Set

class SemanticCleaner:
    """Heuristic-based cleaner to remove noise and extract key content from large attachments."""
    
    @staticmethod
    def clean(text: str, max_size_kb: int = 50) -> str:
        """
        Clean text based on its size and content.
        
        Args:
            text: Input text from attachment
            max_size_kb: Threshold for aggressive cleaning
            
        Returns:
            Cleaned and potentially sampled text
        """
        if not text:
            return ""
            
        text_size_kb = len(text.encode('utf-8')) / 1024
        
        # 1. Basic Cleaning (always do this)
        text = SemanticCleaner.remove_noise(text)
        
        # 2. Boilerplate Detection (expensive on huge files, so we do it strategically)
        text = SemanticCleaner.remove_repeated_lines(text)
        
        # 3. Tiered Strategy
        if text_size_kb > 300:
            # Oversized: Selective Extraction
            return SemanticCleaner.extract_key_sections(text)
        elif text_size_kb > max_size_kb:
            # Large: Aggressive Cleaning
            return SemanticCleaner.aggressive_clean(text)
            
        return text

    @staticmethod
    def remove_noise(text: str) -> str:
        """Remove obvious noise like page numbers and navigation artifacts."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip page numbering patterns like "Page 1 of 10" or just "12"
            if re.match(r'^(Page\s+\d+\s+of\s+\d+|\d+)$', line, re.IGNORECASE):
                continue
            # Skip very short lines that likely contain no info (except headers)
            if len(line) < 2 and not line.isalnum():
                continue
            cleaned_lines.append(line)
            
        return '\n'.join(cleaned_lines)

    @staticmethod
    def remove_repeated_lines(text: str) -> str:
        """Remove lines that repeat frequently (likely headers/footers)."""
        lines = text.split('\n')
        if len(lines) < 20:
            return text
            
        line_counts = {}
        for line in lines:
            line = line.strip()
            if len(line) > 10: # Only track meaningful lines
                line_counts[line] = line_counts.get(line, 0) + 1
        
        # Identify lines that appear more than 3 times (headers/footers usually repeat on every page)
        boilerplate = {line for line, count in line_counts.items() if count > 5}
        
        if not boilerplate:
            return text
            
        return '\n'.join([l for l in lines if l.strip() not in boilerplate])

    @staticmethod
    def aggressive_clean(text: str) -> str:
        """More aggressive filtering for large files."""
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            line = line.strip()
            # Remove lines with high ratio of non-alphanumeric characters (tables/code noise)
            if len(line) > 20:
                alnum_count = sum(1 for c in line if c.isalnum())
                if alnum_count / len(line) < 0.3:
                    continue
            cleaned.append(line)
        return '\n'.join(cleaned)

    @staticmethod
    def extract_key_sections(text: str) -> str:
        """Extract Head, Tail and 'Dense' middle blocks for oversized files."""
        lines = text.split('\n')
        if len(lines) < 100:
            return text
            
        # Keep first 50 lines (Intro/Headers)
        head = lines[:50]
        
        # Keep last 50 lines (Conclusion/Summary)
        tail = lines[-50:]
        
        # Find a dense block in the middle (heuristic: line length density)
        # Average length of 20-line window
        max_density = 0
        dense_idx = 50
        
        for i in range(50, len(lines) - 70, 10):
            window = lines[i:i+20]
            density = sum(len(l) for l in window)
            if density > max_density:
                max_density = density
                dense_idx = i
                
        middle = lines[dense_idx:dense_idx+50]
        
        result = [
            "--- START OF DOCUMENT ---",
            *head,
            "\n... [LARGE CONTENT REMOVED FOR EFFICIENCY] ...\n",
            "--- KEY SECTION ---",
            *middle,
            "\n... [LARGE CONTENT REMOVED FOR EFFICIENCY] ...\n",
            "--- END OF DOCUMENT ---",
            *tail
        ]
        
        return '\n'.join(result)
