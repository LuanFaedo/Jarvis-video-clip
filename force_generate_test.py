import os
import sys
import logging

# Forçar UTF-8 no Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from pipeline_av import av_pipeline

# Configuração de Log para arquivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("force_generation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

audio_path = "audios/upload_1770292252.mp3"
tema = "Teste de Força Bruta - Jarvis V171"

print(f"=== INICIANDO GERAÇÃO FORÇADA DE VIDEOCLIPE ===")
print(f"Áudio: {audio_path}")
print(f"Tema: {tema}")
print("Este processo pode levar MUITO tempo. Não interrompa.")

try:
    final_path, message = av_pipeline.process_mp3(audio_path, tema_usuario=tema)
    print(f"RESULTADO: {message}")
    if final_path:
        print(f"VÍDEO GERADO EM: {final_path}")
    else:
        print("FALHA NA GERAÇÃO.")
except Exception as e:
    print(f"ERRO CRÍTICO NO TESTE: {e}")
