import os
import json
import threading
import yt_dlp
import time
import logging
import re
import requests
import base64
from openai import OpenAI
from moviepy.editor import AudioFileClip
from video_engine import JarvisVideoMaker
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Configurações
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DOWNLOAD_DIR = os.path.join(BASE_DIR, "audios", "temp_downloads")
TEMP_UPLOADS_DIR = os.path.join(BASE_DIR, "temp_clips", "user_uploads")


# Caminho unificado para o arquivo de notificação de vídeo
VIDEO_PUSH_FILE = os.path.join(BASE_DIR, "jarvis-mcp-whatsapp", "video_push.json")

# Configuração API Jarvis
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:11434/v1")
API_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIJ9KfyhZeNo5E84kORaqKYu7gxopcvqT2hRabwJU/sXF"
MODELO_ATIVO = "gpt-oss:120b-cloud"

for d in [AUDIO_DOWNLOAD_DIR, TEMP_UPLOADS_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# --- UTILITÁRIOS ---

def _notificar_push(user_id, file_path, caption):
    try:
        data = {
            "target": user_id,
            "path": file_path if file_path else "",
            "caption": caption
        }
        with open(VIDEO_PUSH_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"[Push Error] {e}")

def extrair_url(texto):
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    match = url_pattern.search(texto)
    return match.group(0) if match else None

# --- ETAPA 1: O RESET & EXTRAÇÃO UNIVERSAL (The Reader) ---
def extrair_texto_url_universal(url):
    """Lê o conteúdo textual de QUALQUER site via Jina AI para garantir fidelidade."""
    logging.info(f"[Stage 1/4: Universal Reader] Lendo URL: {url}")
    try:
        # Jina AI Reader: Transforma qualquer site em Markdown limpo
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"Accept": "application/json"}
        resp = requests.get(jina_url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            conteudo = resp.json().get('data', {}).get('content', '')
            if len(conteudo) > 50:
                return conteudo[:5000] # Limite para não estourar o contexto do LLM
        
        # Fallback para o modo texto simples se o JSON falhar
        resp_text = requests.get(jina_url, timeout=15)
        if len(resp_text.text) > 50:
            return resp_text.text[:5000]
            
        return None
    except Exception as e:
        logging.error(f"[Universal Reader Error] {e}")
        return None

# --- CONFIGURAÇÕES DE CONSISTÊNCIA VISUAL (Regras de Ouro) ---
ESTILO_VISUAL_ANCORA = "Photorealistic, 8k, Cinematic, Live Action, High-End Commercial, Shot on Arri Alexa, Professional Lighting."
NEGATIVE_PROMPT_PADRAO = "cartoon, illustration, 3d render, anime, painting, drawing, sketch, deformed, low quality, bad anatomy, text, blurry, CGI, Pixar style, Buty Now."

# --- ETAPA 2: O ROTEIRISTA ESTRUTURADO (The Writer - Sandwich Method) ---
def gerar_roteiro_fiel(texto_extraido, tema_usuario=""):
    """Cria um roteiro de 3 atos (Problema -> Solução Real -> Resultado)."""
    logging.info("[Stage 2/4: Screenwriter] Aplicando Estrutura de 3 Atos (Sandwich)...")
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    system_prompt = (
        "VOCÊ É UM DIRETOR DE CRIAÇÃO PUBLICITÁRIA. "
        "Sua missão é criar um roteiro de 15-30s seguindo RIGOROSAMENTE o MÉTODO SANDUÍCHE:\n"
        "ATO 1 (O PROBLEMA): Mostre a dor do usuário usando métodos antigos/ineficientes. Estilo Dramático.\n"
        "ATO 2 (A REVELAÇÃO): O PRODUTO REAL aparece em detalhes (Glory Shot). Use a descrição física exata do site.\n"
        "ATO 3 (O RESULTADO): O problema resolvido e o resultado final perfeito. Termine com CTA 'COMPRE AGORA'.\n\n"
        "DIRETRIZ: Mantenha o tom profissional e realista. Narração deve ser persuasiva e descrever a cena."
    )
    
    user_prompt = (
        f"TEXTO EXTRAÍDO DO SITE (Verdade do Produto):\n{texto_extraido}\n\n"
        f"TEMA DO USUÁRIO: {tema_usuario}\n\n"
        "Gere o roteiro dividido em: CENA 1 (Problema), CENA 2 (Solução com o Produto), CENA 3 (Resultado)."
    )
    
    try:
        resp = client.chat.completions.create(
            model=MODELO_ATIVO,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.5
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"[Screenwriter Error] {e}")
        return "Cena 1: Problema. Cena 2: Produto. Cena 3: Resultado."

# --- ETAPA 3: O DIRETOR TÉCNICO (The Director - Style Anchor) ---
def gerar_prompt_video_tecnico(roteiro_narrativo):
    """Converte o roteiro em prompts técnicos injetando Ancoragem de Estilo e Negative Prompts."""
    logging.info("[Stage 3/4: Director] Injetando Ancoragem de Estilo e Anti-Alucinação...")
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    system_prompt = (
        f"Você é um Diretor de Fotografia de IA Especialista em Commercial Film. "
        f"Transforme o roteiro em um JSON ARRAY de 3 prompts visuais.\n\n"
        f"REGRAS DE OURO:\n"
        f"1. Estilo Obrigatório em todas as cenas: {ESTILO_VISUAL_ANCORA}\n"
        f"2. Negative Prompts (O que evitar): {NEGATIVE_PROMPT_PADRAO}\n"
        f"3. Fidelidade: Descreva o produto exatamente como no roteiro (cor, forma, função).\n"
        f"4. Narração: Cada cena deve ter uma narração que descreva EXATAMENTE o que está na tela."
    )
    
    try:
        resp = client.chat.completions.create(
            model=MODELO_ATIVO,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": roteiro_narrativo}],
            temperature=0.3
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"[Director Error] {e}")
        return "[]"

# --- ETAPA 4: O SANITIZADOR (The Sanitizer) ---
def limpar_json_video(conteudo_bruto):
    """Remove tags markdown e garante que o output seja uma lista de strings limpa."""
    logging.info("[Stage 4/4: Sanitizer] Limpando saída técnica...")
    try:
        limpo = re.sub(r'```json|```', '', str(conteudo_bruto), flags=re.IGNORECASE).strip()
        start = limpo.find('[')
        end = limpo.rfind(']')
        if start != -1 and end != -1:
            limpo = limpo[start:end+1]
        
        dados = json.loads(limpo)
        if isinstance(dados, list):
            return [str(c).strip() for c in dados if c]
        return []
    except Exception as e:
        logging.error(f"[Sanitizer Error] {e}")
        return re.findall(r'"([^"]{15,})"', str(conteudo_bruto))

def buscar_e_baixar_audio(query):
    if os.path.exists(query): return query, os.path.basename(query)
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        'outtmpl': os.path.join(AUDIO_DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'quiet': True, 'noplaylist': True
    }
    try:
        if not "http" in query: query = f"ytsearch1:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if 'entries' in info: info = info['entries'][0]
            video_id = info['id']
            for f in os.listdir(AUDIO_DOWNLOAD_DIR):
                if video_id in f and f.endswith(".mp3"):
                    return os.path.join(AUDIO_DOWNLOAD_DIR, f), info.get('title', 'Musica')
    except: pass
    return None, None

def gerar_roteiro_universal(tipo, titulo, duracao_segundos, contexto_extra="", image_context=None):
    if duracao_segundos > 60: duracao_segundos = 60
    num_cenas = int(duracao_segundos / 5)
    if num_cenas < 1: num_cenas = 1
    
    logging.info(f"[Diretor Universal] Iniciando Produção Evolutiva (V115) - {tipo}")
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    system_prompt = """
    Voce e um Diretor de Cinema Visionario e Especialista em VFX.
    Sua missao e criar roteiros visuais para videoclipes curtos baseados em um tema ou audio.

    REGRAS DE OURO PARA A SEQUENCIA (Storytelling):
    1. NUNCA repita a acao da cena anterior. A historia deve avancar.
    2. USE A REGRA DOS 3 ATOS:
       - Inicio: Estabelecimento, ambiente, calmaria.
       - Meio: Acao, movimento rapido, conflito, climax.
       - Fim: Resolucao, slow motion, fade out, ou transformacao.
    3. VARIEDADE DE CAMERA (Obrigatorio variar):
       - Se a Cena 1 usou 'Drone Shot', a Cena 2 DEVE usar 'Close-up' ou 'Tracking Shot'.
       - Se a Cena 1 foi 'Slow Motion', a Cena 2 deve ser 'Fast Paced'.

    ESTRUTURA JSON OBRIGATORIA:
    {
      "visual_style": "Estilo artistico (ex: Cyberpunk, National Geographic, Dark Fantasy)",
      "main_subject": "O sujeito principal (ex: Golden Eagle)",
      "scenes": [
        {
          "id": 1,
          "action": "Animate this image. [Camera Move] + [Subject Action].",
          "mood": "Majestic"
        }
      ]
    }

    IMPORTANTE:
    - Use terminologia cinematografica: Bokeh, Dolly Zoom, Rack Focus, Motion Blur, Anamorphic Lens.
    - Mantenha o 'main_subject' consistente, mas MUDE O ANGULO e a ACAO drasticamente a cada cena.
    """

    contexto_base = f"TIPO: {tipo}. TITULO: {titulo}. CONTEXTO: {contexto_extra}."
    if image_context: contexto_base += f" IMAGEM BASE: {image_context}"
    
    user_prompt = f"Gere {num_cenas} cenas evolutivas para: {contexto_base}. Retorne APENAS o JSON."
    
    try:
        resp = client.chat.completions.create(
            model=MODELO_ATIVO,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        content = resp.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        
        scenes = data.get("scenes", [])
        visual_style = data.get("visual_style", "Cinematic")
        main_subject = data.get("main_subject", titulo)
        
        prompts = []
        for s in scenes:
            action = s.get("action", "")
            mood = s.get("mood", "")
            prompts.append(f"{action} Style: {visual_style}. Subject: {main_subject}. Mood: {mood}.")
            
        return prompts[:num_cenas]
    except Exception as e:
        logging.error(f"[Brain Error] {e}")
    
    return [f"Cinematic shot of {titulo}, scene {i+1}, 8k quality" for i in range(num_cenas)]

def _thread_processar_solicitacao(user_id, dados_video):
    try:
        tipo = dados_video.get('tipo', 'musica')
        termo = dados_video.get('termo')
        duracao = dados_video.get('duracao', 30)
        tema = dados_video.get('tema', '')
        image_b64_data = dados_video.get('image_b64_data')
        image_context = dados_video.get('image_context')
        
        logging.info(f"[Director] Iniciando JOB para {user_id}: {tipo} - {termo}")
        _notificar_push(user_id, None, f"🎬 Jarvis Studio: Iniciando produção de {tipo} para '{termo}' ({duracao}s)...")

        audio_path = None
        contexto_roteiro = ""
        titulo_display = termo
        base_image_path = None

        # Se uma imagem foi enviada, ela tem prioridade máxima
        if image_b64_data:
            _notificar_push(user_id, None, "🖼️ Imagem recebida! Analisando para criar o roteiro...")
            try:
                img_bytes = base64.b64decode(image_b64_data)
                filename = f"upload_{user_id.split('@')[0]}_{int(time.time())}.png"
                base_image_path = os.path.join(TEMP_UPLOADS_DIR, filename)
                with open(base_image_path, 'wb') as f:
                    f.write(img_bytes)
                logging.info(f"Imagem de base salva em: {base_image_path}")
                # A música se torna secundária, usando um tema ambiente
                audio_path = os.path.join(BASE_DIR, "musica-para-videoclip", "musica_30s.mp3")
                tipo = 'imagem' # Tipo interno para o roteiro
            except Exception as e:
                logging.error(f"Erro ao salvar imagem base: {e}")
                _notificar_push(user_id, None, "❌ Erro ao processar a imagem que você enviou.")
                return

        elif tipo == 'comercial':
            url = extrair_url(termo)
            if url:
                # RESET & ESTÁGIO 1: THE READER
                _notificar_push(user_id, None, "🔍 Estágio 1/4: Lendo conteúdo universal (Jina AI)...")
                texto_site = extrair_texto_url_universal(url)
                
                if not texto_site:
                    _notificar_push(user_id, None, "❌ Não consegui ler este site. Tente outro link.")
                    return

                # ESTÁGIO 2: THE WRITER
                _notificar_push(user_id, None, "🧠 Estágio 2/4: Criando roteiro fiel ao conteúdo...")
                roteiro = gerar_roteiro_fiel(texto_site, tema)
                logging.info(f"Roteiro Fiel: {roteiro}")
                
                # ESTÁGIO 3: THE DIRECTOR
                _notificar_push(user_id, None, "🎬 Estágio 3/4: Gerando visão técnica cinematográfica...")
                json_bruto = gerar_prompt_video_tecnico(roteiro)
                
                # ESTÁGIO 4: THE SANITIZER
                _notificar_push(user_id, None, "🧼 Estágio 4/4: Sanitizando prompts visuais...")
                storyboard = limpar_json_video(json_bruto)
                
                if not storyboard:
                    storyboard = [f"Cinematic 8k video about {tema}"]
                
                titulo_display = "Comercial de " + (tema if tema else "Link Externo")
            else:
                contexto_roteiro = f"Produto: {termo}. {tema}"
                storyboard = gerar_roteiro_universal(tipo, termo, duracao, contexto_extra=contexto_roteiro)
            
            audio_path = os.path.join(BASE_DIR, "musica-para-videoclip", "musica_30s.mp3") 
        
        else: # Tipo é 'musica'
            _notificar_push(user_id, None, "🎵 Baixando trilha sonora...")
            audio_path, titulo_dl = buscar_e_baixar_audio(termo)
            if audio_path: 
                titulo_display = titulo_dl
                try:
                    with AudioFileClip(audio_path) as clip:
                        if clip.duration > duracao:
                            novo_path = audio_path.replace(".mp3", f"_{duracao}s.mp3")
                            clip.subclip(0, duracao).write_audiofile(novo_path, logger=None)
                            audio_path = novo_path
                except Exception as e_clip:
                    logging.warning(f"Não foi possível cortar o áudio: {e_clip}")
            else:
                _notificar_push(user_id, None, "❌ Não achei a música.")
                return
            
            # Para música também podemos usar o fluxo lógico se houver um tema complexo
            storyboard = gerar_roteiro_universal(tipo, titulo_display, duracao, contexto_extra=tema)

        maker = JarvisVideoMaker(base_dir=BASE_DIR)
        
        def callback(msg): pass 

        video_filename = maker.gerar_video_musical(
            audio_path=audio_path if audio_path and os.path.exists(audio_path) else None,
            tema_base=tema,
            storyboard=storyboard,
            status_callback=callback,
            base_image_path=base_image_path
        )

        if video_filename:
            full_path = os.path.join(maker.output_dir, video_filename)
            legenda = f"✨ *{titulo_display.upper()}*\nVideo gerado por Jarvis V29 (Visão Ativa).\nModo: {tipo.capitalize()}"
            _notificar_push(user_id, full_path, legenda)
        else:
            _notificar_push(user_id, None, "❌ Erro na renderização final.")

    except Exception as e:
        logging.error(f"[Director Error] {e}")
        _notificar_push(user_id, None, f"❌ Erro crítico: {e}")

def iniciar_processo_video(user_id, texto_usuario, image_b64_data=None, image_context=None):

    dados = {'tipo': 'musica', 'duracao': 30, 'termo': '', 'tema': '', 'image_b64_data': image_b64_data, 'image_context': image_context}

    texto_lower = texto_usuario.lower()

    

    # Extração de Tempo

    match_tempo = re.search(r'(\d+)\s?s', texto_lower) or re.search(r'(\d+)\s?seg', texto_lower)

    if match_tempo:

        t = int(match_tempo.group(1))

        if t > 60: t = 60

        dados['duracao'] = t



        # Limpeza básica do texto para extrair o tema/comando real



        clean_theme = texto_usuario



        # Gatilhos de limpeza (mais amplos e com bordas de palavras para evitar fragmentos)



        gatilhos_limpeza = [



            r"criar?\s+ví?deo", r"fazer?\s+ví?deo", r"gerar?\s+ví?deo", r"cria\s+ví?deo", r"faz\s+um\s+ví?deo",



            r"criar?\s+clipe", r"fazer?\s+clipe", r"videoclipe", r"ví?deo\s+de\s+produto", r"comercial\s+sobre",



            r"ví?deo\s+comercial", r"ví?deo\s+de\s+venda", r"propaganda\s+de", r"fazer?\s+um\s+ví?deo", r"cria\s+um\s+ví?deo",



            r"da\s+mú?sica", r"sobre\s+este\s+link", r"desse\s+produto\s+do\s+link", r"com\s+esse\s+link",



            r"com\s+\d+\s?s", r"com\s+\d+\s?seg", r"\d+\s?seg", r"\d+\s?s\b"



        ]



        



        for r in gatilhos_limpeza:



            clean_theme = re.sub(r, "", clean_theme, flags=re.IGNORECASE).strip()



        



        # Remove URLs do tema



        url = extrair_url(texto_usuario)



        if url:



            clean_theme = clean_theme.replace(url, "").strip()



            dados['termo'] = url



            dados['tipo'] = 'comercial'



        elif any(x in texto_lower for x in ["comercial", "produto", "venda", "oferta", "propaganda"]):



            dados['tipo'] = 'comercial'



    



        # Limpeza final de conectores órfãos



        clean_theme = re.sub(r"^(de|do|da|com|sobre)\s+", "", clean_theme, flags=re.IGNORECASE).strip()



        dados['tema'] = clean_theme.strip(", ").strip()



    



    # O que sobrar da limpeza é o "tema" visual (ex: "mulher brasileira fazendo propaganda")

    dados['tema'] = clean_theme.strip(", ").strip()



    # Se tem imagem, o texto do usuário vira o "tema"

    if image_b64_data:

        dados['tipo'] = 'imagem'

        if not dados['termo']:

            dados['termo'] = "Cena baseada na imagem"

    

    # Se ainda não temos termo (não é link nem imagem), o tema vira o termo (ex: nome da música)

    if not dados['termo']:

        dados['termo'] = dados['tema']

    

    if not dados['termo'] and not image_b64_data:

        return None, "🤖 Para criar o vídeo, preciso de mais detalhes: uma imagem, um link, um tema ou uma música."

    

    logging.info(f"[Director] Dados Extraídos: {dados}")

    

    t = threading.Thread(target=_thread_processar_solicitacao, args=(user_id, dados))

    t.start()

    

    if dados['tipo'] == 'imagem':

        tipo_str = "Vídeo a partir da sua imagem"

    elif dados['tipo'] == 'comercial':

        tipo_str = "Comercial/Produto"

    else:

        tipo_str = "Videoclipe"

        

    return dados, f"🎥 Entendido! Iniciando produção de um **{tipo_str}** ({dados['duracao']}s).\n**Contexto:** {dados['tema'] if dados['tema'] else 'Geral'}\nUsarei o motor de análise V3. Fique atento, te envio o resultado!"
