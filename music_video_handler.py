import os
import json
import threading
import yt_dlp
import time
import logging
from openai import OpenAI
from moviepy.editor import AudioFileClip
from video_engine import JarvisVideoMaker

# Configurações
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # D:\...\automação_video ou ...\sistema
AUDIO_DOWNLOAD_DIR = os.path.join(BASE_DIR, "audios", "temp_downloads")

# Lógica robusta para encontrar a pasta do WhatsApp
# No projeto atual, jarvis-mcp-whatsapp está na raiz.
ROOT_MOBILE = BASE_DIR 

VIDEO_PUSH_FILE = os.path.join(ROOT_MOBILE, "jarvis-mcp-whatsapp", "video_push.json")
# Fallback: cria pasta se não existir (para testes isolados)
if not os.path.exists(os.path.dirname(VIDEO_PUSH_FILE)):
    try: os.makedirs(os.path.dirname(VIDEO_PUSH_FILE))
    except: pass

# Configuração API Jarvis
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:11434/v1")
API_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIJ9KfyhZeNo5E84kORaqKYu7gxopcvqT2hRabwJU/sXF"
MODELO_ATIVO = "gpt-oss:120b-cloud"

if not os.path.exists(AUDIO_DOWNLOAD_DIR): os.makedirs(AUDIO_DOWNLOAD_DIR)

def buscar_e_baixar_audio(query):
    """
    Baixa o áudio do Youtube ou usa arquivo local se existir.
    """
    # 0. Verificar se é arquivo local
    if os.path.exists(query):
        logging.info(f"[Audio] Usando arquivo local detectado: {query}")
        return query, os.path.basename(query)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(AUDIO_DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'quiet': False, 
        'noplaylist': True
    }

    try:
        # Se não for URL nem arquivo, faz busca
        if not "http" in query:
            query = f"ytsearch1:{query}"
        
        logging.info(f"[Youtube] Iniciando busca e download: {query}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            
            video_id = info['id']
            # Busca o arquivo gerado
            for f in os.listdir(AUDIO_DOWNLOAD_DIR):
                if video_id in f and f.endswith(".mp3"):
                    path = os.path.join(AUDIO_DOWNLOAD_DIR, f)
                    logging.info(f"[Youtube] Download concluído: {path} ({os.path.getsize(path)} bytes)")
                    return path, info.get('title', 'Musica')
            
    except Exception as e:
        logging.error(f"[Youtube DL Erro] {e}")
        return None, None
    return None, None

def _sanitizar_prompt(prompt):
    """
    Remove ou substitui termos proibidos para evitar bloqueio do Meta AI.
    """
    proibidos = [
        "blood", "gore", "kill", "dead", "suicide", "naked", "nude", "breast", "sex", 
        "weapon", "gun", "pistol", "rifle", "knife", "drug", "cocaine", "heroin", 
        "hitler", "nazi", "child abuse", "rape", "torture", "marvel", "dc comics", "disney"
    ]
    prompt_lower = prompt.lower()
    for p in proibidos:
        if p in prompt_lower:
            logging.warning(f"[Sanitizer] Termo proibido detectado: '{p}'. Substituindo cena.")
            return "Abstract artistic visual representing intense emotion, cinematic lighting, 4k, safe content"
    return prompt

def analisar_letra_musica(audio_path):
    """
    Transcreve o áudio para obter a letra e o timing (Sincronia).
    Converte MP3 -> WAV se necessário.
    """
    logging.info(f"[Ouvido Absoluto] Analisando letra e ritmo de: {os.path.basename(audio_path)}")
    wav_path = audio_path
    temp_wav = False
    
    try:
        # Importa o Scanner Offline (Vosk) do sistema
        try:
            from sistema.audio_scanner import scanner as audio_scanner_offline
        except ImportError:
            # Fallback se executado fora do contexto
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__)))
            from sistema.audio_scanner import scanner as audio_scanner_offline

        # Importa Pydub aqui para não travar se faltar ffmpeg no inicio
        from pydub import AudioSegment
        
        # Se não for wav, converte
        if not audio_path.lower().endswith(".wav"):
            logging.info("   -> Convertendo áudio para WAV (requisito do ouvido)...")
            sound = AudioSegment.from_file(audio_path)
            # Corta para 60s max para agilizar
            if len(sound) > 60000: sound = sound[:60000]
            
            wav_path = audio_path + ".temp.wav"
            sound.export(wav_path, format="wav")
            temp_wav = True
        
        logging.info("   -> Escutando (Offline Vosk)...")
        texto = audio_scanner_offline.transcrever_audio(wav_path)
        
        if "ERRO" not in texto and len(texto) > 5:
            logging.info(f"[Ouvido] Letra detectada: {texto[:100]}...")
            return texto
        else:
            logging.warning("[Ouvido] Áudio ininteligível ou instrumental (Vosk).")
            return "(Instrumental)"
                    
    except Exception as e:
        logging.error(f"[Erro Transcrição] {e}")
        return None
    finally:
        if temp_wav and os.path.exists(wav_path):
            try: os.remove(wav_path)
            except: pass

def gerar_roteiro_inteligente(titulo_musica, duracao_segundos, letra_detectada=None):
    """
    Usa a LLM para criar um storyboard detalhado, cinematográfico e com NEXO TOTAL (Creative Engine V1).
    """
    if duracao_segundos > 180: duracao_segundos = 180
    num_cenas = int(duracao_segundos / 5)
    if num_cenas < 1: num_cenas = 1
    
    logging.info(f"[Creative Engine] Iniciando Direção de Arte para: {titulo_musica}")
    
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # QUALITY BOOSTERS - Injeção de Alta Qualidade
    quality_tags = "8k resolution, photorealistic, cinematic lighting, Unreal Engine 5 render, extremely detailed, depth of field, ray tracing"
    
    system_prompt = """
    VOCE E UM DIRETOR DE VIDEOCLIPES PREMIADO (CANNES/MTV).
    Sua missao e traduzir AUDIO e EMOCAO em VISUAIS IMPACTANTES.

    ### SUA METODOLOGIA (THE VISION):
    1.  **ANALISE A VIBE:** Se a letra for triste, use chuva, neon azul, slow motion. Se for agitada, use cortes rapidos, fogo, luz estroboscopica.
    2.  **PALETA DE CORES:** Defina uma paleta de cores consistente para o video (ex: "Teal & Orange", "Cyberpunk Neon", "B&W with Red").
    3.  **ILUMINACAO:** A luz e tudo. Use termos como: "Volumetric lighting", "God rays", "Neon rim light", "Cinematic softbox".
    4.  **MOVIMENTO DE CAMERA:** Proibido camera estatica. Use: "Drone shot", "Dolly zoom", "Tracking shot", "Dutch angle".

    ### ESTRUTURA JSON OBRIGATORIA:
    {
      "visual_style": "Estilo artistico dominante (ex: Dark Fantasy, Cyberpunk City, Ethereal Nature)",
      "color_palette": "Esquema de cores (ex: Cold Blues and Greys)",
      "main_subject": "O sujeito principal (ex: A lonely astronaut)",
      "scenes": [
        {
          "id": 1,
          "action": "Descreva a cena visualmente. ONDE estao? O que o sujeito faz?",
          "camera": "Movimento de camera especifico (ex: Slow Dolly-In)",
          "lighting": "Iluminacao da cena (ex: Dim neon lights)",
          "mood": "Emocao da cena (ex: Melancholic)"
        }
      ]
    }
    """

    contexto_letra = f"LETRA/TRANSCRICAO: '{letra_detectada}'" if letra_detectada else "VIBE: Baseie-se no título e ritmo sugerido."
    user_prompt = f"Crie um roteiro visual de {num_cenas} cenas para a música: {titulo_musica}. {contexto_letra}. SEJA CRIATIVO E VISUAL. Retorne APENAS o JSON."
    
    # Tentativas de reconexão (Retry Logic)
    for tentativa in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODELO_ATIVO,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8 # Aumentado para mais criatividade
            )
            
            content = resp.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            
            # Tratamento de erro comum onde o modelo poe texto antes do json
            if "{" in content: content = content[content.find("{"):content.rfind("}")+1]

            data = json.loads(content)
            
            scenes = data.get("scenes", [])
            visual_style = data.get("visual_style", "Cinematic")
            color_palette = data.get("color_palette", "Vibrant")
            main_subject = data.get("main_subject", "")
            
            prompts = []
            for s in scenes:
                action = s.get("action", "")
                camera = s.get("camera", "")
                lighting = s.get("lighting", "")
                
                # O PROMPT FINAL É A MAGIA DA ENGENHARIA
                # Estrutura: [Style] + [Action] + [Camera] + [Lighting] + [Quality Tags]
                full_prompt = (
                    f"{visual_style} style. {action}. "
                    f"Camera: {camera}. Lighting: {lighting}, {color_palette}. "
                    f"{quality_tags}."
                )
                prompts.append(full_prompt)

            if prompts:
                # Garante que temos prompts suficientes
                while len(prompts) < num_cenas:
                    prompts.append(prompts[-1] + " (Continued visual evolution)")
                
                return [_sanitizar_prompt(str(s)) for s in prompts[:num_cenas]]
                
        except Exception as e:
            logging.warning(f"[Creative Engine] Tentativa {tentativa+1}/3 falhou: {e}")
            time.sleep(2)

    logging.error("[Creative Engine] FALHA NO CÉREBRO CRIATIVO. Usando fallback de emergência.")
    return [f"Cinematic masterpiece of {titulo_musica}, scene {i+1}, {quality_tags}" for i in range(num_cenas)]

def _thread_processar_video(user_id, query_musica, tema_visual):
    try:
        logging.info(f"[Jarvis Integration] Iniciando processo para {user_id}: {query_musica}")
        
        # 1. Baixar Música
        audio_path, titulo = buscar_e_baixar_audio(query_musica)
        if not audio_path:
            _notificar_push(user_id, None, "❌ Não consegui baixar a música.")
            return
            
        # 1.5 Analisar
        aclip = AudioFileClip(audio_path)
        duracao = aclip.duration
        aclip.close()
        letra = analisar_letra_musica(audio_path)

        # 2. Gerar Roteiro
        _notificar_push(user_id, None, f"🧠 Jarvis Diretor está escrevendo o roteiro para *{titulo}*...")
        storyboard = gerar_roteiro_inteligente(f"{titulo} ({tema_visual})", duracao, letra)

        # 3. Gerar Vídeo (Pipeline Sequencial Single-Tab V90)
        _notificar_push(user_id, None, f"🎬 Iniciando renderização contínua (V90 Single-Tab)...")
        maker = JarvisVideoMaker(base_dir=BASE_DIR)
        
        # Chama o pipeline completo (Loop interno na mesma aba)
        todos_videos, last_frame = maker.pipeline_video_sequencial(
            audio_path=audio_path,
            roteiro=storyboard,
            output_folder=maker.output_dir,
            initial_image_path=None # Começa do zero, ou pode passar imagem se tiver
        )
        
        if not todos_videos:
             logging.error(f"[Maestro] Pipeline falhou. Nenhum video gerado.")
        else:
             logging.info(f"[Maestro] Pipeline concluiu com {len(todos_videos)} clips.")
        
        # 4. Montagem Final (Concatenação)
        if todos_videos:
            _notificar_push(user_id, None, "🎬 Montando videoclipe final...")
            
            output_filename = f"music_video_{int(time.time())}.mp4"
            output_path = os.path.join(maker.output_dir, output_filename)
            
            # Concatena vídeo
            import subprocess
            list_path = os.path.join(maker.temp_dir, "concat_list.txt")
            with open(list_path, "w", encoding="utf-8") as f:
                for v in todos_videos:
                    f.write(f"file '{os.path.abspath(v).replace(os.sep, '/')}'\n")
            
            temp_v = os.path.join(maker.temp_dir, "temp_concat.mp4")
            subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_path, '-c', 'copy', temp_v], check=True)
            
            # Adiciona Áudio
            cmd_final = ['ffmpeg', '-y', '-i', temp_v, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-shortest', output_path]
            subprocess.run(cmd_final, check=True)
            
            # Salva roteiro
            try:
                with open(output_path.replace(".mp4", "_roteiro.txt"), "w", encoding="utf-8") as f:
                    f.write(f"ROTEIRO: {titulo}\n\n")
                    for i, c in enumerate(storyboard): f.write(f"{i+1}: {c}\n")
            except: pass

            legenda = f"🎬 *Videoclipe Oficial: {titulo}*\nBy Jarvis V70 (20s Blocks)"
            _notificar_push(user_id, output_path, legenda)
        else:
            _notificar_push(user_id, None, "❌ Falha na renderização: Nenhum bloco gerado.")

    except Exception as e:
        logging.error(f"[Integration Error] {e}")
        _notificar_push(user_id, None, f"❌ Erro: {str(e)}")

def _notificar_push(user_id, file_path, caption):
    """Escreve no JSON para o Node.js ler"""
    try:
        data = {
            "target": user_id,
            "path": file_path if file_path else "",
            "caption": caption
        }
        # Escreve atomicamente (com .tmp e rename) para evitar leitura parcial?
        # Para simplificar, write direto, o Node tem try/catch.
        with open(VIDEO_PUSH_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"[Push Error] {e}")

def iniciar_criacao_videoclipe(user_id, comando_texto):
    """
    Função de entrada chamada pelo app.py.
    Ex: "criar clipe da musica numb do linkin park tema cyberpunk"
    """
    # Parser simples
    comando_limpo = comando_texto.lower().replace("criar clipe", "").replace("fazer videoclipe", "").replace("da musica", "").replace("da música", "").strip()
    
    tema = ""
    musica = comando_limpo
    
    # Tenta separar por palavras chave de tema
    separadores = [" tema ", " estilo ", " com visual "]
    for sep in separadores:
        if sep in comando_limpo:
            partes = comando_limpo.split(sep)
            musica = partes[0].strip()
            tema = partes[1].strip()
            break
            
    # Se não achou tema, deixa vazio para a thread decidir usar o titulo
    
    # Inicia Thread
    t = threading.Thread(target=_thread_processar_video, args=(user_id, musica, tema))
    t.start()
    
    msg_tema = f" com tema '{tema}'" if tema else " (vou improvisar o visual baseado no som)"
    return f"🚀 Entendido! Vou baixar '{musica}' e criar um clipe{msg_tema}. Isso leva uns minutos!"