@echo off
chcp 65001 > nul
echo Iniciando Ferramenta de Ditado Jarvis...
echo Certifique-se de clicar na janela onde deseja ditar apos o inicio.
echo.
python tools/dictation_tool.py
pause
