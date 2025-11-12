#!/bin/bash
# Startup script for AutoDevOS FastAPI Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting AutoDevOS FastAPI Server${NC}"
echo "================================================"

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv_pyinstaller" ]; then
    echo -e "${YELLOW}⚠️  No virtual environment found. Creating one...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    # Activate virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo -e "${GREEN}✓ Activated 'venv'${NC}"
    else
        source .venv_pyinstaller/bin/activate
        echo -e "${GREEN}✓ Activated '.venv_pyinstaller'${NC}"
    fi
fi

# Check if requirements are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing dependencies...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Dependencies already installed${NC}"
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Please create one from .env.example${NC}"
    echo "   cp .env.example .env"
    echo "   Then edit .env and add your GEMINI_API_KEY"
fi

# Load environment variables if .env exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
fi

# Get port from environment or use default
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo ""
echo "================================================"
echo -e "${GREEN}Server Configuration:${NC}"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo ""
echo "  API Documentation:"
echo "  • Swagger UI: http://localhost:$PORT/docs"
echo "  • ReDoc:      http://localhost:$PORT/redoc"
echo "  • Health:     http://localhost:$PORT/health"
echo "================================================"
echo ""

# Start the server
echo -e "${GREEN}🌐 Starting server...${NC}"
exec uvicorn main:app --host "$HOST" --port "$PORT" --reload
