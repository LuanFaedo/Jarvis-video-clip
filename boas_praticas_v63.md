# 🛠️ Jarvis V63 - Boas Práticas & Checklist de Manutenção

## 📋 Checklist Pré-Execução

Antes de rodar qualquer job do Jarvis:

```bash
# 1. Verificar espaço em disco
df -h | grep "/$"  # Deve ter >5GB livres

# 2. Verificar memória RAM
free -h  # Deve ter >4GB disponível

# 3. Verificar se Brave está rodando (kill se necessário)
ps aux | grep -i brave  # Se muitos processos, killall brave

# 4. Verificar VOSK model
ls -la ./tools/vosk_pt_br/  # Deve existir e ter >100MB

# 5. Limpar cache antigo
rm -rf ./temp_cache/*
rm -rf ./anchors/*.png  # Manter apenas últimos 3

# 6. Validar conexão WhatsApp
curl -I https://api.whatsapp.com/  # Deve retornar 200

# 7. Ativar logging
export LOG_LEVEL=DEBUG

# 8. Iniciar Jarvis
python app.py
```

---

## 🔍 Monitoramento em Tempo Real

Abra **3 terminais**:

### Terminal 1: Aplicação Principal
```bash
python app.py 2>&1 | tee ./logs/current_session.log
```

### Terminal 2: Monitor de Recursos
```bash
# Atualizar a cada 2 segundos
watch -n 2 'echo "=== MEMORY ===" && \
free -h && \
echo "=== DISK ===" && \
df -h / && \
echo "=== PROCESSES ===" && \
ps aux | grep python | wc -l'
```

### Terminal 3: Monitor de Logs (Real-time)
```bash
tail -f ./logs/jarvis_v63_*.log | grep -E "ERROR|WARNING|CRITICAL"
```

---

## 🚨 Resposta Rápida a Erros

### Erro: "Target Closed / Browser Killed"
```bash
# 1. Verificar se é realmente OOM
free -h  # Se <500MB, é memória

# 2. Limpar caches
rm -rf ./temp_cache/* ./anchors/*

# 3. Reduzir batch manualmente
# Editar app.py: batch_size = 2

# 4. Reiniciar
pkill -f "python app.py"
python app.py
```

### Erro: "Navigation Timeout"
```bash
# 1. Testar conexão internet
ping -c 3 google.com

# 2. Verificar se servidor Meta está up
curl -s -o /dev/null -w "%{http_code}" https://www.imagine.meta.com/

# 3. Aumentar timeout (app.py)
# search: wait_until="networkidle"
# replace: wait_until="load"

# 4. Retry manual
# Usar mesmo prompt, sistema tenta novamente
```

### Erro: "VOSK Model Not Found"
```bash
# 1. Download correto
mkdir -p ./tools/
cd ./tools/
wget https://alphacephei.com/vosk/models/vosk-model-pt-br-0.3.zip
unzip vosk-model-pt-br-0.3.zip
mv vosk-model-pt-br-0.3 vosk_pt_br/

# 2. Verificar integridade
ls -la ./tools/vosk_pt_br/
# Deve ter: am/, conf/, graph/, ivector/, ...

# 3. Testar
python -c "from vosk import Model; Model('./tools/vosk_pt_br')"
```

### Erro: "Socket Timeout WhatsApp"
```bash
# 1. Verificar conexão
curl -I https://api.whatsapp.com/

# 2. Se arquivo >100MB, comprimir mais
# Editar video_engine.py
# search: crf=18
# replace: crf=23  (mais compressão)

# 3. Usar WhatsApp Web Direct
# Em vez de arquivo, enviar link compartilhado
```

---

## 📈 Métricas Diárias

Crie um script para rodar TODOS os dias:

### `daily_health_check.py`
```python
#!/usr/bin/env python3
import os
import json
from datetime import datetime
from pathlib import Path

def health_check():
    """Verifica saúde do sistema Jarvis"""
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # 1. Disco
    stat = os.statvfs("./")
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
    report["checks"]["disk_free_gb"] = free_gb
    report["checks"]["disk_ok"] = free_gb > 5
    
    # 2. Logs
    log_files = list(Path("./logs").glob("*.log"))
    report["checks"]["log_count"] = len(log_files)
    report["checks"]["latest_log_size_mb"] = (
        max((f.stat().st_size for f in log_files), default=0) / (1024**2)
    )
    
    # 3. Cache
    cache_files = list(Path("./temp_cache").glob("*"))
    report["checks"]["cache_files"] = len(cache_files)
    report["checks"]["cache_cleanup_needed"] = len(cache_files) > 50
    
    # 4. VOSK
    vosk_ok = os.path.exists("./tools/vosk_pt_br/am/")
    report["checks"]["vosk_ready"] = vosk_ok
    
    # 5. Videclipes
    video_files = list(Path("./videoclipes").glob("*.mp4"))
    report["checks"]["videos_generated"] = len(video_files)
    report["checks"]["latest_video_size_mb"] = (
        max((f.stat().st_size for f in video_files), default=0) / (1024**2)
    )
    
    # Salvar report
    with open("./logs/daily_health.json", "a") as f:
        f.write(json.dumps(report) + "\n")
    
    # Imprimir
    print(json.dumps(report, indent=2))
    
    # Alertas
    if not report["checks"]["disk_ok"]:
        print("⚠️  ALERTA: Espaço em disco baixo!")
    if report["checks"]["cache_cleanup_needed"]:
        print("⚠️  ALERTA: Cache com muitos arquivos, limpar")
    if not report["checks"]["vosk_ready"]:
        print("🚨 CRÍTICO: VOSK não encontrado, baixar modelo")

if __name__ == "__main__":
    health_check()
```

**Adicionar ao crontab (roda diariamente às 6 da manhã):**
```bash
crontab -e

# Adicionar:
0 6 * * * cd /path/to/jarvis && python daily_health_check.py >> ./logs/cron.log 2>&1
```

---

## 🔄 Rotina Semanal de Manutenção

### Segunda-feira (10h)
```bash
# Limpar logs antigos (>7 dias)
find ./logs -name "*.log" -mtime +7 -delete

# Revisar daily_health.json
tail -50 ./logs/daily_health.json | grep -i "false\|alerta"

# Rodar teste de integridade
python -c "
from tools.vosk import Model
from pathlib import Path
print('✅ VOSK OK') if Path('./tools/vosk_pt_br').exists() else print('❌ VOSK Missing')
"
```

### Sexta-feira (18h)
```bash
# Backup de vídeos gerados essa semana
tar -czf ./backups/videoclipes_$(date +%Y%m%d).tar.gz ./videoclipes/

# Limpeza agressiva de temp
rm -rf ./temp_cache/*

# Relatório semanal
echo "📊 Vídeos gerados essa semana:"
find ./videoclipes -mtime -7 | wc -l
echo "📊 Espaço usado:"
du -sh ./videoclipes
```

---

## 🐛 Debugging Avançado

### Ativar Verbose Mode
```python
# Em app.py, topo do arquivo
import logging
logging.basicConfig(level=logging.DEBUG)

# Tudo vai para console + arquivo
```

### Rastrear uma Execução Específica
```bash
# Incluir ID único em cada execução
JOB_ID=$(date +%s)
python app.py --job-id $JOB_ID --verbose

# Depois, extrair apenas logs desse job
grep "JOB_ID:$JOB_ID" ./logs/*.log
```

### Profiling de Performance
```python
# app.py
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# ... seu código ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats("cumulative")
stats.print_stats(20)  # Top 20 funções mais lentas
```

---

## 🔐 Segurança & Backup

### Backup Automático de Configurações
```bash
# Backup dos arquivos críticos
mkdir -p ./backups/configs_$(date +%Y%m%d)
cp app.py ./backups/configs_$(date +%Y%m%d)/
cp video_engine.py ./backups/configs_$(date +%Y%m%d)/
cp memory.md ./backups/configs_$(date +%Y%m%d)/  # ⭐ SEU MEMORY.MD
```

### Rotação de Logs
```bash
# Já implementado no logging, mas validar:
find ./logs -name "*.log" -mtime +7 -delete

# Manter apenas 7 dias
```

### Credenciais Seguras
```bash
# NÃO commitar em git:
.env  # Chaves API, tokens WhatsApp
./tools/vosk_pt_br  # Modelo grande

# Usar .gitignore:
echo ".env" >> .gitignore
echo "tools/vosk_pt_br" >> .gitignore
echo "temp_cache/" >> .gitignore
echo "logs/" >> .gitignore
```

---

## 📞 Suporte & Escalação

### Se erro recorrente
1. **Reproduzir:** Executar mesma tarefa 3x
2. **Documentar:** Capturar log completo (grep para erro)
3. **Isolar:** Testar componente separadamente
4. **Escalar:** Usar taxonomy de erros em `erro_taxonomia_v63.md`

### Template de Relatório de Bug
```markdown
## 🐛 Bug Report

**Versão:** V63
**Data:** 2026-01-29
**Frequência:** 1 em 10 vídeos

**Comportamento:**
[Descrever o que aconteceu]

**Esperado:**
[Descrever o que deveria ter acontecido]

**Logs Relevantes:**
[grep do erro do arquivo ./logs/jarvis_v63_*.log]

**Categoria (usar taxonomy):**
- [ ] Browser Crash (1.1-1.3)
- [ ] Upload/Frame (2.1-2.2)
- [ ] Áudio (3.1-3.2)
- [ ] Conteúdo (4.1-4.2)
- [ ] Performance (5.1-5.2)
- [ ] WhatsApp (6.1)

**Solução Testada:**
[Qual solução de V63 foi aplicada?]

**Resultado:**
[Bug resolvido? Sim/Não]
```

---

## 🎯 Checklist Mensal

No final de cada mês:

- [ ] Revisar `daily_health.json` para patterns
- [ ] Atualizar `memory.md` com novos insights
- [ ] Limpar todas as pastas temp/cache
- [ ] Backup completo (tar -czf)
- [ ] Testar recuperação do backup
- [ ] Revisar uso de disco (./videoclipes) → arquivar antigos
- [ ] Atualizar modelos VOSK se nova versão disponível
- [ ] Benchmark: gerar 10 vídeos, cronometrar tempo médio
- [ ] Documento de lições aprendidas

---

## 📚 Referência Rápida

| Situação | Comando | Resultado |
|----------|---------|-----------|
| Limpar TUDO | `./cleanup.sh` | Volta ao estado inicial |
| Teste de conectividade | `./test_connectivity.sh` | Relatório de recursos |
| Rodar com debug | `LOG_LEVEL=DEBUG python app.py` | Logs verbosos |
| Stress test (5 vídeos) | `python stress_test.py` | Performance baseline |
| Ver logs em tempo real | `tail -f ./logs/jarvis_v63_*.log` | Live feed de erros |
| Health check | `python daily_health_check.py` | Relatório de saúde |

---

**Manutenção regular = Zero downtime ✨**

*Última atualização: 29/01/2026*
