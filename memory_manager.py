import os
import psutil
import logging
import glob
import gc
import time
import shutil

logger = logging.getLogger("JarvisMemory")

class MemoryManager:
    def __init__(self, max_memory_percent=80, cache_dir="./temp_cache"):
        self.max_memory_percent = max_memory_percent
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def check_memory(self):
        """Retorna a porcentagem de uso de RAM."""
        memory = psutil.virtual_memory()
        return memory.percent

    def adaptive_batch_size(self):
        """Define o tamanho do batch baseado na memória disponível."""
        mem = self.check_memory()
        if mem > 85:
            logger.warning(f"Memória CRÍTICA ({mem}%)! Reduzindo batch para 1.")
            return 1
        elif mem > 70:
            logger.warning(f"Memória ALTA ({mem}%)! Reduzindo batch para 2.")
            return 2
        elif mem > 50:
            return 3
        else:
            return 4

    def cleanup_cache(self, keep_last=3):
        """Limpa arquivos antigos do cache, mantendo apenas os N mais recentes."""
        try:
            files = sorted(glob.glob(os.path.join(self.cache_dir, "*")), 
                           key=os.path.getmtime, reverse=True)
            
            deleted_count = 0
            for f in files[keep_last:]:
                try:
                    if os.path.isdir(f):
                        shutil.rmtree(f)
                    else:
                        os.remove(f)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Erro ao deletar {f}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Limpeza de cache: {deleted_count} itens removidos.")
                
        except Exception as e:
            logger.error(f"Erro na limpeza de cache: {e}")

    def force_gc(self):
        """Força a coleta de lixo do Python."""
        before = self.check_memory()
        gc.collect()
        after = self.check_memory()
        logger.info(f"Garbage Collector: {before}% -> {after}%")

    def monitor_and_act(self):
        """Verifica memória e age se necessário (limpeza + GC)."""
        mem = self.check_memory()
        if mem > self.max_memory_percent:
            logger.warning(f"ALERTA DE MEMÓRIA ({mem}%). Iniciando limpeza de emergência...")
            self.force_gc()
            self.cleanup_cache(keep_last=1)
