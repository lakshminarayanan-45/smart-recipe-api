#!/usr/bin/env bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Build Vite frontend
cd Frontend
npm install
npm run build

# Move built files
cd ..
mkdir -p templates static
cp dist/index.html templates/
cp -r dist/assets static/
