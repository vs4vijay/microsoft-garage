#!/bin/bash
# 🚁 Drone Command Center - Quick Setup Script

echo "🚁 Setting up Drone Command Center..."
echo "=================================="

# Check Python version
python_version=$(python3 --version 2>&1)
if [[ $? -eq 0 ]]; then
    echo "✅ Python found: $python_version"
else
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment (optional but recommended)
echo "📦 Creating virtual environment..."
python3 -m venv drone_env
source drone_env/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements_streamlit.txt

# Check for environment file
if [ ! -f ".env" ]; then
    echo "⚙️ Creating environment file template..."
    cat > .env << EOF
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_REALTIME_DEPLOYMENT=gpt-4o-realtime-preview

# Optional: Drone specific settings
DRONE_CONNECTION_TIMEOUT=30
DRONE_MAX_HEIGHT=200
DRONE_MAX_DISTANCE=100
EOF
    echo "📝 Please edit .env file with your Azure OpenAI credentials"
fi

# Create run script
echo "🚀 Creating run script..."
cat > run_drone_center.sh << 'EOF'
#!/bin/bash
echo "🚁 Starting Drone Command Center..."
source drone_env/bin/activate 2>/dev/null || echo "Virtual environment not found, using system Python"
streamlit run drone_command_center.py --server.port 8501 --server.address 0.0.0.0
EOF
chmod +x run_drone_center.sh

# System-specific setup
echo "🔧 System-specific setup..."
case "$(uname -s)" in
    Darwin*)    # macOS
        echo "🍎 macOS detected"
        echo "Installing audio dependencies..."
        if command -v brew &> /dev/null; then
            brew install portaudio
        else
            echo "⚠️ Homebrew not found. Please install portaudio manually for audio features."
        fi
        ;;
    Linux*)     # Linux
        echo "🐧 Linux detected"
        echo "Installing audio dependencies..."
        sudo apt-get update
        sudo apt-get install -y portaudio19-dev python3-pyaudio
        ;;
    CYGWIN*|MINGW*|MSYS*)     # Windows
        echo "🪟 Windows detected"
        echo "Audio dependencies should install with pip on Windows"
        ;;
esac

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your Azure OpenAI credentials"
echo "2. For real drone mode: Power on your DJI Tello and connect to its WiFi"
echo "3. Run the application:"
echo "   ./run_drone_center.sh"
echo "   OR"
echo "   streamlit run drone_command_center.py"
echo ""
echo "🌐 The interface will be available at: http://localhost:8501"
echo ""
echo "🔒 Start with 'Vision Only' mode for safe testing!"
echo ""
echo "Happy flying! 🚁✨"