import time
import video_director
import sys

# Simula o ID do usuário (Patrick)
USER_ID = "Patrick_Simulacao"

def teste_interacao(texto):
    print(f"\n[Usuário]: {texto}")
    dados, resposta = video_director.iniciar_processo_video(USER_ID, texto)
    print(f"[Jarvis]: {resposta}")
    return dados

if __name__ == "__main__":
    print("=== TESTE DE INTEGRAÇÃO: JARVIS DIRECTOR V27 ===")
    
    # 1. Teste Vago (Deve perguntar detalhes)
    print("\n--- Cenário 1: Pedido Vago ---")
    teste_interacao("Jarvis, quero criar um video")
    
    # 2. Teste Completo (Deve iniciar produção)
    print("\n--- Cenário 2: Pedido Comercial Completo ---")
    # Vou usar um link fictício da Nike, mas o scraper vai cair no fallback "Produto genérico" se falhar, o que é esperado no teste offline.
    pedido = "crie um video comercial de 30s sobre este link https://www.nike.com.br/tenis-nike-air-max-sc-masculino-153-169-229-307"
    dados = teste_interacao(pedido)
    
    if dados:
        print("\n[SISTEMA] Aguardando thread de produção iniciar...")
        # Monitora o arquivo de push para ver se o diretor escreveu algo
        for i in range(10):
            try:
                with open("video_push.json", "r", encoding="utf-8") as f:
                    content = f.read()
                    print(f"   -> Status Push (Loop {i}): {content[:100]}...")
            except: pass
            time.sleep(2)
            
        print("\n[SISTEMA] Teste de inicialização concluído. O vídeo estaria sendo renderizado em background.")
