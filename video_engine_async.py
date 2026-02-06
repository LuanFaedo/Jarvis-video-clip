import os
import asyncio
import time
import uuid
import cv2
import numpy as np
import pyperclip
import subprocess
import logging
from playwright.async_api import async_playwright

class AsyncJarvisVideoMaker:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.getcwd()
        self.meta_ai_url = "https://www.meta.ai"
        # Semáforo para garantir que apenas um worker use o clipboard por vez
        self.clipboard_lock = asyncio.Lock()

    async def _get_input(self, page):
        seletores = ["div[role='textbox']", "div[contenteditable='true']", "textarea"]
        for sel in seletores:
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=2000):
                    await loc.click(force=True)
                    return loc
            except: continue
        return None

    async def _download_video_async(self, page, save_path, vids_antes, worker_id):
        """Monitoramento robusto por índice (V119)."""
        logging.info(f"[Worker {worker_id}] Aguardando vÃ­deo novo (Ã­ndice > {vids_antes})...")
        start_time = time.time()
        # V192: Timeout aumentado para 25s
        while time.time() - start_time < 25:
            vids = await page.locator("video").all()
            if len(vids) > vids_antes:
                target = vids[vids_antes] 
                try:
                    src = await target.get_attribute("src")
                    if src and src.startswith("blob:"):
                        logging.info(f"[Worker {worker_id}] Capturando Blob via JS...")
                        js_fetch = "async (url) => { const r = await fetch(url); const b = await r.blob(); return new Promise(res => { const rd = new FileReader(); rd.onloadend = () => res(rd.result); rd.readAsDataURL(b); }); }"
                        b64_data = await page.evaluate(js_fetch, src)
                        if b64_data and "," in b64_data:
                            import base64
                            raw_bytes = base64.b64decode(b64_data.split(",")[1])
                            if len(raw_bytes) > 500 * 1024:
                                with open(save_path, "wb") as f: f.write(raw_bytes)
                                return True
                    elif src and "scontent" in src:
                        logging.info(f"[Worker {worker_id}] Baixando via CDN...")
                        resp = await page.context.request.get(src)
                        if resp.status == 200:
                            with open(save_path, "wb") as f: f.write(await resp.body())
                            return True
                except: pass
            await asyncio.sleep(4)
        return False

    async def _baixar_imagens_async(self, page, worker_id, prefixo="seed"):
        """Captura as imagens geradas pelo /imagine de forma assíncrona."""
        paths = []
        try:
            logging.info(f"[Worker {worker_id}] Aguardando geração de imagens...")
            start_time = time.time()
            candidatas = []
            while time.time() - start_time < 60:
                imgs = await page.locator("img").all()
                for img in imgs:
                    try:
                        box = await img.bounding_box()
                        src = await img.get_attribute("src")
                        if src and box and box['width'] > 200:
                            if "scontent" in src or "blob:" in src:
                                if src not in candidatas: candidatas.append(src)
                    except: pass
                if len(candidatas) >= 2: break
                await asyncio.sleep(3)
            
            for i, src in enumerate(candidatas[-4:]):
                path = os.path.join(self.base_dir, "temp_clips", f"{prefixo}_w{worker_id}_{i}.png")
                try:
                    resp = await page.context.request.get(src)
                    if resp.status == 200:
                        with open(path, "wb") as f: f.write(await resp.body())
                        paths.append(path)
                except: pass
            return paths
        except Exception as e:
            logging.error(f"[Worker {worker_id}] Erro imagens: {e}")
            return []

    def _selecionar_melhor_frame(self, paths):
        """Escolhe a melhor imagem semente."""
        scores = []
        if not paths: return None
        for p in paths:
            try:
                img_array = np.fromfile(p, np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                score = cv2.Laplacian(gray, cv2.CV_64F).var() * gray.std()
                scores.append(score)
            except: scores.append(0)
        return paths[scores.index(max(scores))] if scores else None

    def _extract_frame(self, video_path, out_path):
        """Extração de frame com OpenCV."""
        try:
            cap = cv2.VideoCapture(os.path.abspath(video_path))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total - 2))
            ret, frame = cap.read()
            cap.release()
            if ret:
                _, buf = cv2.imencode(".png", frame)
                with open(out_path, "wb") as f: f.write(buf)
                return True
        except: pass
        return False

    async def processar_lote_aba(self, browser_ctx, worker_id, cenas, worker_dir):
        """Worker V119: Foco total na persistência dos 20s."""
        if not os.path.exists(worker_dir): os.makedirs(worker_dir, exist_ok=True)
        page = await browser_ctx.new_page()
        await page.goto(self.meta_ai_url)
        await asyncio.sleep(10)
        
        current_ref = ""
        videos_lote = []

        for i, prompt_cena in enumerate(cenas):
            print(f"\n[Worker {worker_id}] 🎬 Iniciando Bloco {i+1}/{len(cenas)}...")
            
            sucesso_bloco = False
            for tentativa in range(3):
                # 1. PREPARAR SEMENTE OU FRAME
                if not current_ref:
                    async with self.clipboard_lock:
                        input_field = await self._get_input(page)
                        if input_field:
                            print(f"[Worker {worker_id}] Gerando semente inicial (Crie uma imagem)...")
                            pyperclip.copy(f"Crie uma imagem do prompt: {prompt_cena}, 8k cinematic")
                            await page.keyboard.press("Control+V")
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(5)
                    
                    imgs = await self._baixar_imagens_async(page, worker_id)
                    current_ref = self._selecionar_melhor_frame(imgs)
                    if not current_ref:
                        print(f"[Worker {worker_id}] Erro na semente (T{tentativa+1}). Resetando chat...")
                        await page.reload(); await asyncio.sleep(10); continue
                
                # 2. PRODUÇÃO DO VÍDEO
                async with self.clipboard_lock:
                    abs_p = os.path.abspath(current_ref)
                    cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('{abs_p}'))"
                    subprocess.run(["powershell", "-command", cmd], shell=True)
                    
                    input_field = await self._get_input(page)
                    if input_field:
                        # Limpa e Cola Frame
                        await page.keyboard.press("Control+A"); await page.keyboard.press("Delete")
                        await page.keyboard.press("Control+V")
                        await asyncio.sleep(8) # Aguarda reconhecimento do upload
                        
                        # Cola Prompt
                        pyperclip.copy(f"Animate this: {prompt_cena}. Continuous evolution, 8k.")
                        await page.keyboard.press("Control+V")
                        await asyncio.sleep(1)
                        
                        vids_antes = await page.locator("video").count()
                        
                        # Loop de Envio (Enter Garantido)
                        for _ in range(3):
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(2)
                            txt = await input_field.inner_text()
                            if len(txt.strip()) < 2: break
                            try:
                                btn = page.locator("div[aria-label*='Send'], button[type='submit']").first
                                if await btn.is_visible(): await btn.click(force=True)
                            except: pass

                # 3. DOWNLOAD E TRANSIÇÃO
                fname = f"w{worker_id}_clip_{i}.mp4"
                fpath = os.path.join(worker_dir, fname)
                
                if await self._download_video_async(page, fpath, vids_antes, worker_id):
                    videos_lote.append(fpath)
                    frame_path = os.path.join(worker_dir, f"frame_{i}.png")
                    if self._extract_frame(fpath, frame_path):
                        current_ref = frame_path
                        print(f"[Worker {worker_id}] ✅ Bloco {i+1} concluído com sucesso.")
                        sucesso_bloco = True
                        break
                else:
                    print(f"[Worker {worker_id}] ⚠️ Falha no download (T{tentativa+1}). Reloading...")
                    await page.reload()
                    await asyncio.sleep(10)
                    
                    # V192: Async Recovery Check
                    vids_now = await page.locator("video").count()
                    if vids_now > vids_antes:
                         print(f"[Worker {worker_id}] Vídeo encontrado após reload! Recuperando...")
                         if await self._download_video_async(page, fpath, vids_antes, worker_id):
                             videos_lote.append(fpath)
                             frame_path = os.path.join(worker_dir, f"frame_{i}.png")
                             if self._extract_frame(fpath, frame_path):
                                 current_ref = frame_path
                                 sucesso_bloco = True
                                 break

            if not sucesso_bloco:
                print(f"[Worker {worker_id}] ❌ Falhou definitivamente no bloco {i+1}.")
                break 

        print(f"[Worker {worker_id}] Finalizado. Total: {len(videos_lote)} clips.")
        await page.close()
        return videos_lote