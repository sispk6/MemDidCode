# ChromaDB + SQLite Architecture Explained

## Overview

Your DidI project uses **ChromaDB**, which internally uses **SQLite** as its metadata storage backend. They work together to provide both **semantic search** (via vector embeddings) and **structured filtering** (via relational data).

---

## The Two-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ChromaDB Layer                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: VECTOR STORAGE (Embeddings)                      │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  • 384-dimensional vectors (from sentence-transformers)│ │
│  │  • Stored in: DuckDB or custom binary format          │ │
│  │  • Optimized for: Cosine similarity search            │ │
│  │  • Index: HNSW (Hierarchical Navigable Small World)   │ │
│  │  • Location: data/chromadb/[uuid]/                    │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Layer 2: METADATA STORAGE (SQLite)                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  • Document IDs and relationships                      │ │
│  │  • Metadata fields (sender, date, subject, etc.)      │ │
│  │  • Collection configuration                            │ │
│  │  • Full-text search indexes                            │ │
│  │  • File: data/chromadb/chroma.sqlite3 (1.7 MB)        │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## What's Stored in SQLite

Based on your actual database, here's what SQLite contains:

### 1. **Collections Table**
Stores information about your ChromaDB collections:
```sql
CREATE TABLE collections (
    id TEXT PRIMARY KEY,
    name TEXT,
    topic TEXT,
    dimension INTEGER,
    database_id TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

**Your data:**
- Collection: `didi_messages`
- Dimension: 384 (matches your sentence-transformer model)
- 100 messages stored

---

### 2. **Embeddings Table**
Links documents to their vector embeddings:
```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    segment_id TEXT,
    embedding_id TEXT,  -- Your message ID (e.g., "gmail_abc123")
    seq_id BLOB,
    created_at TIMESTAMP
)
```

**What it stores:**
- Document IDs (your Gmail message IDs)
- Pointers to actual vector data
- Sequence IDs for ordering
- **NOT the actual 384-dimensional vectors** (those are in separate files)

---

### 3. **Embedding_Metadata Table**
Stores your searchable metadata fields:
```sql
CREATE TABLE embedding_metadata (
    id INTEGER PRIMARY KEY,
    key TEXT,              -- Field name (e.g., "sender_email", "date")
    string_value TEXT,     -- For text fields
    int_value INTEGER,     -- For numeric fields
    float_value REAL,      -- For decimal fields
    bool_value INTEGER     -- For boolean fields
)
```

**Your metadata (from vector_store.py):**
```python
metadata = {
    "platform": "gmail",           # string_value
    "sender_email": "alice@...",   # string_value
    "sender_name": "Alice",        # string_value
    "date": "2024-12-20T...",      # string_value
    "subject": "Q4 Report",        # string_value
    "thread_id": "thread123",      # string_value
    "url": "https://mail...",      # string_value
    "type": "email"                # string_value
}
```

**Current stats:**
- 100 embeddings (messages)
- 900 metadata entries (9 fields × 100 messages)

---

### 4. **Full-Text Search Tables**
SQLite FTS5 (Full-Text Search) for text matching:
```sql
-- Virtual table for full-text search
CREATE VIRTUAL TABLE embedding_fulltext_search 
USING fts5(string_value);
```

**Purpose:**
- Enables keyword search on document content
- Complements vector similarity search
- Fast text matching without scanning all documents

---

## How They Work Together

### Example Query: "What did Alice say about the budget?"

```python
# Your code in vector_store.py
results = vector_store.search(
    query_embedding=embedder.embed("What did Alice say about the budget?"),
    n_results=10,
    where={"sender_name": "Alice"}  # SQLite metadata filter
)
```

**What happens internally:**

1. **Vector Search (DuckDB/Binary Files)**
   ```
   - Compute cosine similarity between query embedding and all 100 message embeddings
   - Find top 10 most similar vectors
   - Returns candidate message IDs
   ```

2. **Metadata Filtering (SQLite)**
   ```sql
   SELECT embedding_id 
   FROM embedding_metadata 
   WHERE key = 'sender_name' 
     AND string_value = 'Alice'
     AND embedding_id IN (candidate_ids_from_step_1)
   ```

3. **Combine Results**
   ```
   - Intersect vector search results with metadata filter
   - Return only messages that match BOTH:
     * Semantic similarity to query
     * sender_name = "Alice"
   ```

---

## Storage Breakdown

### Your Current Data (100 messages):

```
data/chromadb/
├── chroma.sqlite3                    # 1.7 MB
│   ├── Collections (1 row)
│   ├── Embeddings (100 rows)
│   ├── Metadata (900 rows)
│   └── Full-text search indexes
│
└── a1bfece5-3554-4447-a0a9-5c0ce0fb9b35/  # UUID directory
    ├── Vector data (binary)          # ~150 KB
    │   └── 100 × 384 floats
    └── HNSW index                    # ~50 KB
```

**Size calculation:**
- Each embedding: 384 dimensions × 4 bytes (float32) = 1,536 bytes
- 100 embeddings: ~150 KB
- SQLite metadata: 1.7 MB (includes indexes and full-text search)
- Total: ~2 MB for 100 messages

---

## Benefits of This Hybrid Approach

### 1. **Fast Semantic Search**
- Vector similarity computed on optimized binary format
- HNSW index enables sub-linear search time
- No need to scan all 100 embeddings

### 2. **Flexible Metadata Filtering**
- SQL queries for complex filters:
  ```python
  where={
      "$and": [
          {"platform": "gmail"},
          {"date": {"$gte": "2024-12-01"}},
          {"sender_email": {"$contains": "example.com"}}
      ]
  }
  ```

### 3. **Full-Text Search**
- Keyword matching on document content
- Complements semantic search
- Example: Find exact phrase "Q4 budget report"

### 4. **Scalability**
- SQLite handles millions of metadata rows efficiently
- Vector index scales to 100K+ documents
- Separate storage allows independent optimization

---

## Comparison: Vector vs. Relational Data

| Aspect | Vector Embeddings | SQLite Metadata |
|--------|------------------|-----------------|
| **Purpose** | Semantic similarity | Exact matching & filtering |
| **Storage** | Binary files (DuckDB) | SQLite tables |
| **Search** | Cosine similarity | SQL WHERE clauses |
| **Size** | 1.5 KB per message | ~17 KB per message (with indexes) |
| **Query** | "Similar to this concept" | "sender = Alice AND date > X" |
| **Index** | HNSW (approximate) | B-tree (exact) |

---

## Real-World Example from Your Data

### Stored Message:
```json
{
  "id": "gmail_abc123",
  "platform": "gmail",
  "from": {"name": "Alice", "email": "alice@example.com"},
  "date": "2024-12-15T10:30:00",
  "subject": "Q4 Budget Discussion",
  "content": "We need to finalize the Q4 budget by Friday..."
}
```

### How It's Stored:

**1. Vector (Binary File):**
```
[0.123, -0.456, 0.789, ..., 0.234]  # 384 floats
```

**2. SQLite Metadata:**
```sql
-- embeddings table
INSERT INTO embeddings VALUES (1, 'segment_id', 'gmail_abc123', ...);

-- embedding_metadata table (9 rows for this message)
INSERT INTO embedding_metadata VALUES (1, 'platform', 'gmail', NULL, NULL, NULL);
INSERT INTO embedding_metadata VALUES (2, 'sender_email', 'alice@example.com', NULL, NULL, NULL);
INSERT INTO embedding_metadata VALUES (3, 'sender_name', 'Alice', NULL, NULL, NULL);
INSERT INTO embedding_metadata VALUES (4, 'date', '2024-12-15T10:30:00', NULL, NULL, NULL);
INSERT INTO embedding_metadata VALUES (5, 'subject', 'Q4 Budget Discussion', NULL, NULL, NULL);
-- ... 4 more rows for thread_id, url, type, etc.
```

**3. Full-Text Search:**
```sql
-- embedding_fulltext_search table
INSERT INTO embedding_fulltext_search VALUES ('Q4 Budget Discussion We need to finalize...');
```

---

## Query Performance

### Semantic Search (Vector)
```python
# Query: "budget planning"
results = vector_store.search(
    query_embedding=embed("budget planning"),
    n_results=10
)
```
**Performance:** ~10-50ms for 100 messages (sub-linear with HNSW index)

### Metadata Filter (SQLite)
```python
# Query: All emails from Alice in December
results = vector_store.search(
    query_embedding=embed("anything"),
    where={
        "sender_name": "Alice",
        "date": {"$gte": "2024-12-01"}
    }
)
```
**Performance:** ~1-5ms (B-tree index on metadata)

### Hybrid Search (Both)
```python
# Query: Budget-related emails from Alice
results = vector_store.search(
    query_embedding=embed("budget planning"),
    where={"sender_name": "Alice"}
)
```
**Performance:** ~15-60ms (vector search + metadata filter)

---

## Summary

**ChromaDB = Vector Storage + SQLite Metadata**

- **SQLite** stores:
  - Document IDs and relationships
  - Searchable metadata (sender, date, subject, etc.)
  - Full-text search indexes
  - Collection configuration

- **Vector Storage** (DuckDB/Binary) stores:
  - 384-dimensional embeddings
  - HNSW similarity index
  - Optimized for cosine similarity

- **Together** they enable:
  - Semantic search ("find similar concepts")
  - Metadata filtering ("from Alice in December")
  - Hybrid queries ("budget-related emails from Alice")
  - Fast, scalable search across thousands of messages

This is why your DidI project can do both:
1. **Semantic**: "When did I discuss the Q4 presentation?" (vector similarity)
2. **Structured**: "Show me all emails from Alice" (SQL filter)
3. **Hybrid**: "What did Alice say about the budget?" (both!)
