import os
import sys
import json
import pyaudio
import pyautogui
import pyperclip
from vosk import Model, KaldiRecognizer
import re
import time

def treat_text(text):
    """
    Formatação básica rápida (Regex) para não depender de IA lenta.
    """
    # Capitalização inicial
    if text:
        text = text[0].upper() + text[1:]
    
    replacements = [
        (r"\bvírgula\b", ","),
        (r"\bvirgula\b", ","),
        (r"\bponto\b", "."),
        (r"\binterrogação\b", "?"),
        (r"\bexclamação\b", "!"),
        (r"\bnova linha\b", "\n"),
        (r"\bparágrafo\b", "\n\n")
    ]
    
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text

def paste_text(text):
    """
    Usa a área de transferência para colar texto instantaneamente sem erros de acento.
    """
    try:
        pyperclip.copy(text + " ")
        pyautogui.hotkey("ctrl", "v")
    except Exception as e:
        print(f"[ERRO AO COLAR] {e}")

def listen_and_type():
    # Definição do caminho do modelo
    model_path = "tools/vosk-model-small-pt-0.3"
    
    if not os.path.exists(model_path):
        if os.path.exists("vosk-model-small-pt-0.3"):
            model_path = "vosk-model-small-pt-0.3"
        elif os.path.exists("../tools/vosk-model-small-pt-0.3"):
            model_path = "../tools/vosk-model-small-pt-0.3"
        else:
            print(f"[ERRO] Modelo Vosk não encontrado.")
            sys.exit(1)

    print(f"Carregando modelo offline ({model_path})...")
    try:
        model = Model(model_path)
    except Exception as e:
        print(f"[ERRO] Falha ao carregar modelo: {e}")
        sys.exit(1)

    p = pyaudio.PyAudio()
    
    # Seleção inteligente de dispositivo
    device_index = None
    try:
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            dev_info = p.get_device_info_by_host_api_device_index(0, i)
            dev_name = dev_info.get('name')
            if dev_info.get('maxInputChannels') > 0:
                if "Realtek" in dev_name or "USB" in dev_name:
                    device_index = i
                    print(f"Dispositivo selecionado: {dev_name} (ID: {i})")
                    break
        if device_index is None:
            device_index = 0
    except Exception:
        pass

    try:
        stream = p.open(format=pyaudio.paInt16, 
                        channels=1, 
                        rate=16000, 
                        input=True, 
                        input_device_index=device_index,
                        frames_per_buffer=4096)
        stream.start_stream()
    except Exception as e:
        print(f"[ERRO] Erro microfone: {e}")
        sys.exit(1)

    rec = KaldiRecognizer(model, 16000)

    print("\n" + "="*60)
    print("      MODO DITADO JARVIS (TURBO / OFFLINE)      ")
    print("="*60)
    print("[PRONTO] Digitação INSTANTÂNEA ativada.")
    print("Diga 'vírgula', 'ponto', etc. para pontuar.")
    print("Diga 'PARAR DITADO' para encerrar.")
    print("-" * 60)

    while True:
        try:
            data = stream.read(4096, exception_on_overflow=False)
            
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get('text', '')

                if text:
                    if "parar ditado" in text.lower():
                        print("\n[Encerrando ditado...]")
                        break
                    
                    # Processamento Local Instantâneo
                    final_text = treat_text(text)
                    
                    print(f"Ouvido: {text}")
                    
                    # Cola instantaneamente
                    paste_text(final_text)
            
        except KeyboardInterrupt:
            print("\n[Encerrado pelo usuário]")
            break
        except OSError as e:
            if e.errno == -9999:
                 time.sleep(0.1)
                 continue
            break
        except Exception as e:
            print(f"\n[ERRO] {e}")
            break

    try:
        if stream.is_active():
            stream.stop_stream()
        stream.close()
    except:
        pass
    p.terminate()

if __name__ == "__main__":
    listen_and_type()