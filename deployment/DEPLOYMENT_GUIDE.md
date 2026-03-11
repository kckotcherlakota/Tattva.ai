# Tatva.ai - Deployment Guide
## Cheap & Free Hosting Options

---

## Option 1: Railway.app (RECOMMENDED) ⭐
**Cost: $0-5/month | Difficulty: Easy**

### Why Railway?
- Free tier: $5 credit/month (enough for small app)
- Automatic HTTPS
- Easy deployment from GitHub
- Auto-scaling
- Good for MVPs

### Steps:
1. Push code to GitHub
2. Sign up at railway.app (use GitHub login)
3. Click "New Project" → "Deploy from GitHub"
4. Select your repo
5. Add environment variables if needed
6. Deploy!

### Pricing:
- **Free tier**: 512 MB RAM, shared CPU, 1GB disk
- **Starter**: $5/month → 1GB RAM, better CPU
- **Pro**: $25/month → 2GB RAM (for production)

**Good for**: Startups, MVPs, testing

---

## Option 2: Render.com
**Cost: $0-7/month | Difficulty: Easy**

### Steps:
1. Push code to GitHub
2. Sign up at render.com
3. Create "Web Service"
4. Connect GitHub repo
5. Configure:
   - Build Command: `docker-compose build`
   - Start Command: `docker-compose up`
6. Deploy

### Pricing:
- **Free**: Web services sleep after 15min idle (slow cold start)
- **Starter**: $7/month → Always on, 512MB RAM

**Note**: Whisper models need RAM. Free tier might struggle with large models.

---

## Option 3: Fly.io
**Cost: $0-2/month | Difficulty: Medium**

### Why Fly.io?
- Run Docker containers globally
- Free tier: 3 shared-cpu-1x VMs, 256MB RAM
- Very fast (runs on edge)
- Great for global users

### Steps:
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch
fly launch

# Deploy
fly deploy
```

### Pricing:
- **Free**: 2340 hours/month, 256MB RAM
- **Paid**: ~$2/month per 256MB RAM

**Tip**: Use smallest Whisper model (tiny) on free tier.

---

## Option 4: AWS Free Tier
**Cost: $0 (12 months) | Difficulty: Hard**

### Services to use:
- **EC2 t2.micro**: 750 hours/month free
- **S3**: 5GB storage free

### Steps:
1. Create AWS account
2. Launch EC2 instance (Ubuntu)
3. Install Docker
4. Deploy with docker-compose
5. Configure security group (ports 80, 443)

### Gotchas:
- Requires credit card (won't be charged if under limits)
- Must monitor usage to avoid charges
- More complex setup

---

## Option 5: Google Cloud Run
**Cost: $0-10/month | Difficulty: Medium**

### Why Cloud Run?
- Serverless containers
- Pay only when running
- 2 million requests/month free
- Auto-scaling to zero

### Steps:
1. Push Docker image to GCR
2. Deploy to Cloud Run
3. Configure memory (1-2GB for Whisper)

### Pricing:
- **Free**: 2M requests, 360K GB-seconds
- **Paid**: ~$0.00002400/vCPU-second

**Note**: Cold starts can be slow (5-10s) as Whisper model loads.

---

## Option 6: VPS (Hetzner/DO/Linode)
**Cost: $4-6/month | Difficulty: Medium**

### Recommended: Hetzner Cloud
- CX11: 1 vCPU, 2GB RAM = €3.29/month (~$3.50)
- More RAM than others for same price
- Reliable German hosting

### Steps:
1. Sign up at hetzner.com/cloud
2. Create CX11 server (Ubuntu)
3. SSH into server
4. Install Docker + docker-compose
5. Clone repo and deploy

### Other VPS Options:
| Provider | Cheapest Plan | RAM | Cost |
|----------|--------------|-----|------|
| Hetzner | CX11 | 2GB | $3.50/mo |
| DigitalOcean | Basic | 512MB | $4/mo |
| Linode | Nanode | 1GB | $5/mo |
| Vultr | Cloud Compute | 1GB | $5/mo |

---

## Cost Comparison Summary

| Platform | Free Tier | Paid (Min) | Best For |
|----------|-----------|------------|----------|
| **Railway** | $5 credit/mo | $5/mo | Easiest setup |
| **Render** | Limited | $7/mo | Simple web apps |
| **Fly.io** | 256MB RAM | $2/mo | Global edge |
| **AWS** | 12 months | ~$5/mo | Enterprise |
| **GCP** | 2M requests | ~$10/mo | Serverless |
| **Hetzner** | None | $3.50/mo | Cheapest VPS |

---

## Recommended Setup by Stage

### MVP/Testing (Now)
**Railway Free Tier**
- Zero cost
- Easy deployment
- Good enough for demos

### Production (Later)
**Hetzner CX11 ($3.50/mo)**
- Cheapest reliable option
- 2GB RAM handles Whisper small
- Full control

### Scale (High traffic)
**Fly.io or Railway Pro**
- Auto-scaling
- Global CDN
- $20-50/month

---

## Quick Deploy: Railway (Step-by-Step)

### 1. Prepare Repo
```bash
cd tatvai
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOURNAME/tatvai.git
git push -u origin main
```

### 2. Deploy
1. Go to railway.app
2. Click "New Project"
3. "Deploy from GitHub repo"
4. Select tatvai
5. Railway auto-detects Dockerfile
6. Click "Deploy"

### 3. Add Domain (Optional)
1. Project Settings → Domains
2. Add custom domain or use railway.app subdomain
3. Auto SSL enabled

Done! 🎉

---

## Environment Variables

Create `.env` file:
```bash
# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Storage
MAX_FILE_SIZE=26214400  # 25MB
UPLOAD_DIR=./uploads
TRANSCRIPTS_DIR=./transcripts

# Model (tiny, base, small, medium)
DEFAULT_MODEL_SIZE=small

# CORS
ALLOWED_ORIGINS=*
```

---

## Performance Optimization

### For Cheap Hosting (512MB-1GB RAM):
1. Use Whisper `tiny` or `base` model
2. Limit file size to 10MB
3. Process audio in chunks
4. Enable model caching

### For Better Hosting (2GB+ RAM):
1. Use Whisper `small` model (recommended)
2. 25MB file limit
3. Full features enabled

---

## Monitoring

Add to your backend:
```python
# Health check endpoint
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "timestamp": datetime.now().isoformat()
    }
```

Use UptimeRobot (free) to monitor:
- Check every 5 minutes
- Alert if down

---

## SSL/HTTPS

Most platforms provide free SSL:
- Railway: Auto SSL
- Render: Auto SSL
- Fly.io: Auto SSL
- Hetzner: Use Let's Encrypt + Caddy/Nginx

---

## Domain Setup

Buy domain from:
- Namecheap (~$10/year)
- Cloudflare (~$9/year)
- Google Domains (~$12/year)

Then point to your hosting platform.

---

## Launch Checklist

- [ ] Code pushed to GitHub
- [ ] Choose hosting platform
- [ ] Deploy application
- [ ] Test API endpoints
- [ ] Configure custom domain (optional)
- [ ] Set up monitoring
- [ ] Add analytics (Plausible/Google Analytics)
- [ ] Create social media accounts
- [ ] Prepare launch announcement

---

*Deploy Tatva.ai and give voice to ancient wisdom!* 🚀
