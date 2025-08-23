#!/bin/bash

# Script seguro para publicar no PyPI

# Verifica se .env existe
if [ ! -f .env ]; then
    echo "❌ Arquivo .env não encontrado!"
    echo "Crie um arquivo .env com: PYPI_TOKEN=seu-token-aqui"
    exit 1
fi

# Carrega o token do .env
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=$(grep PYPI_TOKEN .env | cut -d'=' -f2)

# Limpa builds anteriores
rm -rf dist/ build/ *.egg-info

# Build
echo "📦 Building package..."
python -m build

# Pergunta confirmação
echo "🚀 Pronto para publicar no PyPI?"
read -p "Continuar? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Publicação cancelada"
    exit 1
fi

# Upload
echo "📤 Uploading to PyPI..."
python -m twine upload dist/*

echo "✅ Publicado com sucesso!"
