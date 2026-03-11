# Tatva.ai - Backend API
# FastAPI application for Telugu & Sanskrit ASR

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import whisper
import torch
import torchaudio
import tempfile
import os
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import asyncio
from pydantic import BaseModel

# App configuration
app = FastAPI(
    title="Tatva.ai API",
    description="Audio-to-Text for Telugu & Sanskrit",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage paths
UPLOAD_DIR = Path("uploads")
TRANSCRIPTS_DIR = Path("transcripts")
UPLOAD_DIR.mkdir(exist_ok=True)
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

# Model cache
models = {}

def load_model(model_size: str = "small"):
    """Load Whisper model (cached)"""
    if model_size not in models:
        print(f"Loading Whisper {model_size} model...")
        models[model_size] = whisper.load_model(model_size)
    return models[model_size]

class TranscriptionRequest(BaseModel):
    language: str = "te"  # te for Telugu, sa for Sanskrit
    model_size: str = "small"  # tiny, base, small, medium
    
class TranscriptionResponse(BaseModel):
    id: str
    text: str
    language: str
    duration: float
    confidence: float
    created_at: str

@app.get("/")
async def root():
    return {
        "name": "Tatva.ai",
        "tagline": "Giving Voice to Ancient Wisdom",
        "version": "1.0.0",
        "languages": ["te", "sa"],
        "status": "operational"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    language: str = "te",
    model_size: str = "small"
):
    """
    Transcribe audio file to text
    
    - **audio**: Audio file (wav, mp3, m4a, ogg)
    - **language**: "te" for Telugu, "sa" for Sanskrit
    - **model_size**: tiny, base, small, medium, large
    """
    
    # Validate language
    if language not in ["te", "sa"]:
        raise HTTPException(status_code=400, detail="Language must be 'te' (Telugu) or 'sa' (Sanskrit)")
    
    # Validate file type
    allowed_types = ["audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a", "audio/ogg"]
    file_ext = Path(audio.filename).suffix.lower()
    
    if audio.content_type not in allowed_types and file_ext not in [".wav", ".mp3", ".m4a", ".ogg", ".mp4"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {audio.content_type}")
    
    # Generate unique ID
    transcription_id = str(uuid.uuid4())[:8]
    
    # Save uploaded file
    input_path = UPLOAD_DIR / f"{transcription_id}_{audio.filename}"
    wav_path = UPLOAD_DIR / f"{transcription_id}.wav"
    
    try:
        # Save uploaded file
        with open(input_path, "wb") as f:
            content = await audio.read()
            f.write(content)
        
        # Convert to WAV if needed
        if file_ext != ".wav":
            await convert_to_wav(input_path, wav_path)
        else:
            wav_path = input_path
        
        # Load model and transcribe
        model = load_model(model_size)
        
        result = model.transcribe(
            str(wav_path),
            language=language,
            task="transcribe"
        )
        
        # Calculate confidence (avg logprob)
        segments = result.get("segments", [])
        avg_confidence = sum(s.get("avg_logprob", -1) for s in segments) / len(segments) if segments else 0
        confidence = min(max((avg_confidence + 1) / 2 * 100, 0), 100)  # Normalize to 0-100
        
        # Get audio duration
        duration = result.get("duration", 0)
        
        # Save transcript
        transcript_data = {
            "id": transcription_id,
            "text": result["text"],
            "language": language,
            "language_name": "Telugu" if language == "te" else "Sanskrit",
            "duration": duration,
            "confidence": round(confidence, 2),
            "created_at": datetime.now().isoformat(),
            "model": f"whisper-{model_size}",
            "filename": audio.filename
        }
        
        transcript_path = TRANSCRIPTS_DIR / f"{transcription_id}.json"
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        # Cleanup temp files in background
        background_tasks.add_task(cleanup_files, input_path, wav_path if wav_path != input_path else None)
        
        return TranscriptionResponse(
            id=transcription_id,
            text=result["text"],
            language=language,
            duration=duration,
            confidence=round(confidence, 2),
            created_at=transcript_data["created_at"]
        )
        
    except Exception as e:
        # Cleanup on error
        if input_path.exists():
            input_path.unlink()
        if wav_path.exists() and wav_path != input_path:
            wav_path.unlink()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

async def convert_to_wav(input_path: Path, output_path: Path):
    """Convert audio to 16kHz mono WAV using torchaudio"""
    try:
        waveform, sample_rate = torchaudio.load(str(input_path))
        
        # Resample to 16kHz
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
        
        # Convert to mono
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        torchaudio.save(str(output_path), waveform, 16000)
        
    except Exception as e:
        # Fallback: assume ffmpeg is available
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-i", str(input_path),
            "-ar", "16000", "-ac", "1",
            str(output_path)
        ], check=True, capture_output=True)

def cleanup_files(*paths):
    """Remove temporary files"""
    for path in paths:
        if path and Path(path).exists():
            try:
                Path(path).unlink()
            except:
                pass

@app.get("/transcript/{transcription_id}")
async def get_transcript(transcription_id: str):
    """Get transcription by ID"""
    transcript_path = TRANSCRIPTS_DIR / f"{transcription_id}.json"
    
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    with open(transcript_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/transcript/{transcription_id}/download")
async def download_transcript(transcription_id: str, format: str = "txt"):
    """
    Download transcription
    
    - **format**: txt, json, srt (subtitles)
    """
    transcript_path = TRANSCRIPTS_DIR / f"{transcription_id}.json"
    
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    with open(transcript_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if format == "json":
        return FileResponse(
            transcript_path,
            media_type="application/json",
            filename=f"tatvai_{transcription_id}.json"
        )
    
    elif format == "txt":
        text_content = f"""Tatva.ai Transcription
========================
Language: {data['language_name']} ({data['language']})
Duration: {data['duration']:.2f} seconds
Confidence: {data['confidence']}%
Created: {data['created_at']}

TRANSCRIPTION:
{data['text']}
"""
        txt_path = TRANSCRIPTS_DIR / f"{transcription_id}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        
        return FileResponse(
            txt_path,
            media_type="text/plain",
            filename=f"tatvai_{transcription_id}.txt"
        )
    
    elif format == "srt":
        # Generate SRT subtitles if segments available
        srt_content = generate_srt(data)
        srt_path = TRANSCRIPTS_DIR / f"{transcription_id}.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        
        return FileResponse(
            srt_path,
            media_type="text/plain",
            filename=f"tatvai_{transcription_id}.srt"
        )
    
    else:
        raise HTTPException(status_code=400, detail="Format must be txt, json, or srt")

def generate_srt(data: dict) -> str:
    """Generate SRT subtitle format"""
    # This would need segment data stored - simplified version
    return f"""1
00:00:00,000 --> 00:00:05,000
{data['text'][:100]}...

Generated by Tatva.ai
"""

@app.get("/history")
async def get_history(limit: int = 10):
    """Get recent transcriptions"""
    transcripts = []
    
    for file_path in sorted(TRANSCRIPTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            transcripts.append({
                "id": data["id"],
                "language": data["language_name"],
                "preview": data["text"][:100] + "..." if len(data["text"]) > 100 else data["text"],
                "created_at": data["created_at"],
                "duration": data["duration"]
            })
    
    return {"transcripts": transcripts, "count": len(transcripts)}

@app.delete("/transcript/{transcription_id}")
async def delete_transcript(transcription_id: str):
    """Delete transcription"""
    transcript_path = TRANSCRIPTS_DIR / f"{transcription_id}.json"
    txt_path = TRANSCRIPTS_DIR / f"{transcription_id}.txt"
    srt_path = TRANSCRIPTS_DIR / f"{transcription_id}.srt"
    
    deleted = False
    for path in [transcript_path, txt_path, srt_path]:
        if path.exists():
            path.unlink()
            deleted = True
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    return {"message": "Transcription deleted"}

# Serve frontend static files (production)
if Path("../frontend/dist").exists():
    app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
