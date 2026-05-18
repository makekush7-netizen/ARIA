"""
Standalone Kokoro TTS Engine
Copy this entire KokoroTTS folder to any project and use it!

SETUP:
1. pip install kokoro-onnx numpy scipy sounddevice
2. Download models to this folder:
   - kokoro-v1.0.onnx (from HuggingFace)
   - voices-v1.0.bin (from HuggingFace)
3. Import and use:

   from KokoroTTS.tts_engine import KokoroTTS
   
   tts = KokoroTTS()
   tts.speak("Hello world!", voice="af_nicole")
   
AVAILABLE VOICES:
   Female: af_sarah, af_nicole, af_sky
   Male: am_michael, am_adam, am_liam
"""

from pathlib import Path
import numpy as np
from scipy.io import wavfile
try:
    import sounddevice as sd
except ImportError:
    sd = None
import threading
import re
import unicodedata
import hashlib
from concurrent.futures import ThreadPoolExecutor


class KokoroTTS:
    """
    Standalone Kokoro TTS Engine
    
    Usage:
        tts = KokoroTTS()
        tts.speak("Hello world!")
        tts.speak("Different voice", voice="am_michael")
        tts.save("Text to save", "output.wav")
    """
    
    def __init__(self, model_dir=None):
        """
        Initialize Kokoro TTS
        
        Args:
            model_dir: Directory containing kokoro-v1.0.onnx and voices-v1.0.bin
                      Defaults to this file's directory
        """
        from kokoro_onnx import Kokoro
        
        if model_dir is None:
            model_dir = Path(__file__).parent
        
        self.model_dir = Path(model_dir)
        self.model_path = self.model_dir / "kokoro-v1.0.onnx"
        self.voices_path = self.model_dir / "voices-v1.0.bin"
        
        # Check if models exist
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Kokoro model not found: {self.model_path}\n"
                "Download from: https://huggingface.co/hexgrad/Kokoro-82M-v1.0-ONNX"
            )
        if not self.voices_path.exists():
            raise FileNotFoundError(
                f"Voices file not found: {self.voices_path}\n"
                "Download from: https://huggingface.co/hexgrad/Kokoro-82M-v1.0-ONNX"
            )
        
        # Initialize Kokoro
        self.kokoro = Kokoro(str(self.model_path), str(self.voices_path))
        self.sample_rate = 24000
        
        # Cache and threading
        self.cache = {}
        self.worker_pool = ThreadPoolExecutor(max_workers=2)
        self.synthesis_lock = threading.Lock()
        
        print(f"[KokoroTTS] Initialized successfully")
    
    def get_voices(self):
        """Get available voices"""
        return {
            "female": ["af_sarah", "af_nicole", "af_sky"],
            "male": ["am_michael", "am_adam", "am_liam"]
        }
    
    def synthesize(self, text, voice="af_sky", speed=1.0, lang="en-us"):
        """
        Generate audio from text (returns numpy array)
        
        Args:
            text: Text to synthesize
            voice: Voice ID (default: af_sky)
            speed: Speech speed (default: 1.0)
            lang: Language code (default: en-us)
        
        Returns:
            tuple: (audio_samples, sample_rate)
        """
        samples, sr = self.kokoro.create(
            text,
            voice=voice,
            speed=speed,
            lang=lang
        )
        return samples, sr
    
    def play(self, samples, sample_rate=None):
        """Play audio samples directly"""
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        # Normalize if needed
        if np.max(np.abs(samples)) > 1.0:
            samples = samples / np.max(np.abs(samples))
        
        sd.play(samples, sample_rate)
        duration = len(samples) / sample_rate
        sd.wait()
        return duration
    
    def save(self, text, output_path, voice="af_sky", speed=1.0, lang="en-us"):
        """
        Synthesize and save to WAV file
        
        Args:
            text: Text to synthesize
            output_path: Output file path
            voice: Voice ID
            speed: Speech speed
            lang: Language code
        
        Returns:
            str: Saved file path
        """
        samples, sr = self.synthesize(text, voice, speed, lang)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Normalize and convert to 16-bit PCM
        if np.max(np.abs(samples)) > 1.0:
            samples = samples / np.max(np.abs(samples))
        samples_int16 = np.int16(samples * 32767)
        
        wavfile.write(output_path, sr, samples_int16)
        return str(output_path)
    
    def speak(self, text, voice="af_sky", speed=1.0, lang="en-us", use_cache=True):
        """
        Synthesize and play text directly
        
        Args:
            text: Text to speak
            voice: Voice ID (default: af_sky)
            speed: Speech speed (default: 1.0)
            lang: Language code (default: en-us)
            use_cache: Use cached audio if available (default: True)
        
        Returns:
            float: Duration in seconds
        """
        # Check cache
        if use_cache:
            cache_key = self._text_hash(text, voice, speed, lang)
            if cache_key in self.cache:
                samples, sr = self.cache[cache_key]
                return self.play(samples, sr)
        
        # Synthesize
        samples, sr = self.synthesize(text, voice, speed, lang)
        
        # Store in cache
        if use_cache:
            self.cache[cache_key] = (samples, sr)
        
        # Play
        return self.play(samples, sr)
    
    def speak_long(self, text, voice="af_sky", speed=1.0, lang="en-us", chunk_size=300):
        """
        Speak long text with chunking and streaming
        
        Args:
            text: Long text to speak
            voice: Voice ID
            speed: Speech speed
            lang: Language code
            chunk_size: Max characters per chunk (default: 300)
        
        Returns:
            float: Total duration in seconds
        """
        # Split into chunks
        chunks = self._split_text(text, max_chars=chunk_size)
        
        if len(chunks) == 1:
            return self.speak(chunks[0], voice, speed, lang)
        
        print(f"[KokoroTTS] Streaming {len(chunks)} chunks...")
        
        # Process chunks
        total_duration = 0
        for i, chunk in enumerate(chunks):
            duration = self.speak(chunk, voice, speed, lang)
            total_duration += duration
            print(f"  [{i+1}/{len(chunks)}] {chunk[:40]}... ({duration:.1f}s)")
        
        return total_duration
    
    def _split_text(self, text, max_chars=300):
        """Split text into manageable chunks"""
        txt = " ".join(text.strip().split())
        sentence_end = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_end.split(txt)
        
        chunks = []
        current = ""
        
        for s in sentences:
            if len(current) + len(s) + 1 <= max_chars:
                current = (current + " " + s).strip() if current else s
            else:
                if current:
                    chunks.append(current)
                if len(s) > max_chars:
                    # Split long sentences by commas
                    parts = re.split(r'([,;:])', s)
                    temp = ""
                    for p in parts:
                        if len(temp) + len(p) <= max_chars:
                            temp = (temp + p).strip()
                        else:
                            if temp:
                                chunks.append(temp)
                            temp = p.strip()
                    if temp:
                        chunks.append(temp)
                    current = ""
                else:
                    current = s
        
        if current:
            chunks.append(current)
        
        return chunks
    
    def _text_hash(self, text, voice, speed, lang):
        """Create cache key"""
        text = " ".join(text.strip().split()).lower()
        text = unicodedata.normalize("NFKC", text)
        key = f"{text}|{voice}|{speed}|{lang}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear the audio cache"""
        self.cache.clear()
        print("[KokoroTTS] Cache cleared")


# Quick access function
def create_tts(model_dir=None):
    """Create a KokoroTTS instance"""
    return KokoroTTS(model_dir)


# Example usage when run directly
if __name__ == "__main__":
    print("="*60)
    print("KokoroTTS - Standalone Text-to-Speech Engine")
    print("="*60)
    
    try:
        tts = KokoroTTS()
        
        print("\nAvailable voices:")
        voices = tts.get_voices()
        print(f"  Female: {', '.join(voices['female'])}")
        print(f"  Male: {', '.join(voices['male'])}")
        
        print("\nDemo: Speaking with different voices...")
        
        # Demo each voice
        demos = [
            ("Hello! I'm Sarah.", "af_sarah"),
            ("Hey there! Nicole here.", "af_nicole"),
            ("Hi! This is Sky speaking.", "af_sky"),
            ("Hello, I'm Michael.", "am_michael"),
        ]
        
        for text, voice in demos:
            print(f"\n[{voice}] {text}")
            tts.speak(text, voice=voice)
        
        print("\n" + "="*60)
        print("Demo complete!")
        print("="*60)
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("\nPlease download the model files to this folder.")
