@echo off
title Jarvis Video Maker - V12 Ultra
cls

echo ========================================================
echo        JARVIS - AUTOMACAO DE VIDEO SEQUENCIAL
echo ========================================================
echo.

:: Verifica se o Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado! Instale o Python e adicione ao PATH.
    pause
    exit
)

:: Instala dependencias silenciosamente
echo [1/3] Verificando dependencias...
pip install -r requirements.txt --quiet

:: Garante que o Playwright esta pronto
echo [2/3] Verificando navegadores (Playwright)...
python -m playwright install chromium

echo [3/3] Iniciando automacao...
echo.
echo DICA: Quando o navegador abrir, certifique-se de estar logado na Meta AI.
echo.

python run_video_maker.py

echo.
echo ========================================================
echo Processo Finalizado.
echo ========================================================
pause
