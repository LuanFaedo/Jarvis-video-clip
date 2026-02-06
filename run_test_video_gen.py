import os
import sys
import time
from music_video_handler import _thread_processar_video

# Configuração
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_FILE = "upload_1769998325.mp3"
AUDIO_PATH = os.path.join(BASE_DIR, "audios", AUDIO_FILE)

# Mock de ambiente para garantir que funcione fora do app.py
os.environ["API_BASE_URL"] = "http://127.0.0.1:11434/v1"

def run_test():
    print("==================================================")
    print("🎬 INICIANDO TESTE MANUAL DE GERAÇÃO DE VÍDEO")
    print("==================================================")
    
    if not os.path.exists(AUDIO_PATH):
        print(f"❌ Erro: Arquivo de áudio não encontrado: {AUDIO_PATH}")
        return

    print(f"🎵 Áudio Alvo: {AUDIO_FILE}")
    print(f"📂 Caminho: {AUDIO_PATH}")
    print("🧠 Tema Visual: Cyberpunk Neon City (Teste)")
    
    try:
        # Chama diretamente o handler
        # User ID fictício para logs
        _thread_processar_video("TESTE_MANUAL_DEV", AUDIO_PATH, "Cyberpunk Neon City, 8k, cinematic lighting, futuristic")
        
        print("\n✅ Processo de thread iniciado (Verifique os logs do Worker/Playwright)")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar processo: {e}")

if __name__ == "__main__":
    run_test()
