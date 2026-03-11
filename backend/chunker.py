"""
Audio chunking module for long files (1hr+ support)
"""

import subprocess
from pathlib import Path
import os
from typing import List, Tuple

def get_audio_duration(file_path: Path) -> float:
    """Get duration of audio file in seconds"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 
            'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
            str(file_path)
        ], capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except:
        return 0

def split_audio_chunks(input_path: Path, output_dir: Path, 
                       chunk_duration: int = 300) -> List[Path]:
    """
    Split audio into chunks for processing
    
    Args:
        input_path: Input audio file
        output_dir: Directory to save chunks
        chunk_duration: Duration of each chunk in seconds (default 5 min)
    
    Returns:
        List of chunk file paths
    """
    duration = get_audio_duration(input_path)
    
    if duration <= chunk_duration:
        # No need to split
        return [input_path]
    
    chunks = []
    base_name = input_path.stem
    
    # Calculate number of chunks
    num_chunks = int(duration / chunk_duration) + 1
    
    print(f"Splitting {duration}s audio into {num_chunks} chunks...")
    
    for i in range(num_chunks):
        start_time = i * chunk_duration
        chunk_path = output_dir / f"{base_name}_chunk_{i:03d}.wav"
        
        # Extract chunk with ffmpeg
        subprocess.run([
            'ffmpeg', '-y', '-i', str(input_path),
            '-ss', str(start_time),
            '-t', str(chunk_duration),
            '-ar', '16000',  # 16kHz for Whisper
            '-ac', '1',      # Mono
            '-c:a', 'pcm_s16le',
            str(chunk_path)
        ], check=True, capture_output=True)
        
        chunks.append(chunk_path)
        print(f"Created chunk {i+1}/{num_chunks}: {chunk_path.name}")
    
    return chunks

def merge_transcriptions(chunk_results: List[dict]) -> dict:
    """
    Merge transcription results from multiple chunks
    
    Args:
        chunk_results: List of whisper results from each chunk
    
    Returns:
        Merged result dict
    """
    full_text = []
    total_duration = 0
    segments = []
    
    for i, result in enumerate(chunk_results):
        # Adjust timestamps for this chunk
        chunk_offset = i * 300  # 5 minutes per chunk
        
        for segment in result.get("segments", []):
            adjusted_segment = segment.copy()
            adjusted_segment["start"] += chunk_offset
            adjusted_segment["end"] += chunk_offset
            segments.append(adjusted_segment)
        
        full_text.append(result.get("text", ""))
        total_duration += result.get("duration", 0)
    
    # Calculate average confidence
    avg_logprob = sum(s.get("avg_logprob", -1) for s in segments) / len(segments) if segments else -1
    confidence = min(max((avg_logprob + 1) / 2 * 100, 0), 100)
    
    return {
        "text": " ".join(full_text).strip(),
        "segments": segments,
        "duration": total_duration,
        "language": chunk_results[0].get("language") if chunk_results else None,
        "confidence": confidence
    }

# Maximum file sizes and durations
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
MAX_DURATION = 3600  # 1 hour
CHUNK_DURATION = 300  # 5 minutes per chunk
