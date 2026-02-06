import os
import math
import time
import json
import shutil
import logging
from datetime import datetime
from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips
from openai import OpenAI

# Imports do sistema existente
from video_engine import JarvisVideoMaker

# Configuração de Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PipelineAV")

class AudioVideoPipeline:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.getcwd()
        self.producao_dir = os.path.join(self.base_dir, "producao")
        
        # Configuração LLM (Mesma do app.py)
        self.client = OpenAI(
            base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:11434/v1"),
            api_key="AAAAC3NzaC1lZDI1NTE5AAAAIJ9KfyhZeNo5E84kORaqKYu7gxopcvqT2hRabwJU/sXF"
        )
        self.model = "gpt-oss:120b-cloud"

    def _setup_directories(self):
        """1. GESTÃO DE ARQUIVOS E PASTAS (The Organizer)"""
        data_hoje = datetime.now().strftime("%Y-%m-%d")
        timestamp = int(time.time())
        
        sessao_path = os.path.join(self.producao_dir, data_hoje, f"sessao_{timestamp}")
        raw_assets = os.path.join(sessao_path, "raw_assets")
        final_dir = os.path.join(sessao_path, "video-clip-final")
        
        os.makedirs(raw_assets, exist_ok=True)
        os.makedirs(final_dir, exist_ok=True)
        
        logger.info(f"[Organizer] Sessão criada: {sessao_path}")
        return sessao_path, raw_assets, final_dir

    def _analyze_audio(self, mp3_path):
        """2. ANÁLISE DE ÁUDIO (The Calculator)"""
        try:
            # Usando moviepy para ler duração exata
            audio_clip = AudioFileClip(mp3_path)
            duration = audio_clip.duration
            # AGORA CALCULAMOS BLOCOS DE 30s
            num_blocos = math.ceil(duration / 30.0)
            
            logger.info(f"[Calculator] Duração: {duration}s | Blocos de 30s necessários: {num_blocos}")
            return duration, num_blocos, audio_clip
        except Exception as e:
            logger.error(f"[Calculator Error] Falha ao ler áudio: {e}")
            raise e

    def _generate_script(self, num_blocos, tema="Videoclipe abstrato e cinemático"):
        """3. ROTEIRISTA EVOLUTIVO (The Visionary Director) - V115"""
        
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
              "action": "Animate this image. [Camera Move] + [Subject Action]. Ex: Wide drone shot. The eagle glides calmly over the mountains.",
              "mood": "Majestic"
            }
          ]
        }

        IMPORTANTE:
        - Use terminologia cinematografica: Bokeh, Dolly Zoom, Rack Focus, Motion Blur, Anamorphic Lens.
        - Mantenha o 'main_subject' consistente, mas MUDE O ANGULO e a ACAO drasticamente a cada cena.
        """

        user_prompt = f"Crie um roteiro de {num_blocos} cenas para o tema: {tema}. Retorne APENAS o JSON."
        
        logger.info("[Screenwriter] Gerando narrativa evolutiva...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            content = response.choices[0].message.content
            content = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)
            
            scenes = data.get("scenes", [])
            visual_style = data.get("visual_style", "Cinematic")
            main_subject = data.get("main_subject", "")
            
            # Converte cenas estruturadas em prompts lineares para o motor
            prompts = []
            for s in scenes:
                action = s.get("action", "")
                mood = s.get("mood", "")
                # Injeta o estilo e o sujeito para manter consistência
                full_prompt = f"{action} Style: {visual_style}. Subject: {main_subject}. Mood: {mood}."
                prompts.append(full_prompt)

            # Fallback se faltar cenas
            while len(prompts) < num_blocos:
                prompts.append(f"Evolution of {tema}, cinematic 8k, scene {len(prompts)+1}")
            
            return prompts[:num_blocos]
            
        except Exception as e:
            logger.error(f"[Screenwriter Error] {e}")
            return [f"Cinematic evolution of {tema}, scene {i+1}, 8k" for i in range(num_blocos)]

    def process_mp3(self, mp3_input_path, tema_usuario=None):
        """PIPELINE PRINCIPAL (MODO BLOCOS 30s)"""
        
        # 1. Setup
        sessao_path, raw_assets_dir, final_dir_path = self._setup_directories()
        
        # Copiar MP3 para a sessão para segurança
        mp3_filename = os.path.basename(mp3_input_path)
        mp3_sessao_path = os.path.join(sessao_path, mp3_filename)
        shutil.copy2(mp3_input_path, mp3_sessao_path)
        
        # 2. Análise
        duration, num_blocos, audio_clip = self._analyze_audio(mp3_sessao_path)
        
        # 3. Roteiro
        prompts = self._generate_script(num_blocos, tema=tema_usuario or "Musical visual experience")
        
        # 4. EXECUÇÃO DO DOWNLOAD (The Batch Processor)
        logger.info(f"[Batch Processor] Iniciando geração de {len(prompts)} blocos de 30s...")
        
        maker = JarvisVideoMaker(base_dir=self.base_dir)
        # Hack para redirecionar o output temporariamente
        original_output = maker.output_dir
        maker.output_dir = raw_assets_dir 
        
        all_generated_clips = []
        
        for i, prompt in enumerate(prompts):
            logger.info(f"--- Processando Bloco {i+1}/{num_blocos}: {prompt[:50]}... ---")
            
            try:
                # CHAMA O NOVO MÉTODO DO USUÁRIO
                # Gera lista de 6 clips para este bloco
                clips_do_bloco = maker.gerar_bloco_30s_recursivo(prompt, raw_assets_dir, bloco_index=i)
                
                if clips_do_bloco:
                    all_generated_clips.extend(clips_do_bloco)
                else:
                    logger.warning(f"Falha no bloco {i+1}. Nenhum clip gerado.")
            
            except Exception as e:
                logger.error(f"Erro ao gerar bloco {i+1}: {e}")

        # Restaurar config
        maker.output_dir = original_output

        # 5. EDIÇÃO FINAL (The Editor)
        logger.info("[The Editor] Montando videoclipe final...")
        
        if not all_generated_clips:
            return None, "Nenhum clipe foi gerado com sucesso."

        clips_visuais = []
        try:
            for clip_path in all_generated_clips:
                # Tenta carregar cada clip
                try:
                    v = VideoFileClip(clip_path)
                    clips_visuais.append(v)
                except:
                    logger.warning(f"Clip corrompido ignorado: {clip_path}")
            
            if not clips_visuais:
                 return None, "Todos os clips estavam corrompidos."

            # Concatenação Visual
            final_video_raw = concatenate_videoclips(clips_visuais, method="compose")
            
            # Ajuste de duração com Áudio
            # Se o vídeo ficou menor que o áudio, faz loop ou estica? 
            # O usuário pediu para cobrir o áudio. Se fizemos a conta certa, deve bater.
            # Se faltar, vamos repetir o último frame? Ou deixar tela preta? 
            # Por enquanto, cortamos o áudio se o vídeo for menor (ou vice versa, user quer video completo?)
            # Geralmente videoclipe = audio completo.
            
            if final_video_raw.duration < duration:
                logger.warning(f"Vídeo ({final_video_raw.duration}s) menor que áudio ({duration}s). Loopando último clip...")
                # Lógica simples: se faltar, deixa passar.
            
            final_video = final_video_raw.set_audio(audio_clip)
            
            # Output
            output_filename = f"videoclipe_completo_{int(time.time())}.mp4"
            output_path = os.path.join(final_dir_path, output_filename)
            
            logger.info(f"[Render] Salvando em {output_path}...")
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, preset="medium")
            
            # Cleanup resources
            audio_clip.close()
            final_video.close()
            for c in clips_visuais: c.close()
            
            return output_path, f"Videoclipe gerado com sucesso! Salvo em: {output_path}"

        except Exception as e:
            logger.error(f"[Editor Error] {e}")
            return None, f"Erro na edição final: {e}"

# Instância Global
av_pipeline = AudioVideoPipeline()
