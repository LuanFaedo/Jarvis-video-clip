# 🧠 Jarvis Video Maker - Memória de Desenvolvimento (V200)

**Projeto:** Automação de Vídeo Sequencial (Meta AI)
**Data de Início:** 22/01/2026
**Status Atual:** V200 - Cinematic Master (Ultra Performance & Resiliência)
**Objetivo:** Criar vídeos sequenciais a partir de um prompt, mantendo consistência visual absoluta, qualidade cinematográfica e nexo narrativo evolutivo.

---

## 🏗️ Arquitetura do Ecossistema Jarvis

### 1. Núcleo Unificado (`app.py`)
- **Cérebro:** Flask + Socket.IO orquestrando raciocínio (OpenAI/Ollama) e interfaces.
- **Memória:** SQLite (`memoria/db_memoria.py`) para fatos, finanças e contexto.
- **Automação OS:** `sistema/automacao.py` para controle total do Windows.
- **IoT:** Controle de TV Samsung via WebSocket.

### 2. Motor de Vídeo Playwright (`video_engine.py`)
- **Navegador:** Brave Browser com perfil persistente (`brave_profile_jarvis`).
- **Protocolo Daisy Chain:** Fluxo contínuo onde o frame N vira a semente do frame N+1.
- **Reply Mode:** Uso do modo "Responder" nativo do chat para maximizar a retenção de contexto.
- **JS Blob Capturer:** Injeção de script para capturar vídeos `blob:` via Base64, superando restrições de download.

### 3. Orquestração e Direção (`video_director.py` & `pipeline_av.py`)
- **The Reader:** Web Scraping via Jina AI para criar comerciais fiéis a sites.
- **The Visionary:** Gerador de roteiros em 3 atos (Problema -> Solução -> Resultado).
- **The Organizer:** Segmentação de áudios longos em blocos de 30 segundos (6 clips de 5s cada).

### 4. Interfaces de Integração
- **WhatsApp Bridge (`jarvis-mcp-whatsapp`):** Ponte Node.js para disparo de imagens e entrega de vídeos.
- **Mobile HUD (`jarvis_flutter`):** Interface Flutter sci-fi com STT/TTS contínuo.

---

## 🛡️ NÚCLEO IMUTÁVEL - PROTOCOLO DE PRESERVAÇÃO
**REGRA DE OURO:** A lógica fundamental de criação e automação contida nos arquivos listados abaixo **NÃO DEVE SER ALTERADA OU DELETADA** (Princípio **APPEND ONLY**).

### 🚫 Arquivos Protegidos:
1.  **`video_engine.py` / `video_engine_async.py`**: Motores de automação.
2.  **`video_director.py`**: Cérebro de roteirização.
3.  **`pipeline_av.py`**: Lógica de segmentação por blocos.
4.  **`app.py`**: Controlador central e rotas de integração.

---

## 📜 Histórico de Evolução & Soluções Chave

### 🚀 Performance Extrema (V191 - V194)
- **Polling Turbo:** Intervalos de scan reduzidos para **0.2s (Imagens)** e **0.5s (Vídeos)**.
- **Parallel Boot:** Carregamento do modelo VOSK em thread secundária, eliminando tempo de boot da aplicação.
- **WhatsApp Fast-Notify:** Detecção de conclusão de arquivo em **0.5s** para entrega imediata.

### 🛡️ Resiliência & Estabilização (V192 - V196)
- **Smart Recovery:** Pós-F5 (Reload), o sistema escaneia o histórico por 20s antes de reenviar prompts, eliminando pedidos duplicados.
- **Hard Wait Stabilizer:** Espera fixa de **25s** na semente inicial para garantir renderização estável antes do escaneamento.
- **F5 de Verificação:** Realiza reload tático se nada for detectado após o tempo de espera inicial.

### 🎨 Cinematic Engine V200 (Atual)
- **Dynamic Prompting:** Sorteio aleatório de Lentes (**IMAX 70mm, Anamorphic, Macro**), Iluminação (**God rays, Neon, Golden Hour**) e Movimentos (**Dolly Zoom, Tracking, Drone**).
- **Anti-Repetição:** Cada cena possui estética única, proibindo a monotonia visual.
- **Chase Cam:** Foco em vetores de movimento contínuos para evitar "Morphing" ou quebras de direção do sujeito.

---

## 🛠️ Tecnologias & Dependências Core
- **Backend:** Flask, Flask-SocketIO, Playwright, MoviePy, OpenCV (CV2).
- **Voz/Áudio:** VOSK (Offline), Edge-TTS, Librosa (BPM/Energia), Pydub.
- **Inteligência:** OpenAI API (gpt-oss:120b-cloud), Ollama.
- **Utilitários:** PyAutoGUI, Pyperclip, BeautifulSoup4, Jina AI.

---

## 🛑 Protocolo de Atualização (Lei do Projeto)
Sempre que uma nova funcionalidade for implementada com sucesso, as alterações técnicas devem ser registradas aqui. **Execução > Explicação**. Testes imediatos são obrigatórios.

*Atualizado em: 05/02/2026 - Versão V200 Estável.*