import os
import logging
import time
from video_engine import JarvisVideoMaker

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_video_generation():
    print("=== JARVIS V112: TESTE DE GERAÇÃO DE VÍDEO (ATÔMICO) ===")
    
    base_dir = os.getcwd()
    output_folder = os.path.join(base_dir, "videoclipes", "test_v107")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    # Roteiro Curto
    roteiro = [
        "A majestic golden eagle soaring high above snow-capped mountains at sunset, cinematic lighting, 8k",
        "The eagle dives towards a crystal clear lake, water splashes, ultra realistic, slow motion"
    ]
    
    # Inicializa o motor
    maker = JarvisVideoMaker(base_dir=base_dir)
    
    # Forçamos o uso de um áudio existente para garantir a duração
    # Se não houver, criamos um arquivo vazio mas com nome válido?
    # Melhor: vamos usar o arquivo que vimos na pasta audios
    audio_path = os.path.join(base_dir, "audios", "upload_1769887373.mp3")
    
    print(f"--> Iniciando pipeline sequencial para {len(roteiro)} cenas...")
    
    try:
        # TENTATIVA 1: Usando o pipeline oficial
        # Se falhar a semente, vamos tentar entender o porquê
        videos, last_frame = maker.pipeline_video_sequencial(
            audio_path=audio_path, 
            roteiro=roteiro, 
            output_folder=output_folder,
            initial_image_path=None
        )
        
        if videos:
            print(f"\n✅ SUCESSO! {len(videos)} clips gerados.")
        else:
            print("\n❌ FALHA: O pipeline não gerou clipes.")
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")

if __name__ == "__main__":
    test_video_generation()