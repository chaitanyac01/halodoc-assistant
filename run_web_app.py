#!/usr/bin/env python3
"""
Script to run the Halodoc Homecare Assistant Streamlit web app
"""

import subprocess
import sys
import os

def main():
    """Run the Streamlit web app"""
    try:
        # Check if we're in the right directory
        if not os.path.exists("app.py"):
            print("❌ app.py not found. Please run this script from the project root directory.")
            sys.exit(1)
        
        print("🚀 Starting Halodoc Homecare Assistant Web App...")
        print("📱 The app will open in your default web browser")
        print("🔗 URL: http://localhost:8501")
        print("\n💡 Press Ctrl+C to stop the server\n")
        
        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ])
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down the web app. Goodbye!")
    except Exception as e:
        print(f"❌ Error running the web app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
