@echo off
title Sistema de Stock - Servidor Local
cd /d "%~dp0"

echo ========================================
echo   Sistema de Control de Stock y Ventas
echo ========================================
echo.
echo Iniciando servidor local en http://localhost:8000
echo.
echo Para detener el servidor, cerra esta ventana o presiona Ctrl+C
echo.

start "" "http://localhost:8000/sistema_compartido.html"

python -m http.server 8000
