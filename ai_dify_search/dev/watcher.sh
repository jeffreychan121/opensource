#!/bin/bash
# Odoo Auto-Restart Watcher for ai_dify_search module
# Usage: ./watcher.sh [module_path]

MODULE_PATH="${1:-/Users/chan/Henson/odoo/oscg/yzl_addons/ai_dify_search}"
ODOO_DIR="/Users/chan/Henson/odoo"
ODOO_CMD="./venv310/bin/python ./odoo-bin -c debian/odoo.conf -d odoo17"

echo "Watching: $MODULE_PATH"
echo "Press Ctrl+C to stop"

# Kill existing Odoo on port 8069
kill_odoo() {
    PID=$(lsof -i :8069 2>/dev/null | grep LISTEN | awk '{print $2}' | head -1)
    if [ -n "$PID" ]; then
        echo "Killing Odoo (PID: $PID)..."
        kill $PID 2>/dev/null
        sleep 2
    fi
}

# Upgrade module and restart
upgrade_and_run() {
    echo "[$(date)] Change detected, upgrading module..."
    cd "$ODOO_DIR"

    # Kill existing Odoo
    kill_odoo

    # Upgrade module
    ./venv310/bin/python ./odoo-bin -c debian/odoo.conf -d odoo17 -u ai_dify_search --stop-after-init
    echo "[$(date)] Module upgraded"

    # Start Odoo in background
    nohup ./venv310/bin/python ./odoo-bin -c debian/odoo.conf -d odoo17 > /tmp/odoo.log 2>&1 &
    echo "[$(date)] Odoo started, PID: $!"
}

# Use fswatch (macOS) or inotifywait (Linux)
if command -v fswatch &> /dev/null; then
    # macOS
    fswatch -r "$MODULE_PATH" | while read -r; do
        upgrade_and_run
    done
elif command -v inotifywait &> /dev/null; then
    # Linux
    inotifywait -r -e modify "$MODULE_PATH" | while read -r; do
        upgrade_and_run
    done
else
    # Fallback: simple polling every 5 seconds
    LAST_MOD=""
    while true; do
        CURRENT_MOD=$(find "$MODULE_PATH" -type f -name "*.py" -o -name "*.xml" -o -name "*.js" 2>/dev/null | xargs stat -f "%m" 2>/dev/null | sort -n | tail -1)
        if [ "$CURRENT_MOD" != "$LAST_MOD" ] && [ -n "$LAST_MOD" ]; then
            upgrade_and_run
        fi
        LAST_MOD="$CURRENT_MOD"
        sleep 5
    done
fi
