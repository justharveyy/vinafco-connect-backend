import requests

url = "https://www.marinetraffic.com/en/vessels/736668/general"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:150.0) Gecko/20100101 Firefox/150.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-GPC": "1",
    "Alt-Used": "www.marinetraffic.com",
    "Referer": "https://www.marinetraffic.com/en/ais/details/ships/shipid:736668",
}

response = requests.get(
    url,
    headers=headers,
    timeout=30
)

print(response.status_code)
print(response.text)