import os
from moviepy.editor import AudioFileClip

# Configurações
BASE_DIR = os.getcwd()
AUDIO_DIR = os.path.join(BASE_DIR, "musica-para-videoclip")
INPUT_FILE = os.path.join(AUDIO_DIR, "PROTOCOLO_ WAKE UP PATRIQUE.mp3")
OUTPUT_FILE = os.path.join(AUDIO_DIR, "musica_30s.mp3")

def cortar_audio():
    print(f"[Jarvis] Processando áudio: {INPUT_FILE}")
    if not os.path.exists(INPUT_FILE):
        print("[Erro] Arquivo de áudio não encontrado.")
        return

    try:
        audio = AudioFileClip(INPUT_FILE)
        # Corta de 0 a 30 segundos
        clip_cortado = audio.subclip(0, 30)
        clip_cortado.write_audiofile(OUTPUT_FILE)
        audio.close()
        clip_cortado.close()
        print(f"[Sucesso] Áudio cortado salvo em: {OUTPUT_FILE}")
    except Exception as e:
        print(f"[Erro ao processar áudio] {e}")

if __name__ == "__main__":
    cortar_audio()
