#!/bin/sh
# Start the API server in the background, then run the agent investigation.
# After the investigation completes the API stays alive so the UI can read
# results from the local cache until the container is stopped.
set -e

echo "[entrypoint] Starting API server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "[entrypoint] Running investigation agent..."
python -m agent.main
AGENT_EXIT=$?

echo "[entrypoint] Agent finished (exit=$AGENT_EXIT). API remains up for result queries."
wait $API_PID
