import subprocess
import json
from datetime import datetime

def get_clients():
    try:
        result = subprocess.check_output(
            ["hyprctl", "clients", "-j"]
        )

        clients = json.loads(result)

        windows = []

        for c in clients:
            windows.append({
                "class": c.get("class", ""),
                "title": c.get("title", ""),
                "workspace": c.get("workspace", {}).get("id", -1),
                "pid": c.get("pid", 0),
                "fullscreen": c.get("fullscreen", False)
            })

        return windows

    except Exception as e:
        print(f"[HYPRLAND CLIENT ERROR] {e}")
        return []


def get_active_window():
    try:
        result = subprocess.check_output(
            ["hyprctl", "activewindow", "-j"]
        )

        data = json.loads(result)

        return {
            "class": data.get("class", ""),
            "title": data.get("title", ""),
            "workspace": data.get("workspace", {}).get("id", -1),
            "pid": data.get("pid", 0),
            "fullscreen": data.get("fullscreen", False)
        }

    except Exception as e:
        print(f"[ACTIVE WINDOW ERROR] {e}")
        return {}


def get_context():

    now = datetime.now()

    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),

        "active_window": get_active_window(),

        "windows": get_clients()
    }

if __name__ == "__main__":
    context = get_context()

    print(json.dumps(context, indent=2))
