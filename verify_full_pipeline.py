import os
import time
import logging
from video_engine import JarvisVideoMaker

# Configuração de Logs para ver o que está acontecendo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_pipeline_real():
    print("=== TESTE DE PONTA A PONTA (PROMPT -> VÍDEO) ===")
    
    # 1. Limpeza
    print("🧹 Matando processos Brave...")
    os.system("taskkill /F /IM brave.exe >nul 2>&1")
    time.sleep(2)
    
    # 2. Setup
    maker = JarvisVideoMaker()
    output_dir = os.path.join(os.getcwd(), "teste_pipeline_output")
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    roteiro = ["A futuristic cyberpunk city with neon lights, raining, cinematic 8k"]
    
    print(f"🚀 Iniciando Pipeline para 1 cena...")
    print(f"📂 Output: {output_dir}")
    
    try:
        # Passa roteiro e força 1 clipe (lógica interna calcula clips baseada em duração, vamos simular via roteiro)
        # Nota: pipeline_video_sequencial espera audio_path. Se None, usa roteiro.
        videos, ref = maker.pipeline_video_sequencial(
            audio_path=None, 
            roteiro=roteiro, 
            output_folder=output_dir
        )
        
        if videos and len(videos) > 0:
            print(f"\n✅ SUCESSO! Vídeos gerados: {len(videos)}")
            print(f"📹 Arquivo: {videos[0]}")
            if os.path.exists(videos[0]) and os.path.getsize(videos[0]) > 1000:
                print("✅ Arquivo de vídeo validado (tamanho OK).")
            else:
                print("❌ Arquivo de vídeo vazio ou inválido.")
        else:
            print("\n❌ FALHA: Nenhum vídeo foi retornado pelo pipeline.")
            
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO DURANTE EXECUÇÃO: {e}")

if __name__ == "__main__":
    test_pipeline_real()
