import os
import sys
import time
from moviepy.editor import AudioClip
from video_engine import JarvisVideoMaker

# Forçar UTF-8
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def make_silent_audio(duration=7, filename="test_silence.mp3"):
    make_frame = lambda t: 0
    clip = AudioClip(make_frame, duration=duration)
    clip.write_audiofile(filename, fps=44100, verbose=False, logger=None)
    return filename

def test_pipeline():
    print("=== TESTE DE GERACAO DE VIDEO (V180) ===")
    print("Objetivo: Validar envio de prompt apos upload de imagem.")
    
    # 1. Gerar Audio Curto (4s -> 1 clip)
    try:
        audio_path = make_silent_audio(duration=4, filename="test_audio_4s.mp3")
        audio_path = os.path.abspath(audio_path)
    except Exception as e:
        print(f"Erro ao criar audio: {e}")
        return

    # 2. Roteiro Simples
    roteiro = ["Cyberpunk city flyover, neon lights, 8k"]
    
    # 3. Instanciar Engine
    maker = JarvisVideoMaker(base_dir=os.getcwd())
    
    print(f"Iniciando Pipeline para {audio_path}...")
    try:
        videos, _ = maker.pipeline_video_sequencial(
            audio_path=audio_path,
            roteiro=roteiro,
            output_folder=maker.output_dir
        )
        
        if videos and len(videos) > 0:
            print(f"\nSUCESSO! {len(videos)} videos gerados.")
            for v in videos:
                print(f" - {v}")
        else:
            print("\nFALHA: Nenhum video gerado.")
            
    except Exception as e:
        print(f"\nERRO CRITICO: {e}")

if __name__ == "__main__":
    test_pipeline()