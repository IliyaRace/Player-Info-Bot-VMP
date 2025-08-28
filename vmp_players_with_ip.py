import requests

SERVER_IP = "5.42.217.217"
SERVER_PORT = 30120

def get_vmp_players():
    """
    اطلاعات پلیرهای متصل به سرور VMP را با API دریافت می‌کند.
    فرض شده API در آدرس زیر موجود است:
    http://SERVER_IP:SERVER_PORT/players.json
    """
    url = f"http://{SERVER_IP}:{SERVER_PORT}/players.json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            players = response.json()
            return players
        else:
            return []
    except Exception as e:
        print(f"خطا در دریافت لیست بازیکنان: {e}")
        return []