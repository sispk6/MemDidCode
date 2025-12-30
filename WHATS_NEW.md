# Quick Reference: What's New in DidI

## Recent Updates

### ✅ Enhanced Metadata (Just Added!)

**13 new metadata fields** for better search and filtering:

#### High Priority Fields
- `recipient_emails` - Who you sent messages to
- `recipient_names` - Recipient names
- `participants` - All conversation participants
- `participant_count` - Number of participants
- `direction` - "sent" or "received"

#### Medium Priority Fields
- `year`, `month`, `day_of_week`, `hour` - Temporal filtering

### ✅ Emoji Encoding Fix

All emoji characters replaced with ASCII for Windows compatibility.

---

## New Query Examples

### Find group conversations
```python
chromadb.search(
    query="team meeting",
    where={"participant_count": {"$gte": "3"}}
)
```

### Find Friday emails
```python
chromadb.search(
    query="weekly update",
    where={"day_of_week": "Friday"}
)
```

### Find December 2024 messages
```python
chromadb.search(
    query="year end",
    where={"year": "2024", "month": "12"}
)
```

---

## How to Use

### 1. Configure Your Email
Edit `config.yaml`:
```yaml
user:
  email: "your.email@example.com"
```

### 2. Re-Ingest Messages
```bash
python scripts/ingest.py --max-results 100
```

### 3. Generate Embeddings
```bash
python scripts/embed.py
```

### 4. Query with New Fields
```bash
python scripts/query.py "your search query"
```

---

## Storage Impact

- **+23% storage** for 100K messages (+380 MB)
- **+2-5ms** query time (negligible)
- **$0.11/year** cloud cost (or $0.00 local)

---

## Documentation

- [Enhanced Metadata Walkthrough](file:///C:/Users/Imtiaz/.gemini/antigravity/brain/d1e1b107-bcd7-4ddf-8e11-fd2eb19684e9/walkthrough.md)
- [Metadata Improvements Guide](file:///d:/python/MemoDid/MemDidCode/METADATA_IMPROVEMENTS.md)
- [Cost Analysis](file:///d:/python/MemoDid/MemDidCode/METADATA_COST_ANALYSIS.md)
- [Competitive Edge Analysis](file:///d:/python/MemoDid/MemDidCode/COMPETITIVE_EDGE.md)
