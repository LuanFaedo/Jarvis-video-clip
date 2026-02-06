import os
import sys
import asyncio
import logging
from playwright.async_api import async_playwright

# Configuração de Path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from video_engine_async import AsyncJarvisVideoMaker

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_f5_recovery():
    print("\n" + "="*60)
    print("🧪 TESTE DE RECUPERAÇÃO F5 (ASYNC) - JARVIS V12")
    print("="*60)
    
    maker = AsyncJarvisVideoMaker(base_dir=BASE_DIR)
    
    # Roteiro: 1 cena complexa para dar tempo de testar o timeout
    cenas = ["Cyberpunk detective walking in rain, neon reflection, 8k render"]
    
    output_dir = os.path.join(BASE_DIR, "teste_fluxo_output")
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    worker_dir = os.path.join(output_dir, "worker_test")
    
    async with async_playwright() as p:
        # Configuração REAL do Brave (igual ao sistema de produção)
        ud = os.path.join(BASE_DIR, "brave_profile_jarvis")
        
        # Caminhos possíveis do Brave no Windows
        paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe", 
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe", 
            os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
        ]
        brave_path = next((path for path in paths if os.path.exists(path)), None)
        
        if not brave_path:
            print("❌ ERRO: Executável do Brave não encontrado!")
            return

        print(f"[TESTE] Iniciando Brave em: {brave_path}")
        print(f"[TESTE] Perfil: {ud}")

        # Lança o contexto persistente (igual ao video_engine.py)
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=ud, 
            executable_path=brave_path, 
            headless=False, 
            viewport={'width': 1280, 'height': 720},
            accept_downloads=True, 
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        print("[TESTE] Navegador aberto. Iniciando processamento...")
        try:
            # Chama a função principal
            videos = await maker.processar_lote_aba(browser, 99, cenas, worker_dir)
            
            print("\n" + "="*40)
            print("📊 RELATÓRIO DO TESTE")
            print("="*40)
            
            if videos and len(videos) > 0:
                print(f"✅ SUCESSO! Vídeo gerado: {videos[0]}")
                print("O sistema recuperou ou finalizou corretamente.")
            else:
                print("❌ FALHA: Nenhum vídeo gerado.")
                
        except Exception as e:
            print(f"❌ ERRO CRÍTICO NO TESTE: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_f5_recovery())
