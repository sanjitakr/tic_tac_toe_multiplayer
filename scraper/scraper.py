import requests
from config import REQUEST_TIMEOUT

def fetch_image(url):
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            return response.content
        else:
            print(f"[HTTP ERROR] {url} → {response.status_code}")
            return None

    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] {url}")
    except requests.exceptions.RequestException as e:
        print(f"[REQUEST ERROR] {url}: {e}")

    return None