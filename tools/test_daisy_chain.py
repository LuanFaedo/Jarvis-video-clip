import os
import sys
import time
import logging

# Adiciona a raiz do projeto ao path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from video_engine import JarvisVideoMaker

# Configuração de Log para ver o que acontece internamente
logging.basicConfig(level=logging.INFO)

def test_sequencial():
    print("\n" + "="*60)
    print("🧪 TESTE DE CONTINUIDADE (DAISY CHAIN) - JARVIS V12")
    print("="*60)
    
    maker = JarvisVideoMaker()
    
    # Roteiro curto: 2 cenas de 5 segundos cada
    roteiro = [
        "A cyberpunk city in the rain, neon lights flickering.",
        "A drone flying through the skyscrapers of the neon city."
    ]
    
    # Pasta temporária para o teste
    output_folder = os.path.join(os.getcwd(), "teste_fluxo_output")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    print(f"[TESTE] Iniciando pipeline sequencial...")
    print(f"[TESTE] Destino: {output_folder}")
    
    try:
        # Executa apenas 2 cenas para validar o fluxo de "Colar última imagem"
        videos, last_ref = maker.pipeline_video_sequencial(
            audio_path=None, # Sem áudio para ser mais rápido (ele usará duração default)
            roteiro=roteiro[:2], 
            output_folder=output_folder
        )
        
        print("\n" + "="*40)
        print("📊 RESULTADOS DO TESTE")
        print("="*40)
        print(f"Vídeos gerados: {len(videos)}")
        for v in videos:
            print(f" - {os.path.basename(v)}")
            
        print(f"Última Referência (Semente): {last_ref}")
        
        if len(videos) >= 2 and os.path.exists(last_ref):
            print("\n✅ SUCESSO: A continuidade funcionou e gerou pelo menos 2 clipes com referência.")
        else:
            print("\n❌ FALHA: O fluxo de continuidade não foi completado corretamente.")
            
    except Exception as e:
        print(f"\n❌ ERRO DURANTE O TESTE: {e}")

if __name__ == "__main__":
    test_sequencial()
