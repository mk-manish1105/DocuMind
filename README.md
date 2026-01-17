<div align="center">

# 🧠 DocuMind

### Adaptive AI-Powered Document Intelligence Assistant

*Ask questions. Get answers. From your documents or general knowledge.*

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Features](#-features) • [Demo](#-how-it-works) • [Installation](#️-installation) • [API Docs](#-api-reference) • [Tech Stack](#-tech-stack)

</div>

---

## 🌟 Overview

**DocuMind** is a full-stack AI-powered application that intelligently answers questions using a hybrid approach:
- 📄 **Document-aware**: Upload PDFs, DOCX, or TXT files and get precise answers from your content
- 🌐 **General knowledge**: Seamlessly fallback to AI's broad knowledge when documents don't contain the answer
- 🔐 **Secure & Personal**: User authentication with isolated document storage and persistent chat history

Perfect for researchers, students, professionals, or anyone who needs to extract insights from documents while maintaining the flexibility of general AI assistance.

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔐 Authentication & Access
- **Guest Mode**: Try the AI without signing up
- **User Accounts**: Full authentication with JWT
- **Secure Storage**: Per-user document isolation
- **Session Management**: Persistent chat history

</td>
<td width="50%">

### 📚 Document Intelligence
- **Multi-format Support**: PDF, DOCX, TXT
- **Smart Chunking**: Intelligent text segmentation
- **Semantic Search**: Vector similarity with FAISS
- **RAG Pipeline**: Context-aware responses

</td>
</tr>
<tr>
<td width="50%">

### 💬 Chat Experience
- **Streaming Responses**: Token-by-token live output
- **Hybrid Answering**: Documents + general knowledge
- **Chat History**: Review past conversations
- **Multiple Sessions**: Organize by topic

</td>
<td width="50%">

### ⚡ Performance & UX
- **Background Processing**: Non-blocking indexing
- **Responsive Design**: Desktop & mobile friendly
- **Markdown Support**: Rich text formatting
- **Real-time Updates**: Live response streaming

</td>
</tr>
</table>

---

## 🎯 How It Works

```mermaid
graph LR
    A[User Uploads Document] --> B[Text Extraction]
    B --> C[Cleaning & Chunking]
    C --> D[Generate Embeddings]
    D --> E[FAISS Index]
    F[User Asks Question] --> G{Relevant Context?}
    E --> G
    G -->|Yes| H[RAG with Context]
    G -->|No| I[General Knowledge]
    H --> J[Stream Response]
    I --> J
    J --> K[Live AI Answer]
```

1. **Upload** → Documents are processed and indexed automatically
2. **Ask** → Questions trigger semantic search across your documents
3. **Retrieve** → Most relevant chunks are identified using vector similarity
4. **Generate** → AI produces answers using retrieved context or general knowledge
5. **Stream** → Responses appear live, token by token

---

## 🆚 Guest vs Authenticated Users

<div align="center">

| Feature | 👤 Guest | 🔑 Logged-in User |
|:--------|:--------:|:-----------------:|
| Ask general questions | ✅ | ✅ |
| Upload documents | ❌ | ✅ |
| Document-based answers | ❌ | ✅ |
| Chat history | ❌ | ✅ |
| Persistent sessions | ❌ | ✅ |
| Multi-device sync | ❌ | ✅ |

</div>

---

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- PostgreSQL
- Git

### 1️⃣ Clone Repository

```bash
git clone https://github.com/mk-manish1105/documind.git
cd documind
```

### 2️⃣ Backend Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python app/scripts/create_tables.py

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: **http://localhost:8000**

### 3️⃣ Frontend Setup

```bash
# In a new terminal
cd frontend
python -m http.server 5173
```

Frontend runs at: **http://localhost:5173**

---

## ⚙️ Configuration

Create a `.env` file in the `backend` directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/documind_db

# Authentication
JWT_SECRET=your-super-secret-key-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# LLM Configuration
LLAMA_API_KEY=your_api_key_here
LLAMA_API_URL=https://api.groq.com/openai/v1/chat/completions
LLAMA_MODEL=llama-3.1-8b-instant

# Data Storage
DOCUMIND_DATA_DIR=/path/to/documind_data
```

---

## 📁 Project Structure

```
DocuMind/
├── 📂 frontend/
│   ├── index.html              # Single-page application
│   ├── style.css               # Responsive styling
│   └── app.js                  # Client-side logic
│
├── 📂 backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── 📂 api/             # API endpoints
│   │   │   ├── auth.py         # Authentication routes
│   │   │   ├── chat.py         # Chat & RAG logic
│   │   │   └── files.py        # Document management
│   │   ├── 📂 db/              # Database layer
│   │   │   ├── models.py       # SQLAlchemy models
│   │   │   └── engine.py       # Database connection
│   │   ├── 📂 services/        # Business logic
│   │   │   ├── embeddings.py   # Sentence transformers
│   │   │   ├── retriever_service.py  # FAISS indexing
│   │   │   └── llama_api.py    # LLM integration
│   │   ├── 📂 utils/           # Helper functions
│   │   │   ├── file_utils.py   # File operations
│   │   │   └── utils_extraction.py  # Text processing
│   │   ├── 📂 core/            # Core configuration
│   │   │   ├── config.py       # Environment config
│   │   │   └── security.py     # JWT & hashing
│   │   └── 📂 schemas/         # Pydantic models
│   └── requirements.txt
│
└── README.md
```

---

## 🔌 API Reference

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create new user account |
| `/auth/login` | POST | Login and receive JWT token |
| `/auth/me` | GET | Get current user info |

### Documents (Authenticated)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/files/upload` | POST | Upload and index document |
| `/files/list` | GET | List user's documents |
| `/files/{id}` | DELETE | Delete specific document |

### Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Ask question (streaming response) |
| `/chat/sessions` | GET | Get all chat sessions |
| `/chat/history/{session_id}` | GET | Get session messages |

---

## 🧪 Tech Stack

<div align="center">

### Frontend
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

### Backend
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

### AI/ML
![Transformers](https://img.shields.io/badge/🤗_Transformers-FF6F00?style=for-the-badge)
![FAISS](https://img.shields.io/badge/FAISS-0467DF?style=for-the-badge)

</div>

**Key Technologies:**
- **FastAPI** - Modern async web framework
- **SQLAlchemy** - SQL toolkit and ORM
- **Sentence Transformers** - `intfloat/e5-large-v2` embeddings
- **FAISS** - Facebook AI Similarity Search
- **JWT** - Secure authentication
- **Marked.js** - Markdown rendering

---

## 🔒 Security Features

- 🔐 **Password Hashing**: bcrypt-based secure password storage
- 🎫 **JWT Authentication**: Stateless token-based auth
- 🗂️ **User Isolation**: Documents stored per-user with access control
- 🚫 **Guest Limitations**: No data persistence for unauthenticated users
- 🔑 **Environment Secrets**: All sensitive data in `.env` files

---

## 🚀 Future Enhancements

- [ ] Support for more file formats (PPTX, Excel, Images with OCR)
- [ ] Multi-language support
- [ ] Document summarization
- [ ] Advanced analytics dashboard
- [ ] Team collaboration features
- [ ] Export chat history
- [ ] Voice input/output
- [ ] Mobile native apps

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

<div align="center">

**Manish Kumar**

B.Tech IT Student | Aspiring AI/ML Engineer (NLP & LLM)

📍 Jaipur, Rajasthan, India

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/manishkumar1105)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/mk-manish1105)

</div>

---

<div align="center">

### ⭐ Star this repo if you find it helpful!

Made with ❤️ and ☕ by [Manish Kumar](https://github.com/mk-manish1105)

</div>