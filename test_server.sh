#!/bin/bash
source .venv/bin/activate
export PYTHONPATH=./src
uvicorn --factory src.vortex.api.main:create_app --port 8000 > server.log 2>&1 &
SERVER_PID=$!
sleep 5
python examples/simple_chain.py
kill $SERVER_PID
