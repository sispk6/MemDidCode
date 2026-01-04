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
        line_count = text.count('\n')
        print(f"    [DEBUG] SemanticCleaner.clean: {text_size_kb:.1f}KB, {line_count} lines", flush=True)
            
        # Hard limit: if text is over 5MB, truncate immediately before any processing
        # to avoid OOM during regex or splitting
        if len(text) > 5 * 1024 * 1024:
            text = text[:1024 * 1024] + "\n... [TRUNCATED DUE TO EXTREME SIZE] ...\n"
            print(f"    [WARN] Truncated text from 5MB+ to 1MB", flush=True)

        # 1. Basic Cleaning (always do this)
        text = SemanticCleaner.remove_noise(text)
        
        # 2. Boilerplate Detection (expensive on huge files, so we do it strategically)
        text = SemanticCleaner.remove_repeated_lines(text)
        
        # 3. Tiered Strategy
        if text_size_kb > 300:
            # Oversized: Selective Extraction
            print(f"    [INFO] Large attachment (>300KB), extracting key sections", flush=True)
            return SemanticCleaner.extract_key_sections(text)
        elif text_size_kb > max_size_kb:
            # Large: Aggressive Cleaning
            print(f"    [INFO] Medium attachment (>{max_size_kb}KB), aggressive cleaning", flush=True)
            return SemanticCleaner.aggressive_clean(text)
            
        return text

    @staticmethod
    def remove_noise(text: str) -> str:
        """Remove obvious noise like page numbers and navigation artifacts."""
        print(f"    [DEBUG] remove_noise starting...", flush=True)
        lines = text.split('\n')
        
        # Performance guard: Skip expensive regex on very large texts
        if len(lines) > 100000:
            print(f"    [WARN] Skipping noise removal (too many lines: {len(lines)})", flush=True)
            return text
        
        print(f"    [DEBUG] remove_noise processing {len(lines)} lines", flush=True)
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
        
        print(f"    [DEBUG] remove_noise done, kept {len(cleaned_lines)} lines", flush=True)
        return '\n'.join(cleaned_lines)

    @staticmethod
    def remove_repeated_lines(text: str) -> str:
        """Remove lines that repeat frequently (likely headers/footers)."""
        print(f"    [DEBUG] remove_repeated_lines starting...", flush=True)
        lines = text.split('\n')
        
        # Performance guard: Skip this expensive operation on very large texts
        # (likely data dumps that don't benefit from this cleaning)
        if len(lines) > 50000:
            print(f"    [WARN] Skipping repeated line removal (too many lines: {len(lines)})", flush=True)
            return text
            
        if len(lines) < 20:
            print(f"    [DEBUG] Too few lines ({len(lines)}), skipping", flush=True)
            return text
        
        print(f"    [DEBUG] remove_repeated_lines processing {len(lines)} lines", flush=True)
        line_counts = {}
        for line in lines:
            line = line.strip()
            if len(line) > 10: # Only track meaningful lines
                line_counts[line] = line_counts.get(line, 0) + 1
        
        # Identify lines that appear more than 5 times (headers/footers usually repeat on every page)
        boilerplate = {line for line, count in line_counts.items() if count > 5}
        
        if not boilerplate:
            print(f"    [DEBUG] No boilerplate found", flush=True)
            return text
        
        print(f"    [DEBUG] Removing {len(boilerplate)} boilerplate lines", flush=True)
        return '\n'.join([l for l in lines if l.strip() not in boilerplate])

    @staticmethod
    def aggressive_clean(text: str) -> str:
        """More aggressive filtering for large files."""
        lines = text.split('\n')
        
        # Performance guard
        if len(lines) > 100000:
            print(f"    [WARN] Text too large for aggressive clean ({len(lines)} lines), truncating first")
            lines = lines[:50000]  # Process only first 50k lines
            
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
