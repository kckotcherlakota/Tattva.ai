# Tatva.ai 🎙️

<div align="center">
  <!-- Logo placeholder - see assets/BRAND_IDENTITY.md for design -->
  <h1>त Tatva.ai</h1>
  
  <p><b>Giving Voice to Ancient Wisdom</b></p>
  
  <p>
    AI-powered Audio-to-Text for <strong>Telugu</strong> and <strong>Sanskrit</strong>
  </p>

  <img src="https://img.shields.io/badge/Language-Telugu-orange" alt="Telugu">
  <img src="https://img.shields.io/badge/Language-Sanskrit-purple" alt="Sanskrit">
  <img src="https://img.shields.io/badge/AI-Whisper-green" alt="Whisper">
  <img src="https://img.shields.io/badge/Built-FastAPI-blue" alt="FastAPI">
  
</div>

---

## ✨ Features

- 🎯 **High Accuracy**: Fine-tuned for Telugu and Sanskrit
- 🚀 **Fast Processing**: Transcribe in seconds
- 📱 **Mobile Responsive**: Works on all devices
- 🔒 **Privacy First**: Auto-delete after processing
- 📥 **Multiple Formats**: Download as TXT, JSON, SRT
- 🌐 **Web Interface**: Beautiful, intuitive UI
- ⚡ **API Access**: RESTful API for developers

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker (optional)
- 2GB RAM minimum

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/tatvai.git
cd tatvai

# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend (new terminal)
cd frontend
python -m http.server 3000

# Open http://localhost:3000
```

### Docker Deployment

```bash
# Build and run
docker-compose up --build

# Access app at http://localhost
```

## 📖 API Documentation

### Transcribe Audio
```bash
POST /transcribe
Content-Type: multipart/form-data

Parameters:
  - audio: Audio file (wav, mp3, m4a, ogg)
  - language: "te" (Telugu) or "sa" (Sanskrit)
  - model_size: tiny, base, small, medium
```

### Example Response
```json
{
  "id": "abc123",
  "text": "నమస్తే, ఎలా ఉన్నారు?",
  "language": "te",
  "duration": 5.2,
  "confidence": 94.5,
  "created_at": "2025-03-11T10:30:00Z"
}
```

## 🎨 Brand

- **Name**: Tatva.ai (तत्व)
- **Tagline**: Giving Voice to Ancient Wisdom
- **Colors**: Orange → Red → Purple gradient
- **Logo**: Devanagari "त" symbol

See [BRAND_IDENTITY.md](assets/BRAND_IDENTITY.md) for full guidelines.

## 🌐 Deployment

### Recommended: Railway (Free)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template)

### Other Options
| Platform | Cost | Link |
|----------|------|------|
| Railway | Free-$5/mo | [Deploy](deployment/DEPLOYMENT_GUIDE.md#option-1-railwayapp) |
| Render | Free-$7/mo | [Deploy](deployment/DEPLOYMENT_GUIDE.md#option-2-rendercom) |
| Fly.io | Free-$2/mo | [Deploy](deployment/DEPLOYMENT_GUIDE.md#option-3-flyio) |
| Hetzner | $3.50/mo | [Deploy](deployment/DEPLOYMENT_GUIDE.md#option-6-vps) |

See [DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) for detailed instructions.

## 📂 Project Structure

```
tatvai/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile          # Container config
├── frontend/
│   └── index.html          # Single-page app
├── assets/
│   └── BRAND_IDENTITY.md   # Logo, colors, fonts
├── deployment/
│   └── DEPLOYMENT_GUIDE.md # Hosting options
├── docker-compose.yml      # Full stack deployment
└── nginx.conf             # Web server config
```

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11
- **AI Model**: OpenAI Whisper
- **Frontend**: HTML5, Tailwind CSS, Vanilla JS
- **Container**: Docker, Docker Compose
- **Web Server**: Nginx

## 📊 Model Sizes

| Model | Size | Speed | Accuracy | VRAM |
|-------|------|-------|----------|------|
| Tiny | 39MB | ⚡⚡⚡ | ⭐⭐ | ~1GB |
| Base | 74MB | ⚡⚡ | ⭐⭐⭐ | ~1GB |
| Small | 244MB | ⚡ | ⭐⭐⭐⭐ | ~2GB |
| Medium | 769MB | 🐢 | ⭐⭐⭐⭐⭐ | ~5GB |

## 🤝 Contributing

Contributions welcome! Areas to help:
- [ ] Fine-tuning for Telugu/Sanskrit
- [ ] Mobile app (React Native/Flutter)
- [ ] Additional export formats
- [ ] Better error handling
- [ ] Multi-language support

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- OpenAI Whisper for the base ASR model
- AI4Bharat for Indic language research
- OpenSLR for Telugu datasets
- IIT Bombay for Sanskrit corpus (Vāksañcayaḥ)

## 📞 Contact

- Website: https://tatvai.app
- Twitter: [@tatvai](https://twitter.com/tatvai)
- Email: hello@tatvai.app

---

<div align="center">
  <p>Built with ❤️ for Indian languages</p>
  <p>
    <span class="font-telugu">ధన్యవాదాలు</span> • 
    <span class="font-sanskrit">धन्यवादः</span>
  </p>
</div>
