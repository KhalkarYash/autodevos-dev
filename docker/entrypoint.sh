#!/usr/bin/env bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}AutoDevOS Docker Container${NC}"
echo "========================================"

# Set default prompt if not provided
PROMPT="${DEMO_PROMPT:-Build a sample app with a list and API}"

# Handle different commands
case "${1:-run}" in
    run)
        echo -e "${GREEN}Generating application...${NC}"
        python3 /app/main.py --prompt "$PROMPT" --output /app/output
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Generation failed${NC}"
            exit 1
        fi
        
        echo -e "${GREEN}Installing dependencies...${NC}"
        
        # Install backend dependencies
        if [ -f /app/output/backend/app/package.json ]; then
            echo "Installing backend dependencies..."
            cd /app/output/backend/app && npm ci
        fi
        
        # Install frontend dependencies
        if [ -f /app/output/frontend/app/package.json ]; then
            echo "Installing frontend dependencies..."
            cd /app/output/frontend/app && npm ci
        fi
        
        cd /app
        
        echo -e "${GREEN}Starting applications...${NC}"
        exec npm run dev
        ;;
    
    generate)
        echo -e "${GREEN}Generating application only...${NC}"
        python3 /app/main.py --prompt "$PROMPT" --output /app/output
        ;;
    
    test)
        echo -e "${GREEN}Running tests...${NC}"
        pytest /app/tests
        ;;
    
    bash)
        exec /bin/bash
        ;;
    
    *)
        echo "Usage: $0 {run|generate|test|bash}"
        exit 1
        ;;
esac
