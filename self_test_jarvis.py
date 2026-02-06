import asyncio
import os
import sys

# Adiciona o diretório atual ao path para importar o app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Mock de notificação push para não crashar o teste
def _notificar_push_video(user_id, file_path, caption):
    print(f"[TESTE PUSH] Target: {user_id} | Video: {file_path} | Msg: {caption}")

# Sobrescreve a função global no módulo app para o teste
import app
app._notificar_push_video = _notificar_push_video

async def main():
    print("🧪 [TESTE AUTÔNOMO] Iniciando validação de Geração de Vídeo...")
    
    # 1. Parâmetros de Teste
    user_id = "TEST_RECOVERY_SYSTEM"
    audio_path = r"D:\\compartilhado\\Projetos\\jarvis01\\automação_video_01\\audios\\upload_1770078305.mp3"
    storyboard = [
        "A futuristic robot fixing a clock",
        "The clock starts glowing neon blue"
    ]
    titulo = "Teste de Estabilidade Jarvis V160"

    if not os.path.exists(audio_path):
        print(f"❌ Áudio não encontrado: {audio_path}")
        return

    # 2. Execução do Pipeline
    try:
        print(f"🎬 Chamando Pipeline Ultra-Resiliente...")
        # Chamamos a função interna do app.py que acabamos de fixar
        await app._pipeline_paralelo_interno(user_id, audio_path, storyboard, titulo)
        print("\n✅ [FIM DO TESTE] Pipeline finalizado.")
    except Exception as e:
        print(f"🔥 [FALHA NO TESTE] Erro catastrófico: {e}")

if __name__ == "__main__":
    asyncio.run(main())
