import time
import logging
import os
from PIL import Image, ImageEnhance
import cv2
import numpy as np

logger = logging.getLogger("JarvisSubjectLock")

class SubjectLockManager:
    def __init__(self, initial_prompt):
        self.initial_prompt = initial_prompt
        self.subject_description = self._extract_subject(initial_prompt)
        # Visual Lock: Descrição que será injetada em todos os frames
        self.visual_lock_prompt = f"Consistent character: {self.subject_description}, detailed face, same clothing, 8k, cinematic lighting"
        self.reference_image_path = None

    def _extract_subject(self, prompt):
        """
        Extrai o sujeito principal do prompt.
        (Versão simplificada: pega o início da string até a primeira vírgula ou ponto)
        """
        # TODO: Usar NLP ou LLM para extração mais precisa no futuro
        subject = prompt.split(',')[0].split('.')[0]
        logger.info(f"Subject Lock definido: '{subject}'")
        return subject

    def set_reference_image(self, image_path):
        """Define a imagem âncora para comparação de consistência."""
        if os.path.exists(image_path):
            self.reference_image_path = image_path
            logger.info(f"Imagem de referência definida: {image_path}")

    def enhance_prompt(self, scene_prompt):
        """Injeta o lock visual no prompt da cena."""
        return f"{scene_prompt}. {self.visual_lock_prompt}"

    def validate_consistency(self, new_image_path, threshold=0.6):
        """
        Compara a nova imagem com a referência usando histograma de cores (OpenCV).
        Retorna True se passar no teste de consistência.
        """
        if not self.reference_image_path:
            return True # Sem referência, aceita tudo

        try:
            img1 = cv2.imread(self.reference_image_path)
            img2 = cv2.imread(new_image_path)
            
            if img1 is None or img2 is None:
                return False

            # Converter para HSV para melhor comparação de cor
            hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)

            # Calcular histogramas
            hist1 = cv2.calcHist([hsv1], [0, 1], None, [50, 60], [0, 180, 0, 256])
            hist2 = cv2.calcHist([hsv2], [0, 1], None, [50, 60], [0, 180, 0, 256])

            cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)

            # Comparar (Correlação)
            similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            
            logger.info(f"Consistência Visual: {similarity:.2f} (Threshold: {threshold})")
            
            return similarity > threshold

        except Exception as e:
            logger.error(f"Erro na validação de consistência: {e}")
            return True # Falha aberta para não travar fluxo
