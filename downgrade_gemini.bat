@echo off
echo ==========================================
echo       DOWNGRADE DO GEMINI CLI
echo ==========================================
echo.
echo Este script ira retornar o Gemini CLI para a versao 0.25.2.
echo Por favor, feche qualquer janela do Gemini em execucao antes de continuar.
echo.
pause
echo.
echo Removendo versao atual...
call npm uninstall -g @google/gemini-cli
echo.
echo Instalando versao 0.25.2...
call npm install -g @google/gemini-cli@0.25.2
echo.
echo ==========================================
echo       CONCLUIDO COM SUCESSO
echo ==========================================
echo Agora voce pode reiniciar o Gemini.
pause
