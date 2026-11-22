"""One user-initiated request, fixed HTTPS host, no redirects or location lookup."""
from http.client import HTTPSConnection, HTTPException
import json
import math
from datetime import datetime, timezone


def forecast(consent, lat, lon):
    if consent is not True:
        raise ValueError("Hava durumu için izin gerekli.")
    for coord, limit in ((lat, 90), (lon, 180)):
        if type(coord) not in (int, float) or not -limit <= coord <= limit:
            raise ValueError("Geçerli enlem ve boylam gir.")
    conn = HTTPSConnection("api.open-meteo.com", timeout=6)
    try:
        conn.request("GET", f"/v1/forecast?latitude={lat:.3f}&longitude={lon:.3f}"
                     "&current=temperature_2m,weather_code&timeformat=unixtime")
        reply = conn.getresponse()
        if reply.status != 200:
            raise ValueError()
        record = json.loads(reply.read(16384))["current"]
        temp, code = record["temperature_2m"], record["weather_code"]
        if not math.isfinite(temp) or type(code) != int:
            raise ValueError()
        conditions = {0:"Açık", 1:"Az bulutlu", 2:"Parçalı bulutlu", 3:"Bulutlu",
                      45:"Sisli", 48:"Sisli"}
        label = conditions.get(code)
        if not label:
            if code in (71,73,75,77,85,86): label = "Karlı"
            elif code in (95,96,99): label = "Gök gürültülü"
            elif code in (51,53,55,56,57,61,63,65,66,67,80,81,82): label = "Yağışlı"
            else: label = f"Hava kodu {code}"
        date = datetime.fromtimestamp(record["time"], timezone.utc).astimezone()
        symbol = "☀" if code == 0 else "☁" if code <= 48 else "❄" if "Karlı" == label else "☂"
        return {"label": f"{symbol} {temp:g} °C · {label} · {date:%d.%m %H:%M} · Open-Meteo"}
    except (OSError, HTTPException, ValueError, KeyError, TypeError, OverflowError):
        raise ValueError("Open-Meteo verisi alınamadı. İnternet bağlantısını kontrol et.") from None
    finally:
        conn.close()
