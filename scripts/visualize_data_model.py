"""
Visual demonstration of Vector-Document-Metadata relationships.
Creates a diagram showing how ID links all three layers.
"""

print("=" * 80)
print("DATA MODEL: How ID Links Vector, Document, and Metadata")
print("=" * 80)
print()

# Example message
message_id = "gmail_abc123"

print(f"Message ID: {message_id}")
print()
print("This single ID links three data layers:")
print()

# Layer 1: Document
print("┌" + "─" * 78 + "┐")
print("│ LAYER 1: DOCUMENT (Full Text)                                             │")
print("├" + "─" * 78 + "┤")
print(f"│ ID: {message_id:<70} │")
print("│ Document: 'Q4 Budget Discussion We need to finalize the budget by...'     │")
print("│ Storage: ChromaDB documents table                                         │")
print("│ Purpose: Full-text display, keyword search                                │")
print("│ Size: ~1 KB per message                                                   │")
print("└" + "─" * 78 + "┘")
print("                                    ↓")
print("                          (linked by same ID)")
print("                                    ↓")

# Layer 2: Vector
print("┌" + "─" * 78 + "┐")
print("│ LAYER 2: VECTOR (Semantic Embedding)                                      │")
print("├" + "─" * 78 + "┤")
print(f"│ ID: {message_id:<70} │")
print("│ Vector: [0.123, -0.456, 0.789, ..., 0.234] (384 dimensions)               │")
print("│ Storage: DuckDB/binary files in data/chromadb/[uuid]/                     │")
print("│ Purpose: Semantic similarity search (cosine distance)                     │")
print("│ Size: ~1.5 KB per message                                                 │")
print("└" + "─" * 78 + "┘")
print("                                    ↓")
print("                          (linked by same ID)")
print("                                    ↓")

# Layer 3: Metadata
print("┌" + "─" * 78 + "┐")
print("│ LAYER 3: METADATA (Structured Attributes)                                 │")
print("├" + "─" * 78 + "┤")
print(f"│ ID: {message_id:<70} │")
print("│ Metadata:                                                                  │")
print("│   - platform: 'gmail'                                                      │")
print("│   - sender_email: 'alice@example.com'                                      │")
print("│   - sender_name: 'Alice Smith'                                             │")
print("│   - date: '2024-12-20T15:30:00'                                            │")
print("│   - subject: 'Q4 Budget Discussion'                                        │")
print("│   - thread_id: 'thread_abc123'                                             │")
print("│   - url: 'https://mail.google.com/...'                                     │")
print("│   - type: 'email'                                                          │")
print("│ Storage: SQLite (embedding_metadata table)                                 │")
print("│ Purpose: Filtering, sorting, faceted search                                │")
print("│ Size: ~17 KB per message (with indexes)                                    │")
print("└" + "─" * 78 + "┘")

print()
print("=" * 80)
print("QUERY EXAMPLE: How the layers work together")
print("=" * 80)
print()

print("Query: 'What did Alice say about the budget in December?'")
print()

print("Step 1: VECTOR SEARCH (Semantic)")
print("  - Embed query: 'budget discussion' → [0.5, -0.3, ...]")
print("  - Compute cosine similarity with all 100 message vectors")
print("  - Return top 50 candidates by similarity")
print("  → Candidate IDs: ['gmail_abc123', 'gmail_def456', ...]")
print()

print("Step 2: METADATA FILTER (Structured)")
print("  - SQL query on SQLite:")
print("    WHERE sender_name = 'Alice'")
print("    AND date LIKE '2024-12%'")
print("    AND id IN (candidate_ids)")
print("  → Filtered IDs: ['gmail_abc123', 'gmail_xyz789']")
print()

print("Step 3: RETRIEVE DOCUMENTS (Display)")
print("  - Fetch full text for filtered IDs")
print("  - Return to user with metadata")
print("  → Results: 2 messages from Alice about budget in December")
print()

print("=" * 80)
print("KEY INSIGHT: ID is the PRIMARY KEY linking all three layers")
print("=" * 80)
