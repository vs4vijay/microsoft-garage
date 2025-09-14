@echo off
REM 🚁 Drone Command Center - Windows Setup Script

echo 🚁 Setting up Drone Command Center...
echo ==================================

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
) else (
    echo ✅ Python found
    python --version
)

REM Create virtual environment (optional but recommended)
echo 📦 Creating virtual environment...
python -m venv drone_env
call drone_env\Scripts\activate

REM Install dependencies
echo 📥 Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements_streamlit.txt

REM Check for environment file
if not exist ".env" (
    echo ⚙️ Creating environment file template...
    (
        echo # Azure OpenAI Configuration
        echo AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
        echo AZURE_OPENAI_API_KEY=your-api-key-here
        echo AZURE_OPENAI_REALTIME_DEPLOYMENT=gpt-4o-realtime-preview
        echo.
        echo # Optional: Drone specific settings
        echo DRONE_CONNECTION_TIMEOUT=30
        echo DRONE_MAX_HEIGHT=200
        echo DRONE_MAX_DISTANCE=100
    ) > .env
    echo 📝 Please edit .env file with your Azure OpenAI credentials
)

REM Create run script
echo 🚀 Creating run script...
(
    echo @echo off
    echo echo 🚁 Starting Drone Command Center...
    echo call drone_env\Scripts\activate
    echo streamlit run drone_command_center.py --server.port 8501 --server.address 0.0.0.0
    echo pause
) > run_drone_center.bat

echo.
echo ✅ Setup complete!
echo.
echo 📋 Next steps:
echo 1. Edit .env file with your Azure OpenAI credentials
echo 2. For real drone mode: Power on your DJI Tello and connect to its WiFi
echo 3. Run the application:
echo    run_drone_center.bat
echo    OR
echo    streamlit run drone_command_center.py
echo.
echo 🌐 The interface will be available at: http://localhost:8501
echo.
echo 🔒 Start with 'Vision Only' mode for safe testing!
echo.
echo Happy flying! 🚁✨
pause