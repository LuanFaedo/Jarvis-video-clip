import requests
import json
import time

def testar_comandos_jarvis():
    # Tenta porta 5000 (padrão do Jarvis)
    url = "http://127.0.0.1:5000/api/whatsapp"
    
    testes = [
        {
            "nome": "Teste de Ação de Sistema (CMD)",
            "payload": {
                "sender": "Patrick",
                "text": "Jarvis, liste os arquivos desta pasta agora",
                "chat_id": "test_debug"
            },
            "esperado": "[[CMD:"
        },
        {
            "nome": "Teste de Automação (AUTO)",
            "payload": {
                "sender": "Patrick",
                "text": "Jarvis, abra o notepad",
                "chat_id": "test_debug"
            },
            "esperado": "[[AUTO:"
        }
    ]

    print("\n[TESTE] Verificando se o Jarvis responde com as novas tags...\n")

    for t in testes:
        print(f"Submetendo: {t['nome']}...")
        try:
            # Note: O Jarvis precisa estar rodando (python app.py)
            resp = requests.post(url, json=t['payload'], timeout=45)
            if resp.status_code == 200:
                res_json = resp.json()
                texto = res_json.get('response', '')
                if t['esperado'] in texto:
                    print(f"  ✅ SUCESSO! Tag encontrada: {t['esperado']}")
                else:
                    print(f"  ❌ FALHA. A IA respondeu, mas sem a tag. Resposta: {texto[:100]}...")
            else:
                print(f"  ❌ ERRO: Status Code {resp.status_code}")
        except Exception as e:
            print(f"  ⚠️ ERRO DE CONEXAO: Certifique-se que o 'app.py' esta rodando. ({e})")
        
        time.sleep(1)

if __name__ == "__main__":
    testar_comandos_jarvis()