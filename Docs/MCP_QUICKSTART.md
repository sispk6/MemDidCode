# Quick Start: Using MCP Mode

## Running MCP Ingest

To use the new MCP connector to fetch Gmail messages:

```bash
# Activate virtual environment
cd d:\python\MemoDid\MemDidCode
memoenv\Scripts\activate

# Set UTF-8 encoding (Windows workaround for emoji characters)
$env:PYTHONIOENCODING="utf-8"

# Run ingest with MCP mode
python scripts/ingest.py --mode mcp --max-results 10
```

## Expected Workflow

1. **Authentication**: Uses existing `credentials.json` and `token.json`
2. **Fetching**: Retrieves messages via MCP Gmail connector
3. **Normalization**: Same format as legacy mode
4. **Storage**: Saves to `data/raw/gmail_mcp_YYYYMMDD_HHMMSS.json`

## Next Steps

After ingesting with MCP mode, the rest of the pipeline works identically:

```bash
# Generate embeddings (works with both legacy and MCP data)
python scripts/embed.py

# Query your memory
python scripts/query.py "your search query"
```

## Switching Between Modes

```bash
# Legacy mode (default)
python scripts/ingest.py --max-results 10

# MCP mode
python scripts/ingest.py --mode mcp --max-results 10
```

Both produce the same normalized output format, so they're fully interchangeable!

## Troubleshooting

**Issue**: `UnicodeEncodeError` with emoji characters

**Solution**: Set UTF-8 encoding before running:
```powershell
$env:PYTHONIOENCODING="utf-8"
```

Or add to your PowerShell profile for permanent fix.
