#!/bin/bash. 
# Black-Box Web Intelligence - Startup Script
# Run this from anywhere to start both backend and frontend

# use this oneliner
# cd /Users/jainam/Downloads/Website_exposer/black_box_web_intel && ./start.sh
PROJECT_DIR="/Users/jainam/Downloads/Website_exposer/black_box_web_intel"

echo "🔄 Killing existing processes..."
pkill -f "uvicorn backend.api.main:app" 2>/dev/null
pkill -f "next dev" 2>/dev/null
sleep 2

echo "🚀 Starting Backend API..."
cd "$PROJECT_DIR"
source venv/bin/activate
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 3

echo "🌐 Starting Frontend..."
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Services started!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
