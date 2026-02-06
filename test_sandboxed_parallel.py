
import os
import asyncio
import logging
import time
import math
import shutil
from datetime import datetime
from playwright.async_api import async_playwright
from video_engine_async import AsyncJarvisVideoMaker

# Configuração de Logs (Nível INFO para clareza de paralelismo)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def fatiar_roteiro(roteiro, total_abas=4):
    """Divide o roteiro em partes iguais para os workers."""
    chunk_size = math.ceil(len(roteiro) / total_abas)
    return [roteiro[i:i + chunk_size] for i in range(0, len(roteiro), chunk_size)]

async def run_sandboxed_parallel_test():
    print("=== JARVIS V117: TESTE DE ARQUITETURA SANDBOXED (I/O ISOLADO) ===")
    
    # 1. SETUP DE DIRETÓRIOS (Hierárquico)
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    sessao_id = f"sessao_{int(time.time())}"
    base_sessao = os.path.join(os.getcwd(), "producao", data_hoje, sessao_id)
    
    os.makedirs(base_sessao, exist_ok=True)
    pasta_final = os.path.join(base_sessao, "final")
    os.makedirs(pasta_final, exist_ok=True)

    # Roteiro de Exemplo (12 cenas = 3 por worker)
    roteiro_completo = [
        "Scene 1: High mountains Establishing shot", "Scene 2: Eagle flying close", "Scene 3: Eagle diving fast",
        "Scene 4: Underwater fish swimming", "Scene 5: Shark approaching", "Scene 6: Bubbles and intense action",
        "Scene 7: Deep forest sunlight beams", "Scene 8: Deer running through grass", "Scene 9: Wolves chasing from distance",
        "Scene 10: Cyberpunk city skyline", "Scene 11: Neon signs flickering", "Scene 12: Flying car landing on rooftop"
    ]
    
    lotes = fatiar_roteiro(roteiro_completo, total_abas=4)
    maker = AsyncJarvisVideoMaker()

    async with async_playwright() as p:
        # Configuração de Browser (Single Context, Multiple Pages)
        ud = os.path.abspath("brave_profile_jarvis")
        paths = [r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"]
        brave_path = next((path for path in paths if os.path.exists(path)), None)

        browser = await p.chromium.launch_persistent_context(
            user_data_dir=ud,
            executable_path=brave_path,
            headless=False,
            viewport={'width': 1280, 'height': 720}
        )

        tarefas = []
        print(f"--> Criando {len(lotes)} Sandboxes...")
        
        for i, lote in enumerate(lotes):
            worker_dir = os.path.join(base_sessao, f"worker_{i}")
            # DISPARA OS WORKERS (Gather cuidará do paralelismo real)
            tarefas.append(maker.processar_lote_aba(browser, i, lote, worker_dir))
        
        print("--> Executando workers em paralelo (Aguarde logs sincronizados)...")
        start_time = time.time()
        
        # A MÁGICA DO ASYNCIO: Todos os workers iniciam quase ao mesmo tempo
        resultados = await asyncio.gather(*tarefas)
        
        end_time = time.time()
        print(f"\n✅ TODOS OS WORKERS FINALIZARAM EM {end_time - start_time:.1f}s")

        # 4. MONTAGEM FINAL (The Stitcher)
        print("--> Iniciando Montagem Final (Stitcher)...")
        todos_mp4 = []
        for i in range(len(lotes)):
            worker_dir = os.path.join(base_sessao, f"worker_{i}")
            if os.path.exists(worker_dir):
                # Coleta MP4 ordenados por nome (cena_0, cena_1...)
                files = sorted([os.path.join(worker_dir, f) for f in os.listdir(worker_dir) if f.endswith(".mp4")])
                todos_mp4.extend(files)

        if todos_mp4:
            print(f"--> Total de clips coletados: {len(todos_mp4)}")
            # Aqui poderíamos chamar o FFmpeg para concatenar
            print(f"--> Clips prontos para junção em: {pasta_final}")
        else:
            print("❌ Falha crítica: Nenhum vídeo foi gerado pelos workers.")

        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_sandboxed_parallel_test())
