import os
import time
import subprocess
import logging
import json
import requests
import cv2
import numpy as np
import pyperclip # V86: Clipboard nativo
from typing import List, Optional
from playwright.sync_api import sync_playwright
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
from PIL import Image, ImageEnhance
from memory_manager import MemoryManager
from subject_lock import SubjectLockManager

class JarvisVideoMaker:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.getcwd()
        self.temp_dir = os.path.join(self.base_dir, "temp_clips")
        self.output_dir = os.path.join(self.base_dir, "videoclipes") 
        self.meta_ai_url = "https://www.meta.ai"
        self.memory_manager = MemoryManager()
        self.subject_lock = None 
        if not os.path.exists(self.temp_dir): os.makedirs(self.temp_dir)
        if not os.path.exists(self.output_dir): os.makedirs(self.output_dir)

    def _calcular_score_qualidade_local(self, image_path):
        try:
            img_array = np.fromfile(image_path, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None: return 0
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            contrast = gray.std()
            return sharpness * contrast
        except: return 0

    def _selecionar_melhor_frame_local(self, image_paths):
        scores = [self._calcular_score_qualidade_local(p) for p in image_paths]
        if not scores: return 0
        return scores.index(max(scores))

    def _baixar_imagens_meta(self, page, prefixo="meta_img"):
        paths = []
        try:
            logging.info("[Download Img] Iniciando Polling de imagens...")
            start_time = time.time()
            candidatas_src = []
            while time.time() - start_time < 60:
                imgs = page.locator("img").all()
                candidatas_src = []
                for img in imgs:
                    try:
                        box = img.bounding_box()
                        if box and box['width'] > 200:
                            src = img.get_attribute("src")
                            if src and ("scontent" in src or "blob:" in src):
                                candidatas_src.append(src)
                    except: pass
                if len(candidatas_src) >= 2: break
                time.sleep(2)
            
            if not candidatas_src:
                logging.warning("[Download Img] Nenhuma imagem encontrada.")
                try: page.screenshot(path=os.path.join(self.base_dir, "debug_seed_fail.png"))
                except: pass
                return []

            for i, src in enumerate(candidatas_src[-4:]):
                try:
                    resp = page.context.request.get(src)
                    if resp.status == 200:
                        path = os.path.join(self.temp_dir, f"{prefixo}_{i}.png")
                        with open(path, "wb") as f: f.write(resp.body())
                        paths.append(path)
                except: pass
            return paths
        except Exception as e:
            logging.error(f"Erro download img: {e}")
            return []

    def _enrich_prompt(self, base_prompt):
        magic = ", 8k resolution, highly detailed, photorealistic, cinematic lighting, unreal engine 5 render"
        return base_prompt + magic if "8k" not in base_prompt.lower() else base_prompt

    def _get_input(self, page):
        """Localiza o campo de input com busca profunda e forcagem de foco (V105)."""
        seletores = [
            "div[role='textbox']", 
            "div[contenteditable='true']", 
            "textarea[placeholder*='Imagine']",
            "textarea[placeholder*='Ask']",
            "p[data-lexical-text='true']",
            "div[data-testid='composer_input']",
            "textarea"
        ]
        
        # 1. Tenta limpar overlays
        try: page.keyboard.press("Escape")
        except: pass

        for sel in seletores:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0 and loc.is_visible(timeout=2000):
                    # Forca foco via Script (Garante que o Paste va para o lugar certo)
                    try:
                        page.evaluate(f"(s) => {{ let el = document.querySelector(s); if(el) {{ el.focus(); el.click(); }} }}", sel)
                    except: pass
                    return loc
            except: pass
            
        logging.warning("[Input] Nenhum seletor especifico visivel. Retornando fallback cego.")
        return None

    def _paste_prompt(self, page, text):
        """Envia texto via Clipboard com tripla validacao de foco (V105)."""
        try:
            pyperclip.copy(text)
            time.sleep(0.5)
            
            tb = self._get_input(page)
            if tb:
                try:
                    tb.click(force=True, timeout=5000)
                    time.sleep(0.2)
                    # Limpa
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Delete")
                except: pass
            
            # Paste Indireto (Garante que funcione mesmo sem o locator perfeito)
            logging.info(f"[Paste] Enviando via Ctrl+V: {text[:40]}...")
            page.keyboard.press("Control+V")
            time.sleep(1.5) 
            return True
        except Exception as e:
            logging.error(f"[Paste Error] {e}")
            return False

    def _reply_to_last_media(self, page, file_path):
        """
        Executa 'Responder' no último item com timeout estendido e detecção de vídeo (V103).
        """
        if not os.path.exists(file_path): return False
        abs_path = os.path.abspath(file_path)
        
        try:
            # 1. Clipboard
            if abs_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('{abs_path}'))"
            else:
                ps_cmd = f"Set-Clipboard -Path '{abs_path}'"
            subprocess.run(["powershell", "-command", ps_cmd], check=True, timeout=15)
            time.sleep(1)

            # 2. Ativa Reply (Hover Lateral)
            try:
                # Tenta localizar o container da ultima mensagem de midia
                last_media = page.locator("video, img[src*='scontent']").last
                if last_media.count() > 0:
                    last_media.scroll_into_view_if_needed()
                    box = last_media.bounding_box()
                    if box:
                        page.mouse.move(box['x'] + 5, box['y'] + 5) # Canto superior esquerdo
                        time.sleep(1)
                    
                    reply_btn = page.locator("div[aria-label*='Responder'], div[aria-label*='Reply'], i[class*='reply']").last
                    if reply_btn.is_visible(timeout=5000):
                        reply_btn.click(force=True)
                        time.sleep(1.5)
            except: pass

            # 3. Paste
            page.keyboard.press("Control+V")
                
            # 4. Handshake Visual Estendido (60s para Videos)
            logging.info("[Reply] 🔒 Aguardando Handshake (Timeout 60s)...")
            selectors = [
                "img[src^='blob:']", 
                "video[src^='blob:']", 
                "div[aria-label*='Remove']", 
                "div[data-testid='media-attachment-preview']",
                "div[role='progressbar']" # Meta AI as vezes mostra barra de progresso no upload
            ]
            try:
                page.wait_for_selector(",".join(selectors), state="visible", timeout=60000)
                time.sleep(5.0) # Estabilização final
                logging.info("[Reply] ✅ Handshake concluído.")
                return True
            except:
                logging.warning("[Reply] Timeout visual. Tentando prosseguir cego...")
                return True 
        except Exception as e:
            logging.error(f"[Reply Error] {e}")
            return False

    def pipeline_video_sequencial(self, audio_path: str, roteiro: List[str], output_folder: str, initial_image_path: Optional[str] = None) -> tuple:
        """
        Pipeline V103: Resilient Reply Chain.
        Implementa tentativas de recuperação para evitar videos curtos.
        """
        import math
        import uuid
        
        duration = 0
        try:
            if audio_path and os.path.exists(audio_path):
                with AudioFileClip(audio_path) as a: duration = a.duration
        except: duration = 30
        
        qtd_clips = math.ceil(duration / 5) if duration > 0 else len(roteiro)
        if qtd_clips < 1: qtd_clips = 1
        print(f"[INFO] Objetivo: {duration}s | {qtd_clips} blocos.")

        while len(roteiro) < qtd_clips:
            roteiro.append(roteiro[-1] if roteiro else "Continue this sequence, 8k")

        paths = [r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe", r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe", os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"]
        brave_path = next((p for p in paths if os.path.exists(p)), None)

        ud = os.path.join(self.base_dir, "brave_profile_jarvis")
        videos_gerados = []
        
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(user_data_dir=ud, executable_path=brave_path, headless=False, viewport={'width':1280,'height':720}, accept_downloads=True, args=["--disable-blink-features=AutomationControlled"])
            page = ctx.pages[0]
            
            # Só reseta se não estiver na URL correta
            if page.url != self.meta_ai_url:
                self._reset_chat(page)

            try:
                current_ref = initial_image_path if initial_image_path and os.path.exists(initial_image_path) else ""
                
                # --- GERAÇÃO DA SEMENTE ---
                if not current_ref:
                    for t_seed in range(3):
                        if t_seed > 0:
                            print(f"[RETRY] Tentativa {t_seed+1} para Semente. Executando F5...", flush=True)
                            self._reset_chat(page)
                            time.sleep(5)

                        print("[PIPELINE] Gerando Semente (Imagem Inicial)...")
                        if self._paste_prompt(page, f"Crie uma imagem do prompt: {self._enrich_prompt(roteiro[0])}"):
                            vids_init = page.locator("video").count()
                            page.keyboard.press("Enter")
                            
                            # Espera as imagens aparecerem (sem fechar a aba)
                            imgs = self._baixar_imagens_meta(page, prefixo="seed_master")
                            if imgs: 
                                current_ref = imgs[self._selecionar_melhor_frame_local(imgs)]
                                print(f"[PIPELINE] Semente capturada: {os.path.basename(current_ref)}")
                                time.sleep(5) # EstabilizaÃ§Ã£o pÃ³s-semente
                                break
                            else:
                                print("[AVISO] Falha ao capturar imagem. Tentando ver se gerou vÃ­deo direto...")
                                # Fallback: Se gerou vÃ­deo em vez de imagem
                                if page.locator("video").count() > vids_init:
                                    print("[PIPELINE] VÃ­deo gerado direto na semente. Capturando frame...")
                                    fname = f"seed_video_{uuid.uuid4().hex[:6]}.mp4"
                                    fpath = os.path.join(output_folder, fname)
                                    if self._download_video_src(page, fpath, index=vids_init):
                                        frame_path = fpath.replace(".mp4", "_seed_frame.png")
                                        if self._extrair_ultimo_frame(fpath, frame_path):
                                            current_ref = frame_path
                                            videos_gerados.append(fpath)
                                            break

                if not current_ref or not os.path.exists(current_ref):
                    raise Exception("ImpossÃ­vel continuar sem uma imagem ou vÃ­deo de semente.")

                # --- LOOP DE GERAÇÃO SEQUENCIAL (DAISY CHAIN) ---
                for i in range(qtd_clips):
                    num_cena = i + 1
                    print(f"\n[CENA {num_cena}/{qtd_clips}] Processando...")
                    
                    # V193: Referência de contagem base ANTES das tentativas
                    vids_antes = page.locator("video").count()
                    
                    sucesso_clipe = False
                    for tentativa in range(3):
                        # Só limpa o chat se for a segunda tentativa em diante
                        if tentativa > 0:
                            print(f"[RETRY] Tentativa {tentativa+1}. Executando F5 e aguardando histórico...", flush=True)
                            self._reset_chat(page)
                            
                            # V193: Polling de Recuperação Robusto (20s)
                            print("[RECOVERY] Escaneando por vídeo gerado...", flush=True)
                            video_found = False
                            for _ in range(10): # 10 x 2s = 20s
                                current_count = page.locator("video").count()
                                if current_count > vids_antes:
                                    video_found = True
                                    break
                                time.sleep(2)
                            
                            if video_found:
                                print("[RECOVERY] Vídeo detectado após F5! Capturando sem re-enviar prompt...")
                                fname = f"clip_{i}_recovery_{uuid.uuid4().hex[:6]}.mp4"
                                fpath = os.path.join(output_folder, fname)
                                
                                if self._download_video_src(page, fpath, index=vids_antes):
                                    videos_gerados.append(fpath)
                                    frame_path = fpath.replace(".mp4", "_last_frame.png")
                                    if self._extrair_ultimo_frame(fpath, frame_path):
                                        current_ref = frame_path
                                        print(f"[RECOVERY] ✅ Sucesso! Vídeo recuperado e validado.")
                                        sucesso_clipe = True
                                        break
                            else:
                                print("[RECOVERY] Vídeo não encontrado no histórico. Reiniciando envio...")

                        subprocess.run(["powershell", "-command", "Set-Clipboard -Value $null"], check=True, shell=True)
                        
                        abs_ref = os.path.abspath(current_ref)
                        if abs_ref.lower().endswith(('.png', '.jpg', '.jpeg')):
                            ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('{abs_ref}'))"
                        else:
                            ps_cmd = f"Set-Clipboard -Path '{abs_ref}'"
                        
                        subprocess.run(["powershell", "-command", ps_cmd], check=True, timeout=15, shell=True)
                        time.sleep(1)

                        input_field = self._get_input(page)
                        if input_field:
                            input_field.click(force=True)
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Delete")
                            time.sleep(0.5)
                            page.keyboard.press("Control+V")
                            
                            try:
                                page.wait_for_selector("img[src^='blob:'], div[aria-label*='Remove'], div[role='progressbar']", timeout=15000)
                                time.sleep(3) 
                            except: pass

                            acao = roteiro[i] if i < len(roteiro) else roteiro[-1]
                            p_anim = f"Animate this: {acao}. Continuous movement, cinematic."
                            pyperclip.copy(p_anim)
                            time.sleep(0.5)
                            
                            input_field.click(force=True)
                            page.keyboard.press("Control+V")
                            time.sleep(1)
                            
                            # vids_antes já definido no início do loop da cena
                            print(f"[PIPELINE] 🚀 Enviando Cena {num_cena} (Ref: {vids_antes} vids)...")
                            
                            # Ciclo de Enter Garantido
                            for _ in range(2):
                                page.keyboard.press("Enter")
                                time.sleep(1)
                                if len(input_field.inner_text().strip()) < 2: break
                                try:
                                    page.locator("div[aria-label*='Send'], button[type='submit']").first.click(timeout=1000)
                                except: pass

                            try:
                                # V193: Timeout aumentado para 30s para evitar ansiedade
                                page.wait_for_function("v => document.querySelectorAll('video').length > v", arg=vids_antes, timeout=30000)
                                time.sleep(2) # Delay mínimo para estabilização da tag
                                
                                fname = f"clip_{i}_{uuid.uuid4().hex[:6]}.mp4"
                                fpath = os.path.join(output_folder, fname)
                                
                                if self._download_video_src(page, fpath, index=vids_antes):
                                    videos_gerados.append(fpath)
                                    frame_path = fpath.replace(".mp4", "_last_frame.png")
                                    
                                    if self._extrair_ultimo_frame(fpath, frame_path):
                                        current_ref = frame_path
                                        print(f"[UPDATE] ✅ Cena {num_cena} concluída.")
                                        sucesso_clipe = True
                                        break
                            except Exception as e_gen:
                                print(f"[AVISO] Falha na renderização da cena {num_cena}: {e_gen}")
                        
                    if not sucesso_clipe:
                        print(f"[ERRO] Falha crítica na cena {num_cena}. Encerrando pipeline.")
                        break
                        
                print(f"[FIM] Geracao concluida com {len(videos_gerados)} clipes.")
                time.sleep(10) # Mantém a aba aberta por 10s para conferência final
            except Exception as e: 
                logging.error(f"[Pipeline Error] {e}")
                time.sleep(30) # Se der erro, mantém a aba aberta para debug visual
            finally: 
                ctx.close()
        return videos_gerados, current_ref

    def _download_video_src(self, page, save_path, index=None):
        """
        Localiza e baixa o video gerado (V112 - Indexed Focus).
        Se index for passado, foca no vídeo após esse índice para garantir que seja novo.
        """
        try:
            logging.info(f"[Download] Buscando o vÃ­deo (Index: {index})...")
            start_time = time.time()
            
            # V188: Timeout ajustado para 25s com polling contÃ­nuo de detecÃ§Ã£o
            while time.time() - start_time < 25:
                vids = page.locator("video").all()
                if not vids:
                    time.sleep(3); continue
                
                # Se temos um índice anterior, pegamos o vídeo seguinte a ele.
                # Caso contrário, pegamos o último.
                target_vid = vids[index] if (index is not None and len(vids) > index) else vids[-1]
                
                try:
                    box = target_vid.bounding_box()
                    src = target_vid.get_attribute("src")
                    
                    if src and box and box['width'] > 300:
                        logging.info(f"[Download] Alvo detectado: {src[:50]}...")
                        
                        # ESTRATEGIA: BLOB FETCH VIA JS
                        if src.startswith("blob:"):
                            js_fetch_blob = """
                            async (url) => {
                                const response = await fetch(url);
                                const blob = await response.blob();
                                return new Promise((resolve) => {
                                    const reader = new FileReader();
                                    reader.onloadend = () => resolve(reader.result);
                                    reader.readAsDataURL(blob);
                                });
                            }
                            """
                            b64_data = page.evaluate(js_fetch_blob, src)
                            if b64_data and "," in b64_data:
                                import base64
                                raw_bytes = base64.b64decode(b64_data.split(",")[1])
                                if len(raw_bytes) > 500 * 1024:
                                    with open(save_path, "wb") as f: f.write(raw_bytes)
                                    logging.info(f"[Download] ✅ Vídeo baixado!")
                                    return True
                        else:
                            # ESTRATEGIA: CDN
                            resp = page.context.request.get(src)
                            if resp.status == 200 and len(resp.body()) > 500 * 1024:
                                with open(save_path, "wb") as f: f.write(resp.body())
                                return True
                except: pass
                
                # Dynamic Fast Polling V194
                time.sleep(0.5)
            return False
        except Exception as e:
            logging.error(f"[Download Error] {e}")
            return False

    def _reset_chat(self, page):
        try:
            # V186: LÃ³gica HÃ­brida. Se jÃ¡ estivermos no site, usamos F5 (Reload). 
            # Se estivermos fora (ex: erro de navegaÃ§Ã£o), usamos Goto.
            if self.meta_ai_url in page.url:
                print("[SISTEMA] 🔄 Executando F5 (Reload) para recuperaÃ§Ã£o tÃ¡tica...", flush=True)
                page.reload()
            else:
                print(f"[SISTEMA] 🌐 Redirecionando para {self.meta_ai_url}...", flush=True)
                page.goto(self.meta_ai_url)
                
            time.sleep(10)
            page.keyboard.press("Escape")
        except Exception as e:
            logging.error(f"[Reset Error] {e}")
            try: page.goto(self.meta_ai_url)
            except: pass

    def _extrair_ultimo_frame(self, video_path, output_image_path):
        """Extração cirúrgica do último frame usando OpenCV com suporte a caminhos Unicode (V91)."""
        try:
            # Para caminhos com acentos no Windows, cv2.VideoCapture pode falhar.
            # Usamos o caminho absoluto e garantimos que o arquivo existe.
            abs_video = os.path.abspath(video_path)
            cap = cv2.VideoCapture(abs_video)
            
            if not cap.isOpened():
                logging.error(f"[OpenCV] Não foi possível abrir o vídeo: {abs_video}")
                return False

            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            # Pega o penúltimo ou último frame estável
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total - 2))
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Gravação binária segura para caminhos Windows (Unicode-Safe)
                is_success, buffer = cv2.imencode(".png", frame)
                if is_success:
                    with open(output_image_path, "wb") as f:
                        f.write(buffer)
                    return True
            return False
        except Exception as e:
            logging.error(f"[OpenCV Error] {e}")
            return False

    def _upload_frame_meta(self, page, image_path):
        """Upload de imagem no Meta AI via file input do Playwright (V201 - mais robusto que clipboard)."""
        abs_path = os.path.abspath(image_path)
        if not os.path.exists(abs_path):
            logging.error(f"[Upload] Arquivo não encontrado: {abs_path}")
            return False

        try:
            # Estratégia 1: File input direto (invisível no DOM)
            file_input = page.locator('input[type="file"]')
            if file_input.count() > 0:
                file_input.first.set_input_files(abs_path)
                logging.info("[Upload] Via input[type=file] direto.")
            else:
                # Estratégia 2: Click no botão de attach + file chooser
                attach_selectors = [
                    'button[aria-label*="Attach"]',
                    'button[aria-label*="attach"]',
                    'button[aria-label*="Upload"]',
                    'button[aria-label*="upload"]',
                    'div[aria-label*="Anexar"]',
                    'div[aria-label*="anexar"]',
                    '[data-testid="media-upload"]',
                ]
                clicked = False
                for sel in attach_selectors:
                    try:
                        btn = page.locator(sel).first
                        if btn.count() > 0 and btn.is_visible(timeout=2000):
                            with page.expect_file_chooser() as fc_info:
                                btn.click(force=True)
                            fc_info.value.set_files(abs_path)
                            clicked = True
                            logging.info(f"[Upload] Via file chooser ({sel}).")
                            break
                    except:
                        continue

                if not clicked:
                    # Estratégia 3: Fallback clipboard (Windows PowerShell)
                    logging.info("[Upload] Fallback: clipboard PowerShell.")
                    subprocess.run(["powershell", "-command", "Set-Clipboard -Value $null"], check=True, shell=True)
                    if abs_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                        ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('{abs_path}'))"
                    else:
                        ps_cmd = f"Set-Clipboard -Path '{abs_path}'"
                    subprocess.run(["powershell", "-command", ps_cmd], check=True, timeout=15, shell=True)
                    time.sleep(1)

                    input_field = self._get_input(page)
                    if input_field:
                        input_field.click(force=True)
                        page.keyboard.press("Control+V")

            # Espera preview da imagem aparecer
            try:
                page.wait_for_selector(
                    "img[src^='blob:'], div[aria-label*='Remove'], div[data-testid='media-attachment-preview'], div[role='progressbar']",
                    timeout=15000
                )
                time.sleep(3)
                logging.info("[Upload] ✅ Preview detectado.")
                return True
            except:
                logging.warning("[Upload] Timeout no preview, prosseguindo...")
                time.sleep(2)
                return True

        except Exception as e:
            logging.error(f"[Upload Error] {e}")
            return False

    def gerar_video_comando(self, prompt, num_clips=3):
        """
        V201: Gera vídeo simples via comando /video.
        - prompt: texto do usuário (ex: "frango bebendo suco")
        - num_clips: quantidade de clips de 5s (default 3 = 15s)
        Retorna: path do vídeo final concatenado ou None
        """
        import uuid

        paths_brave = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
        ]
        brave_path = next((p for p in paths_brave if os.path.exists(p)), None)
        ud = os.path.join(self.base_dir, "brave_profile_jarvis")

        videos_gerados = []
        current_frame = None

        print(f"[/VIDEO] Iniciando geração: {num_clips} clips | Prompt: {prompt[:50]}...", flush=True)

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=ud,
                executable_path=brave_path,
                headless=False,
                viewport={'width': 1280, 'height': 720},
                accept_downloads=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = ctx.pages[0]

            try:
                # Navega pro Meta AI
                if self.meta_ai_url not in page.url:
                    self._reset_chat(page)
                else:
                    page.reload()
                    time.sleep(10)
                    page.keyboard.press("Escape")

                for i in range(num_clips):
                    num_cena = i + 1
                    print(f"\n[/VIDEO] === CLIP {num_cena}/{num_clips} ===", flush=True)

                    vids_antes = page.locator("video").count()
                    sucesso = False

                    for tentativa in range(3):
                        if tentativa > 0:
                            print(f"[/VIDEO] Retry {tentativa + 1} para clip {num_cena}...", flush=True)
                            self._reset_chat(page)

                            # Polling de recuperação (20s)
                            video_found = False
                            for _ in range(10):
                                if page.locator("video").count() > vids_antes:
                                    video_found = True
                                    break
                                time.sleep(2)

                            if video_found:
                                print("[/VIDEO] Vídeo recuperado após F5!", flush=True)
                                fname = f"cmd_clip_{i}_recovery_{uuid.uuid4().hex[:6]}.mp4"
                                fpath = os.path.join(self.temp_dir, fname)
                                if self._download_video_src(page, fpath, index=vids_antes):
                                    videos_gerados.append(fpath)
                                    frame_path = fpath.replace(".mp4", "_frame.png")
                                    if self._extrair_ultimo_frame(fpath, frame_path):
                                        current_frame = frame_path
                                    sucesso = True
                                    break
                                continue

                        if i == 0:
                            # CLIP 1: Só prompt, sem frame anterior
                            prompt_enriquecido = self._enrich_prompt(prompt)
                            texto_envio = f"Generate a 5 second video of: {prompt_enriquecido}"
                            if self._paste_prompt(page, texto_envio):
                                page.keyboard.press("Enter")
                        else:
                            # CLIPS 2+: Upload do frame anterior + prompt de continuação
                            if current_frame and os.path.exists(current_frame):
                                print(f"[/VIDEO] Uploading frame: {os.path.basename(current_frame)}", flush=True)
                                self._upload_frame_meta(page, current_frame)
                                time.sleep(1)

                            texto_continuacao = f"Continue this animation from the attached image: {prompt}. Maintain visual continuity, same subject, same style. Cinematic movement."
                            if self._paste_prompt(page, texto_continuacao):
                                # Duplo Enter para garantir envio
                                for _ in range(2):
                                    page.keyboard.press("Enter")
                                    time.sleep(1)

                        # Espera o vídeo ser gerado
                        try:
                            print(f"[/VIDEO] Aguardando renderização (clip {num_cena})...", flush=True)
                            page.wait_for_function(
                                "v => document.querySelectorAll('video').length > v",
                                arg=vids_antes,
                                timeout=60000
                            )
                            time.sleep(3)  # Estabilização

                            # Download do vídeo
                            fname = f"cmd_clip_{i}_{uuid.uuid4().hex[:6]}.mp4"
                            fpath = os.path.join(self.temp_dir, fname)

                            if self._download_video_src(page, fpath, index=vids_antes):
                                videos_gerados.append(fpath)
                                print(f"[/VIDEO] ✅ Clip {num_cena} baixado: {fname}", flush=True)

                                # Extrai último frame pra daisy chain
                                frame_path = fpath.replace(".mp4", "_frame.png")
                                if self._extrair_ultimo_frame(fpath, frame_path):
                                    current_frame = frame_path
                                    print(f"[/VIDEO] Frame extraído: {os.path.basename(frame_path)}", flush=True)

                                sucesso = True
                                break
                        except Exception as e:
                            print(f"[/VIDEO] Falha no clip {num_cena}: {e}", flush=True)

                    if not sucesso:
                        print(f"[/VIDEO] ❌ Falha crítica no clip {num_cena}. Parando.", flush=True)
                        break

                print(f"\n[/VIDEO] Geração finalizada: {len(videos_gerados)}/{num_clips} clips.", flush=True)
                time.sleep(5)

            except Exception as e:
                logging.error(f"[/VIDEO Pipeline Error] {e}")
                time.sleep(10)
            finally:
                ctx.close()

        # --- CONCATENAÇÃO COM FFMPEG ---
        if len(videos_gerados) < 1:
            print("[/VIDEO] Nenhum vídeo gerado. Abortando.", flush=True)
            return None

        if len(videos_gerados) == 1:
            return videos_gerados[0]

        try:
            list_path = os.path.join(self.temp_dir, "cmd_concat_list.txt")
            with open(list_path, "w", encoding="utf-8") as f:
                for v in videos_gerados:
                    f.write(f"file '{os.path.abspath(v).replace(os.sep, '/')}'\n")

            output_path = os.path.join(self.output_dir, f"cmd_video_{int(time.time())}.mp4")
            subprocess.run(
                ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_path, '-c', 'copy', output_path],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print(f"[/VIDEO] ✅ Vídeo final: {output_path}", flush=True)
            return output_path
        except Exception as e:
            logging.error(f"[/VIDEO Concat Error] {e}")
            # Se concat falhar, retorna pelo menos o primeiro clip
            return videos_gerados[0] if videos_gerados else None

    def generate_video_from_prompt(self, prompt, filename_prefix="clip"): pass
    def gerar_video_musical(self, audio_path, tema_base, context_lyrics=None, storyboard=None, status_callback=None, base_image_path=None): pass
