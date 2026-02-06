import os
import sys
import time
import logging

# Adiciona a raiz do projeto ao path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from music_video_handler import _thread_processar_video

# Configuração de Log para ver tudo acontecendo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def teste_completo_producao():
    print("\n" + "="*60)
    print("🎬 TESTE FINAL COMPLETO - JARVIS V12 (PRODUÇÃO REAL)")
    print("="*60)
    
    # 1. Definindo uma música alvo (Linkin Park - Numb, trecho curto ou similar para teste)
    # Vou usar uma string de busca que o yt-dlp vai resolver
    musica_teste = "Linkin Park Numb Official Video" 
    tema_visual = "Cyberpunk, Neon City, Rain, Sad Atmosphere"
    
    print(f"🎵 Música Alvo: {musica_teste}")
    print(f"🎨 Tema Visual: {tema_visual}")
    print("\n[INICIANDO] Disparando thread de produção no music_video_handler...")
    
    try:
        # Chama a função real que o app.py chama
        # User ID fictício "TESTE_DEV"
        _thread_processar_video("TESTE_DEV", musica_teste, tema_visual)
        
        print("\n✅ Thread disparada com sucesso!")
        print("Agora observe o navegador Brave abrir e monitorar o console para ver:")
        print("1. Download do Áudio")
        print("2. Geração do Roteiro (GPT-OSS)")
        print("3. Produção dos Clipes (Daisy Chain Corrigido)")
        print("4. Montagem Final (FFmpeg)")
        
    except Exception as e:
        print(f"\n❌ ERRO AO INICIAR: {e}")

if __name__ == "__main__":
    teste_completo_producao()
