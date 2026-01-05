# Did-I - Personal Memory Assistant

Your personal AI-powered memory that remembers everything across Gmail messages and attachments (pdf/docs initially), (and soon Slack, Calendar, etc.)
   - local data storage
   - searches mails and attachments semantically
   - stores metadata for filter based search

## 🎯 What It Does

Did-I helps you remember:
- "When did I agree to send that report?"
- "What did Alice say about the Q4 budget?"
- "Did I respond to John's email about the meeting?"

It uses AI embeddings to semantically search through your messages and attachments, not just keyword matching.

---

## 📋 Prerequisites

- ✅ Python 3.10+ installed
- ✅ Virtual environment (`memoenv`) created and activated
- ✅ All dependencies installed (`pip install -r requirements.txt`)

---

## 🚀 Quick Start

### 1. Set Up Gmail API Credentials

Before you can use Did-I, you need to set up Gmail API access:

#### **Step 1: Create a Google Cloud Project**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Name it: `DidI-PersonalMemory`
4. Click **"Create"**

#### **Step 2: Enable Gmail API**

1. In your project, go to **"APIs & Services"** → **"Library"**
2. Search for: `Gmail API`
3. Click on it → Click **"Enable"**

#### **Step 3: Create OAuth Credentials**

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. If prompted, configure consent screen:
   - User Type: **External**
   - App name: `DidI Personal Memory`
   - User support email: (your email)
   - Developer contact: (your email)
   - Click **"Save and Continue"**
   - Scopes: Skip for now → **"Save and Continue"**
   - Test users: Add your Gmail address → **"Save and Continue"**
4. Back to creating OAuth client ID:
   - Application type: **Desktop app**
   - Name: `DidI Desktop Client`
   - Click **"Create"**
5. Download the JSON file → Click **"DOWNLOAD JSON"**
6. Rename the downloaded file to `credentials.json`
7. Move `credentials.json` to your project root: `D:\python\MemoDid\MemDidCode\`

#### **Step 4: First Run Authentication**

When you run the ingest script for the first time, a browser window will open asking you to:
1. Sign in to your Google account
2. Allow the app to read your Gmail (read-only)
3. This creates a `token.json` file that stores your access token

---

## 📁 Project Structure

Your project should look like this:

```
D:\python\MemoDid\MemDidCode\
├── .vscode/
│   └── settings.json
├── memoenv/                 # Virtual environment
├── src/
│   ├── __init__.py
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── base_connector.py
│   │   └── gmail_connector.py
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   └── cleaner.py
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── embedder.py
│   ├── storage/
│   │   ├── __init__.py
│   │   └── vector_store.py
│   └── retrieval/
│       ├── __init__.py
│       └── search.py
├── scripts/
│   ├── ingest.py           # Fetch emails from Gmail
│   ├── embed.py            # Generate embeddings & store
│   └── query.py            # Search your memory
├── data/
│   ├── raw/                # Raw JSON from Gmail
│   └── chromadb/           # Vector database (auto-created)
├── config.yaml             # Configuration
├── credentials.json        # Gmail OAuth credentials (YOU ADD THIS)
├── token.json             # Auto-generated on first run
├── requirements.txt
└── README.md
```

---

## 🔧 Usage

### **Step 1: Ingest Data (Fetch Emails)**

Fetch your last 100 emails from Gmail:

```bash
python scripts/ingest.py
```

**What happens:**
- Opens browser for Gmail authentication (first time only)
- Fetches emails
- Saves raw JSON to `data/raw/gmail_YYYYMMDD_HHMMSS.json`

---

### **Step 2: Generate Embeddings & Store**

Process the emails and store them in ChromaDB:

```bash
python scripts/embed.py
```

**What happens:**
- Loads the most recent raw data file
- Cleans and preprocesses messages
- Generates AI embeddings using `all-MiniLM-L6-v2`
- Stores everything in ChromaDB

**Note:** First run downloads the embedding model (~90MB), takes a few minutes.

---

### **Step 3: Search Your Memory!**

Now you can query your personal memory:

```bash
python scripts/query.py "When did I agree to send the report?"
```

**Example queries:**
```bash
python scripts/query.py "What did Alice say about the budget?"
python scripts/query.py "Did I respond to John about the meeting?"
python scripts/query.py "When is the deadline for the Q4 presentation?"
```

**Output:**
```
Found 3 results:
================================================================================

Result #1 (Similarity: 0.856)
  Subject: Re: Q4 Report Timeline
  From: You (you@example.com)
  Date: 2024-12-10 15:30
  Platform: gmail
  Snippet: I'll send the report by Friday afternoon...
  Link: https://mail.google.com/mail/u/0/#inbox/123456
--------------------------------------------------------------------------------
...
```

---

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
gmail:
  credentials_file: "credentials.json"  # Your OAuth credentials
  token_file: "token.json"              # Auto-generated token
  max_results: 100                      # Number of emails to fetch

embeddings:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  dimension: 384

storage:
  chromadb_path: "./data/chromadb"
  collection_name: "didi_messages"

paths:
  raw_data: "./data/raw"
```

---

## 🐛 Troubleshooting

### **Error: "credentials.json not found"**
- Make sure you downloaded it from Google Cloud Console
- Rename it exactly to `credentials.json`
- Place it in project root: `D:\python\MemoDid\MemDidCode\`

### **Error: "No messages fetched"**
- Check your Gmail account has emails
- Verify OAuth permissions were granted
- Try deleting `token.json` and re-authenticating

### **Error: "ChromaDB not found"**
- Make sure you ran: `pip install -r requirements.txt`
- Check that `(memoenv)` is activated in your terminal

### **Search returns no results**
- Make sure you ran `embed.py` after `ingest.py`
- Check that ChromaDB has data: Look in `data/chromadb/` folder

## here is mycode https://github.com/sispk6/MemDidCode.git

## 📊 Data Privacy

- **All data stays local** on your machine
- No cloud services (except Gmail API for fetching)
- `credentials.json` and `token.json` are in `.gitignore`
- Never commit these files to version control

---

## 🚀 Next Steps (Future Phases)

- [ ] Add Slack integration
- [ ] Add date/decision extraction
- [ ] Build browser extension UI
- [ ] Add incremental updates
- [ ] Multi-user support

---

## 🛠️ Tech Stack

- **Python 3.14**
- **ChromaDB** - Vector database
- **sentence-transformers** - AI embeddings
- **Gmail API** - Email access
- **BeautifulSoup4** - HTML cleaning
- **PyYAML** - Configuration

---

## 📝 License

Personal project - Use as you wish!

---

## 🤝 Contributing

This is a solo project for now, but feel free to fork and adapt for your needs!

---

**Built with ❤️ by a solo developer who forgets things**
