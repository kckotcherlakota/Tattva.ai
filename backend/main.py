# Tatva.ai - Backend API
# FastAPI application for Telugu & Sanskrit ASR with Translation

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket
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
from chunker import split_audio_chunks, merge_transcriptions, get_audio_duration, MAX_FILE_SIZE, MAX_DURATION, CHUNK_DURATION
import asyncio
from pydantic import BaseModel
import numpy as np

# Try to import translation libraries
try:
    from transformers import pipeline
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("Warning: Transformers not installed. Translation features limited.")

# App configuration
app = FastAPI(
    title="Tatva.ai API",
    description="Audio-to-Text for Telugu & Sanskrit with Live Translation",
    version="2.0.0"
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
translation_pipelines = {}

def load_model(model_size: str = "large"):  # Changed default to "large"
    """Load Whisper model (cached)"""
    if model_size not in models:
        print(f"Loading Whisper {model_size} model...")
        models[model_size] = whisper.load_model(model_size)
        print(f"Model {model_size} loaded successfully!")
    return models[model_size]

def load_translation_pipeline(source_lang: str, target_lang: str):
    """Load translation pipeline for language pair"""
    if not TRANSLATION_AVAILABLE:
        return None
    
    pair_key = f"{source_lang}-{target_lang}"
    if pair_key not in translation_pipelines:
        try:
            # Use Facebook's M2M100 model for multilingual translation
            translation_pipelines[pair_key] = pipeline(
                "translation",
                model="facebook/m2m100_418M",
                src_lang=source_lang,
                tgt_lang=target_lang
            )
        except Exception as e:
            print(f"Error loading translation pipeline: {e}")
            return None
    return translation_pipelines.get(pair_key)

class TranscriptionRequest(BaseModel):
    language: str = "te"
    model_size: str = "large"  # Default to large for best accuracy
    translate_to: Optional[str] = None  # Optional: en, hi, etc.
    
class TranscriptionResponse(BaseModel):
    id: str
    text: str
    translation: Optional[str] = None
    language: str
    duration: float
    confidence: float
    created_at: str

class TranslationRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str

class TranslationResponse(BaseModel):
    original: str
    translated: str
    source_lang: str
    target_lang: str

@app.get("/")
async def root():
    return {
        "name": "Tatva.ai",
        "tagline": "Giving Voice to Ancient Wisdom",
        "version": "2.0.0",
        "languages": ["te", "sa"],
        "features": ["transcription", "translation", "live-streaming"],
        "models": ["tiny", "base", "small", "medium", "large"],
        "status": "operational"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "models_loaded": list(models.keys()),
        "translation_available": TRANSLATION_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """
    Translate text between languages
    
    - **text**: Text to translate
    - **source_lang**: Source language code (te, sa, en, hi)
    - **target_lang**: Target language code (en, hi, te, sa)
    """
    if not TRANSLATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Translation service not available")
    
    try:
        # Map language codes for M2M100
        lang_map = {
            "te": "te", "sa": "sa", "en": "en", "hi": "hi"
        }
        
        src = lang_map.get(request.source_lang, request.source_lang)
        tgt = lang_map.get(request.target_lang, request.target_lang)
        
        translator = load_translation_pipeline(src, tgt)
        if not translator:
            raise HTTPException(status_code=500, detail="Failed to load translation model")
        
        result = translator(request.text, max_length=512)
        translated_text = result[0]["translation_text"] if result else ""
        
        return TranslationResponse(
            original=request.text,
            translated=translated_text,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    language: str = "te",
    model_size: str = "large",  # Default to large
    translate_to: Optional[str] = None
):
    """
    Transcribe AUDIO file to text with optional translation
    
    - **audio**: Audio file ONLY (mp3, wav, m4a, ogg, flac, aac)
    - **language**: "te" for Telugu, "sa" for Sanskrit
    - **model_size**: tiny, base, small, medium, **large** (recommended)
    - **translate_to**: Optional target language for translation (en, hi)
    
    **Limits:**
    - Max file size: 500MB
    - Max duration: 60 minutes (1 hour)
    - Video files NOT supported
    """
    
    # Validate language
    if language not in ["te", "sa"]:
        raise HTTPException(status_code=400, detail="Language must be 'te' (Telugu) or 'sa' (Sanskrit)")
    
    # Validate file type - AUDIO ONLY
    allowed_types = [
        "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", 
        "audio/mp4", "audio/x-m4a", "audio/ogg", "audio/flac",
        "audio/aac", "audio/webm", "audio/opus"
    ]
    
    # Reject video files
    video_types = ["video/mp4", "video/avi", "video/mkv", "video/mov", "video/webm"]
    if audio.content_type in video_types:
        raise HTTPException(
            status_code=400, 
            detail="Video files not supported. Please extract audio first (MP3, WAV, M4A, OGG only)."
        )
    
    file_ext = Path(audio.filename).suffix.lower()
    allowed_exts = [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".webm", ".opus"]
    
    if audio.content_type not in allowed_types and file_ext not in allowed_exts:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {audio.content_type}. Audio files only (MP3, WAV, M4A, OGG, FLAC)."
        )
    
    # Generate unique ID
    transcription_id = str(uuid.uuid4())[:8]
    
    # Save uploaded file
    input_path = UPLOAD_DIR / f"{transcription_id}_{audio.filename}"
    wav_path = UPLOAD_DIR / f"{transcription_id}.wav"
    
    try:
        # Save uploaded file
        with open(input_path, "wb") as f:
            content = await audio.read()
            
            # Check file size
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413, 
                    detail=f"File too large. Max {MAX_FILE_SIZE/1024/1024:.0f}MB allowed."
                )
            
            f.write(content)
        
        # Convert to WAV if needed
        if file_ext != ".wav":
            await convert_to_wav(input_path, wav_path)
        else:
            wav_path = input_path
        
        # Check audio duration
        duration = get_audio_duration(wav_path)
        
        if duration > MAX_DURATION:
            raise HTTPException(
                status_code=413,
                detail=f"Audio too long. Max {MAX_DURATION/60:.0f} minutes allowed."
            )
        
        # Load model
        model = load_model(model_size)
        
        # Process long audio in chunks
        if duration > CHUNK_DURATION:
            print(f"Long audio detected ({duration:.0f}s). Processing in chunks...")
            
            # Split into chunks
            chunks = split_audio_chunks(wav_path, UPLOAD_DIR, CHUNK_DURATION)
            
            # Transcribe each chunk
            chunk_results = []
            for i, chunk_path in enumerate(chunks):
                print(f"Processing chunk {i+1}/{len(chunks)}...")
                chunk_result = model.transcribe(
                    str(chunk_path),
                    language=language,
                    task="transcribe"
                )
                chunk_results.append(chunk_result)
                
                # Clean up chunk
                if chunk_path != wav_path:
                    chunk_path.unlink()
            
            # Merge results
            result = merge_transcriptions(chunk_results)
        else:
            # Process normally for short audio
            result = model.transcribe(
                str(wav_path),
                language=language,
                task="transcribe"
            )
        
        # Calculate confidence
        segments = result.get("segments", [])
        avg_confidence = sum(s.get("avg_logprob", -1) for s in segments) / len(segments) if segments else 0
        confidence = min(max((avg_confidence + 1) / 2 * 100, 0), 100)
        
        # Get audio duration
        duration = result.get("duration", 0)
        
        # Optional translation
        translation = None
        if translate_to and TRANSLATION_AVAILABLE:
            try:
                translator = load_translation_pipeline(language, translate_to)
                if translator:
                    trans_result = translator(result["text"], max_length=512)
                    translation = trans_result[0]["translation_text"] if trans_result else None
            except Exception as e:
                print(f"Translation error: {e}")
        
        # Save transcript
        transcript_data = {
            "id": transcription_id,
            "text": result["text"],
            "translation": translation,
            "language": language,
            "language_name": "Telugu" if language == "te" else "Sanskrit",
            "duration": result.get("duration", duration),  # Use original duration
            "confidence": round(confidence, 2),
            "created_at": datetime.now().isoformat(),
            "model": f"whisper-{model_size}",
            "filename": audio.filename,
            "chunks_processed": len(chunks) if duration > CHUNK_DURATION else 1
        }
        
        transcript_path = TRANSCRIPTS_DIR / f"{transcription_id}.json"
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        # Cleanup temp files in background
        background_tasks.add_task(cleanup_files, input_path, wav_path if wav_path != input_path else None)
        
        return TranscriptionResponse(
            id=transcription_id,
            text=result["text"],
            translation=translation,
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

# WebSocket for live transcription
@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """WebSocket endpoint for live audio streaming and transcription"""
    await websocket.accept()
    
    try:
        # Load large model for best live transcription
        model = load_model("large")
        
        audio_buffer = []
        
        while True:
            # Receive audio chunks
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data.get("action") == "start":
                language = data.get("language", "te")
                await websocket.send_json({"status": "started", "language": language})
                
            elif data.get("action") == "chunk":
                # Process audio chunk
                chunk = np.array(data.get("audio", []))
                audio_buffer.extend(chunk)
                
                # Process every 3 seconds of audio
                if len(audio_buffer) >= 48000 * 3:  # 3 seconds at 16kHz
                    audio_array = np.array(audio_buffer[:48000 * 3])
                    
                    # Transcribe chunk
                    result = model.transcribe(audio_array, language=language, fp16=False)
                    
                    await websocket.send_json({
                        "type": "partial",
                        "text": result["text"],
                        "is_final": False
                    })
                    
                    # Keep last 0.5 seconds for context
                    audio_buffer = audio_buffer[-2400:]
                    
            elif data.get("action") == "stop":
                # Final transcription
                if audio_buffer:
                    audio_array = np.array(audio_buffer)
                    result = model.transcribe(audio_array, language=language, fp16=False)
                    
                    await websocket.send_json({
                        "type": "final",
                        "text": result["text"],
                        "is_final": True
                    })
                    
                audio_buffer = []
                
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()

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
    """Download transcription"""
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
        if data.get('translation'):
            text_content += f"""TRANSLATION:
{data['translation']}
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
                "translation_preview": data.get("translation", "")[:50] + "..." if data.get("translation") else None,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
