import os
import time
import logging
import pyperclip
from playwright.sync_api import sync_playwright

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_meta_input():
    # Caminhos do Brave (copiados do video_engine.py)
    paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe", 
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe", 
        os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
    ]
    brave_path = next((p for p in paths if os.path.exists(p)), None)
    
    user_data = os.path.join(os.getcwd(), "brave_profile_jarvis")
    
    print(f"--- INICIANDO DIAGNÓSTICO DE INPUT META AI ---")
    print(f"Brave Path: {brave_path}")
    print(f"Profile: {user_data}")

    with sync_playwright() as p:
        print("Lançando navegador...")
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=user_data, 
            executable_path=brave_path, 
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = ctx.pages[0]
        
        print("Acessando Meta AI...")
        page.goto("https://www.meta.ai")
        time.sleep(8) # Espera carregar
        
        # Tirar print inicial
        page.screenshot(path="debug_meta_01.png")
        print("Screenshot inicial salva: debug_meta_01.png")

        # Tenta localizar input com a nova lógica V167
        seletores = [
            "textarea",
            "div[role='textbox']", 
            "div[contenteditable='true']"
        ]
        
        input_loc = None
        found_selector = None
        
        print("Buscando seletores...")
        for sel in seletores:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    if loc.is_visible(timeout=1000):
                        print(f"✅ SELETOR ENCONTRADO: {sel}")
                        input_loc = loc
                        found_selector = sel
                        # Desenha borda vermelha para confirmação visual
                        page.evaluate(f"document.querySelector('{sel}').style.border = '5px solid red'")
                        break
                    else:
                        print(f"⚠️ Seletor existe mas não está visível: {sel}")
            except Exception as e:
                print(f"Erro ao testar {sel}: {e}")
        
        if not input_loc:
            print("❌ NENHUM SELETOR DE INPUT ENCONTRADO!")
            page.screenshot(path="debug_meta_fail_selector.png")
            ctx.close()
            return

        # Teste de Foco e Clique
        print("Tentando clicar...")
        try:
            input_loc.click(force=True)
            time.sleep(1)
        except Exception as e:
            print(f"Erro no clique: {e}")

        # Teste de Digitação Global (Keyboard)
        print("Tentando Digitação Global (Page Keyboard)...")
        prompt_teste = "TESTE GLOBAL V167"
        
        try:
            page.keyboard.type(prompt_teste, delay=50)
            time.sleep(2)
            
            # Validação
            texto_atual = input_loc.input_value() # Para textarea usa-se input_value
            print(f"Conteúdo após Type Global: '{texto_atual}'")
            
            if not texto_atual:
                 texto_atual = input_loc.inner_text() # Fallback para div
                 print(f"Conteúdo (inner_text): '{texto_atual}'")

        except Exception as e:
            print(f"Erro no keyboard global: {e}")

            
        print("Fechando em 5 segundos...")
        time.sleep(5)
        ctx.close()

if __name__ == "__main__":
    test_meta_input()
