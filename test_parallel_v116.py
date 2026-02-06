import os
import asyncio
import logging
import time
from playwright.async_api import async_playwright
from video_engine_async import AsyncJarvisVideoMaker

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def run_parallel_test():
    print("=== JARVIS V116: TESTE DE GERAÇÃO PARALELA (4 ABAS) ===")
    
    maker = AsyncJarvisVideoMaker()
    base_dir = os.getcwd()
    pasta_raw = os.path.join(base_dir, "temp_clips", f"test_parallel_{int(time.time())}")
    os.makedirs(pasta_raw, exist_ok=True)

    # Roteiro Curto: 1 cena por worker (total 4 cenas)
    lotes = [
        ["A futuristic car speeding through a neon city at night, side view, 8k"],
        ["A majestic waterfall in a lush jungle, aerial drone shot, 8k"],
        ["An astronaut floating in deep space, looking at a distant galaxy, 8k"],
        ["A cozy cabin in the snow with a warm fire visible through the window, 8k"]
    ]

    async with async_playwright() as p:
        # Configuração do Browser
        ud = os.path.abspath("brave_profile_jarvis")
        paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
        ]
        brave_path = next((path for path in paths if os.path.exists(path)), None)

        print(f"--> Iniciando Browser Context em: {brave_path}")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=ud,
            executable_path=brave_path,
            headless=False,
            viewport={'width': 1280, 'height': 720},
            args=["--disable-blink-features=AutomationControlled"]
        )

        print(f"--> Disparando {len(lotes)} workers em paralelo...")
        start_time = time.time()
        
        # Criação das tarefas
        tarefas = []
        for i, lote in enumerate(lotes):
            tarefas.append(maker.processar_lote_aba(browser, i, lote, pasta_raw))
        
        # Execução PARALELA
        resultados = await asyncio.gather(*tarefas)
        
        end_time = time.time()
        duracao = end_time - start_time
        
        total_videos = sum(len(r) for r in resultados)
        print(f"\n✅ TESTE CONCLUÍDO EM {duracao:.1f}s")
        print(f"Total de vídeos gerados: {total_videos}")
        print(f"Arquivos salvos em: {pasta_raw}")

        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_parallel_test())
