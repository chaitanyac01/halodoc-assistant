#!/bin/bash

echo "🏥 Halodoc Homecare AI Assistant - Quick Start"
echo "=============================================="

# Check Python version
python_version=$(python3 --version 2>&1)
if [[ $? -ne 0 ]]; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+"
    exit 1
fi
echo "✅ $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip first
echo "🔧 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Verify installation
echo "✅ Verifying installation..."
python setup_check.py

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/faq_documents
mkdir -p logs

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env and add your Google API key"
    echo "   Run 'nano .env' or open in your editor"
    exit 1
fi

# Check if API key is set
if grep -q "your_google_api_key_here" .env; then
    echo "❌ Please set your Google API key in .env file"
    exit 1
fi

# Check for FAQ documents
pdf_count=$(find data/faq_documents -name "*.pdf" 2>/dev/null | wc -l)
if [ $pdf_count -eq 0 ]; then
    echo "⚠️  No PDF documents found in data/faq_documents/"
    echo "   Please add your FAQ PDF files to enable RAG features"
fi

echo ""
echo "✨ Setup complete! Starting Halodoc AI Assistant..."
echo ""

# Run the assistant
python main.py