#!/usr/bin/env python3
"""
Setup verification script for Halodoc Homecare Assistant
Run this to check if everything is properly configured
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Check Python version"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Need Python 3.8+")
        return False

def check_packages():
    """Check required packages"""
    print("\n📦 Checking required packages...")
    
    required_packages = {
        'google.generativeai': 'google-generativeai',
        'chromadb': 'chromadb', 
        'rich': 'rich',
        'prompt_toolkit': 'prompt-toolkit',
        'dotenv': 'python-dotenv',
        'loguru': 'loguru',
        'pydantic': 'pydantic',
        'pydantic_settings': 'pydantic-settings',
        'sentence_transformers': 'sentence-transformers',
        'PyPDF2': 'PyPDF2',
        'pdfplumber': 'pdfplumber'
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing.append(package)
    
    return missing

def check_env_file():
    """Check .env file configuration"""
    print("\n🔧 Checking configuration...")
    
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        print("   Copy .env to .env and configure")
        return False
    
    with open('.env', 'r') as f:
        content = f.read()
        
    if 'your_google_api_key_here' in content:
        print("❌ Google API key not configured")
        print("   Edit .env and set GOOGLE_API_KEY")
        return False
    
    if 'GOOGLE_API_KEY' not in content:
        print("❌ GOOGLE_API_KEY not found in .env")
        return False
    
    print("✅ .env file configured")
    return True

def check_directories():
    """Check required directories"""
    print("\n📁 Checking directories...")
    
    dirs = ['data/faq_documents', 'logs', 'src/core', 'src/agents', 'src/services']
    all_good = True
    
    for dir_path in dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path} - missing")
            all_good = False
    
    return all_good

def check_faq_documents():
    """Check for FAQ documents"""
    print("\n📄 Checking FAQ documents...")
    
    faq_dir = Path('data/faq_documents')
    if not faq_dir.exists():
        print("❌ FAQ documents directory not found")
        return False
    
    pdf_files = list(faq_dir.glob('*.pdf'))
    if not pdf_files:
        print("⚠️  No PDF files found in data/faq_documents/")
        print("   The system will work but with limited FAQ capabilities")
        return True
    
    print(f"✅ Found {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"   📄 {pdf.name}")
    
    return True

def main():
    """Main setup check"""
    print("🏥 Halodoc Homecare Assistant - Setup Check")
    print("=" * 50)
    
    all_checks = []
    
    # Run all checks
    all_checks.append(check_python_version())
    
    missing_packages = check_packages()
    all_checks.append(len(missing_packages) == 0)
    
    all_checks.append(check_env_file())
    all_checks.append(check_directories()) 
    all_checks.append(check_faq_documents())
    
    print("\n" + "=" * 50)
    
    if all(all_checks):
        print("🎉 All checks passed! You're ready to run the assistant.")
        print("\n🚀 Start the assistant with:")
        print("   python main.py")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        
        if missing_packages:
            print("\n📦 To install missing packages:")
            print("   pip install -r requirements.txt")
            print("\n🔧 Or use the quickstart script:")
            print("   ./quickstart.sh")
    
    print("\n📚 Need help? Check README.md or GUIDE.md")

if __name__ == "__main__":
    main()