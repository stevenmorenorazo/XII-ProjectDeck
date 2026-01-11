#!/bin/bash
# Start server accessible on local network
echo "Starting server on 0.0.0.0:8000..."
echo "Accessible on your local network at: http://$(ipconfig getifaddr en0 2>/dev/null || hostname -I | awk '{print $1}'):8000"
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
