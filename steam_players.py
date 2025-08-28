import json
import os

PLAYERS_DATA_FILE = "players_data.json" # Bara File Player Ha

def get_player_job_and_gang(steam_hex):
    """
    از steam_hex (شناسه استیم) برای پیدا کردن شغل و گروه بازیکن در فایل JSON استفاده می‌کنیم.
    """
    if not os.path.exists(PLAYERS_DATA_FILE):
        return {
            "job": "Unknown",
            "job_grade": "N/A",
            "gang": "Unknown",
            "gang_grade": "N/A"
        }

    with open(PLAYERS_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    player = data.get(steam_hex.lower())
    if not player:
        return {
            "job": "Unknown",
            "job_grade": "N/A",
            "gang": "Unknown",
            "gang_grade": "N/A"
        }

    return {
        "job": player.get("job", "Unknown"),
        "job_grade": player.get("job_grade", "N/A"),
        "gang": player.get("gang", "Unknown"),
        "gang_grade": player.get("gang_grade", "N/A")
    }
