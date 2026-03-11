#!/bin/bash
# Tatva.ai - Quick Start Script

echo "🎙️  Tatva.ai - Starting up..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running in Docker
if [ "$1" == "docker" ]; then
    echo -e "${BLUE}Starting with Docker...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker not found. Please install Docker first.${NC}"
        exit 1
    fi
    
    docker-compose up --build
    exit 0
fi

# Python setup
echo -e "${BLUE}Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 not found. Please install Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Check for virtual environment
if [ ! -d "backend/venv" ]; then
    echo ""
    echo -e "${BLUE}Creating virtual environment...${NC}"
    cd backend
    python3 -m venv venv
    cd ..
fi

# Activate virtual environment
source backend/venv/bin/activate

# Install dependencies
echo ""
echo -e "${BLUE}Installing dependencies...${NC}"
cd backend
pip install -q -r requirements.txt
cd ..

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create directories
mkdir -p backend/uploads backend/transcripts

# Download Whisper model (first run)
echo ""
echo -e "${YELLOW}Note: First run will download Whisper model (~244MB)${NC}"

# Start backend
echo ""
echo -e "${BLUE}Starting backend server...${NC}"
cd backend
python3 -c "import whisper; whisper.load_model('small')" 2>/dev/null || echo "Model will download on first request..."

python3 main.py &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
cd ..

# Wait for backend
echo ""
echo -e "${BLUE}Waiting for backend to be ready...${NC}"
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Backend starting... (may take a moment)${NC}"
fi

# Start frontend
echo ""
echo -e "${BLUE}Starting frontend...${NC}"
cd frontend
python3 -m http.server 3000 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
cd ..

echo ""
echo "═══════════════════════════════════════════"
echo -e "${GREEN}🚀 Tatva.ai is running!${NC}"
echo "═══════════════════════════════════════════"
echo ""
echo -e "📱 Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "⚙️  Backend: ${BLUE}http://localhost:8000${NC}"
echo -e "📚 API Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Keep script running
wait
