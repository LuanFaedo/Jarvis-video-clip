import os
import json
import wave
import zipfile
import requests
import logging
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment
import librosa
import numpy as np

# Configuração
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
VOSK_MODEL_NAME = "vosk-model-small-pt-0.3"
VOSK_MODEL_PATH = os.path.join(TOOLS_DIR, VOSK_MODEL_NAME)
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"

import threading

logger = logging.getLogger("JarvisAudioScanner")

class AudioScanner:
    def __init__(self):
        self.model = None
        self.model_path = os.path.join("tools", VOSK_MODEL_NAME)
        self.model_ready_event = threading.Event()
        
        # Inicia carregamento em background
        threading.Thread(target=self._load_model_bg, daemon=True).start()

    def _load_model_bg(self):
        """Carrega o modelo em background."""
        self._ensure_model()
        self._load_model()
        self.model_ready_event.set()

    def _load_model(self):
        """Tenta carregar o modelo VOSK."""
        try:
            if os.path.exists(self.model_path):
                logger.info(f"Carregando modelo VOSK em background: {self.model_path}")
                self.model = Model(self.model_path)
                logger.info("Modelo VOSK carregado com sucesso.")
            else:
                logger.error(f"Caminho do modelo inválido: {self.model_path}")
        except Exception as e:
            logger.error(f"Falha ao carregar VOSK: {e}")
            self.model = None

    def _ensure_model(self):
        """Baixa e extrai o modelo VOSK se não existir."""
        if not os.path.exists(TOOLS_DIR):
            os.makedirs(TOOLS_DIR)
        
        # Verifica se o modelo já existe e não está vazio
        if os.path.exists(VOSK_MODEL_PATH) and os.listdir(VOSK_MODEL_PATH):
            return

        logger.info(f"Modelo VOSK não encontrado em {VOSK_MODEL_PATH}. Baixando...")
        zip_path = os.path.join(TOOLS_DIR, "model.zip")
        
        try:
            # Download com Headers para evitar bloqueio 403/Redirecionamento
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(VOSK_MODEL_URL, headers=headers, stream=True)
            response.raise_for_status() # Garante que não é erro 404/403
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024 * 1024 # 1MB
            wrote = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    wrote += len(chunk)
                    f.write(chunk)
                    if total_size > 0:
                        percent = (wrote / total_size) * 100
                        if int(percent) % 20 == 0: logger.info(f"Download: {percent:.1f}%")
            
            # Extração
            if not zipfile.is_zipfile(zip_path):
                raise Exception("Arquivo baixado não é um ZIP válido.")

            logger.info("Extraindo modelo...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(TOOLS_DIR)
            
            # Limpeza
            os.remove(zip_path)
            logger.info("Modelo instalado com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao baixar modelo VOSK: {e}")
            # Tentar limpar zip corrompido
            if os.path.exists(zip_path): os.remove(zip_path)

    def transcrever_audio(self, file_path):
        """Transcreve um arquivo de áudio para texto (Offline)."""
        if not self.model_ready_event.is_set():
            logger.info("Aguardando finalização do carregamento do VOSK...")
            self.model_ready_event.wait()

        if not self.model:
            return "ERRO: Modelo de voz offline não carregado."

        try:
            # Converter para WAV mono 16kHz (Requisito do VOSK)
            audio = AudioSegment.from_file(file_path)
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            rec = KaldiRecognizer(self.model, 16000)
            rec.SetWords(True)
            
            # Processar em chunks
            step = 4000
            data = audio.raw_data
            
            full_text = ""
            for i in range(0, len(data), step):
                chunk = data[i:i+step]
                if rec.AcceptWaveform(chunk):
                    res = json.loads(rec.Result())
                    full_text += res.get("text", "") + " "
            
            final_res = json.loads(rec.FinalResult())
            full_text += final_res.get("text", "")
            
            return full_text.strip()
            
        except Exception as e:
            logger.error(f"Erro na transcrição VOSK: {e}")
            return f"ERRO TRANSCRICAO: {str(e)}"

    def analisar_musica(self, file_path):
        """Analisa BPM e estrutura musical usando Librosa."""
        try:
            y, sr = librosa.load(file_path, duration=60) # Analisa 1 min
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            
            # Detectar onset (intensidade)
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            
            return {
                "bpm": round(tempo),
                "duration": librosa.get_duration(y=y, sr=sr),
                "energy": float(np.mean(onset_env))
            }
        except Exception as e:
            logger.error(f"Erro na análise musical: {e}")
            return None

# Instância global
scanner = AudioScanner()
