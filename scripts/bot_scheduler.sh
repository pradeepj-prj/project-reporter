#!/bin/bash
# Start/stop the Discord bot.
# Usage: ./scripts/bot_scheduler.sh start|stop

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$PROJECT_DIR/data/bot.pid"

start_bot() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Bot is already running (PID $(cat "$PID_FILE"))"
        exit 0
    fi

    cd "$PROJECT_DIR"
    nohup python cli.py bot >> "$PROJECT_DIR/data/bot.log" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Bot started (PID $!)"
}

stop_bot() {
    if [ ! -f "$PID_FILE" ]; then
        echo "No PID file found — bot may not be running"
        exit 0
    fi

    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "Bot stopped (PID $PID)"
    else
        echo "Bot process $PID not found — already stopped"
    fi
    rm -f "$PID_FILE"
}

case "$1" in
    start) start_bot ;;
    stop)  stop_bot ;;
    *)     echo "Usage: $0 start|stop"; exit 1 ;;
esac
