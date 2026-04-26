#!/usr/bin/env python3
"""
Odoo Auto-Restart Watcher for ai_dify_search module
Usage: python auto_restart.py [module_path]

Requires: pip install watchdog
"""

import sys
import time
import subprocess
import signal
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

MODULE_PATH = sys.argv[1] if len(sys.argv) > 1 else "/Users/chan/Henson/odoo/oscg/yzl_addons/ai_dify_search"
ODOO_DIR = "/Users/chan/Henson/odoo"
ODOO_PID = None


def kill_odoo():
    """Kill existing Odoo process on port 8069"""
    global ODOO_PID
    try:
        result = subprocess.run(
            ["lsof", "-i", ":8069", "-t"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            pid = int(result.stdout.strip().split()[0])
            print(f"Killing Odoo (PID: {pid})...")
            subprocess.run(["kill", str(pid)])
            time.sleep(2)
    except Exception as e:
        print(f"Error killing Odoo: {e}")


def upgrade_and_run():
    """Upgrade module and restart Odoo"""
    global ODOO_PID
    print(f"[{time.strftime('%H:%M:%S')}] Change detected, upgrading module...")

    # Kill existing Odoo
    kill_odoo()

    # Upgrade module
    print("Upgrading module...")
    subprocess.run(
        ["./venv310/bin/python", "./odoo-bin", "-c", "debian/odoo.conf",
         "-d", "odoo17", "-u", "ai_dify_search", "--stop-after-init"],
        cwd=ODOO_DIR,
        capture_output=True
    )
    print(f"[{time.strftime('%H:%M:%S')}] Module upgraded")

    # Start Odoo
    print("Starting Odoo...")
    process = subprocess.Popen(
        ["./venv310/bin/python", "./odoo-bin", "-c", "debian/odoo.conf", "-d", "odoo17"],
        cwd=ODOO_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    ODOO_PID = process.pid
    print(f"[{time.strftime('%H:%M:%S')}] Odoo started, PID: {ODOO_PID}")


class ChangeHandler(FileSystemEventHandler):
    """Handle file system changes"""

    def __init__(self):
        super().__init__()
        self.last_reload = 0

    def on_any_event(self, event):
        # Only process Python, XML, JS files
        if event.is_directory:
            return
        ext = Path(event.src_path).suffix
        if ext not in ('.py', '.xml', '.js', '.scss'):
            return

        # Debounce: only reload once per 3 seconds
        now = time.time()
        if now - self.last_reload < 3:
            return
        self.last_reload = now

        print(f"[{time.strftime('%H:%M:%S')}] File changed: {event.src_path}")
        upgrade_and_run()


if __name__ == "__main__":
    print(f"Watching: {MODULE_PATH}")
    print("Press Ctrl+C to stop")

    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, MODULE_PATH, recursive=True)
    observer.start()

    # Initial startup
    upgrade_and_run()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        kill_odoo()
        observer.stop()
    observer.join()
