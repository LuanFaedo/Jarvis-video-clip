
import os
import logging
import json
import time
from music_video_handler import gerar_roteiro_inteligente
from video_engine import JarvisVideoMaker

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def test_evolutionary_narrative():
    print("=== JARVIS V115: TESTE DE NARRATIVA EVOLUTIVA ===")
    
    tema = "A futuristic robot discovering a small flower in a post-apocalyptic wasteland"
    duracao = 15 # 3 cenas de 5s
    
    print(f"--> Solicitando roteiro evolutivo para: {tema}")
    
    # 1. GERAÇÃO DO ROTEIRO COM O NOVO SYSTEM PROMPT
    storyboard = gerar_roteiro_inteligente(tema, duracao)
    
    print("\n🎬 ROTEIRO GERADO PELO DIRETOR V115:")
    for i, cena in enumerate(storyboard):
        print(f"   [CENA {i+1}]: {cena}")
    
    print("\n--> Analisando variedade de câmera e progressão...")
    # Verifica se há termos de câmera variados
    cam_terms = ["drone", "close-up", "tracking", "dolly", "wide", "zoom", "pan", "bokeh"]
    found_terms = [t for t in cam_terms if any(t in s.lower() for s in storyboard)]
    print(f"--> Termos cinematográficos detectados: {found_terms}")

    # 2. EXECUÇÃO DA PRODUÇÃO
    print("\n--> Iniciando produção visual (Brave Browser)...")
    maker = JarvisVideoMaker()
    output_folder = os.path.join(os.getcwd(), "videoclipes", "test_narrative_v115")
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    
    # Usar áudio local para o teste de sincronia
    audio_path = os.path.abspath("audios/upload_1769887373.mp3")
    
    videos, last_frame = maker.pipeline_video_sequencial(
        audio_path=audio_path,
        roteiro=storyboard,
        output_folder=output_folder
    )
    
    if videos:
        print(f"\n✅ SUCESSO! Produção evolutiva concluída com {len(videos)} clipes.")
    else:
        print("\n❌ FALHA: A produção não gerou vídeos.")

if __name__ == "__main__":
    test_evolutionary_narrative()
