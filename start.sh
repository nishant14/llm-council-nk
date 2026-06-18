#!/bin/bash

# LLM Council - Start script

export PATH="$HOME/.local/bin:$PATH"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "Starting LLM Council..."
echo ""

# Start backend
echo "Starting backend on http://localhost:8001..."
uv run python -m backend.main &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 2

# Start frontend
echo "Starting frontend on http://localhost:5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "✓ LLM Council is running!"
echo "  Backend:  http://localhost:8001 (or http://$LOCAL_IP:8001)"
echo "  Frontend: http://localhost:5173 (or http://$LOCAL_IP:5173)"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
