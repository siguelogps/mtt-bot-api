#!/usr/bin/env bash
set -o errexit

echo "Instalando dependencias de Python..."
pip install -r requirements.txt

echo "Forzando la descarga de Google Chrome..."
STORAGE_DIR=/opt/render/project/.render

# El botón nuclear del caché: borramos la carpeta corrupta
rm -rf $STORAGE_DIR/chrome

# Creamos la carpeta limpia y descargamos
mkdir -p $STORAGE_DIR/chrome
cd $STORAGE_DIR/chrome
wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -x ./google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome
rm ./google-chrome-stable_current_amd64.deb
