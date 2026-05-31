#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=3000
BACKEND_LOG="$ROOT_DIR/backend.log"
FRONTEND_LOG="$ROOT_DIR/frontend.log"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

find_listening_pids() {
  lsof -tiTCP:"$1" -sTCP:LISTEN || true
}

find_command_pids() {
  pgrep -f "$1" || true
}

kill_port() {
  local port="$1"
  local pids
  pids="$(find_listening_pids "$port")"
  if [[ -n "$pids" ]]; then
    echo "Killing process(es) on port $port: $pids"
    kill -9 $pids
  fi
}

kill_command() {
  local pattern="$1"
  local pids
  pids="$(find_command_pids "$pattern")"
  if [[ -n "$pids" ]]; then
    echo "Killing command process(es) matching '$pattern': $pids"
    kill -9 $pids
  fi
}

if ! command_exists lsof; then
  echo "Error: lsof is required to detect listening ports. Install it and retry."
  exit 1
fi

if ! command_exists python3; then
  echo "Error: python3 is required. Install Python 3 and retry."
  exit 1
fi

npm_cmd="npm"
if ! command_exists npm; then
  if [[ -x "/opt/homebrew/bin/npm" ]]; then
    npm_cmd="/opt/homebrew/bin/npm"
  fi
fi

if ! command_exists "$npm_cmd"; then
  echo "Error: npm is required. Install npm or use Homebrew node."
  exit 1
fi

if ! command_exists node; then
  echo "Error: node is required. Install Node.js and retry."
  exit 1
fi

printf "Stopping any processes on ports %s and %s...\n" "$BACKEND_PORT" "$FRONTEND_PORT"
kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"

# Also kill stale backend/frontend processes that may not be actively listening anymore.
kill_command "uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT"
kill_command "npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT"
kill_command "vite --host 0.0.0.0 --port $FRONTEND_PORT"

printf "Starting backend on port %s...\n" "$BACKEND_PORT"
cd "$ROOT_DIR/backend"
nohup python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" > "$BACKEND_LOG" 2>&1 &
backend_pid=$!

printf "Starting frontend on port %s...\n" "$FRONTEND_PORT"
cd "$ROOT_DIR/frontend"
nohup "$npm_cmd" run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
frontend_pid=$!

printf "\nStarted backend PID=%s and frontend PID=%s\n" "$backend_pid" "$frontend_pid"
printf "Backend logs: %s\n" "$BACKEND_LOG"
printf "Frontend logs: %s\n" "$FRONTEND_LOG"
printf "Open http://localhost:%s/ in your browser.\n" "$FRONTEND_PORT"
