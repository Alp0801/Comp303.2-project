import requests
import time
import logging
from flask import Flask, jsonify, request, render_template_string
from datetime import datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


API_KEY = "23005d9ad6a0c145d2cd791af1500b4e"
BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"

DAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
CITIES = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana", "Konya", "Gaziantep", "Kayseri", "Trabzon"]


CACHE = {}
CACHE_TTL = 900



def get_weather_data(city):
    now = time.time()

    
    if city in CACHE and (now - CACHE[city]["time"]) < CACHE_TTL:
        return CACHE[city]["data"]

    params = {
        "q": city,
        "units": "metric",
        "lang": "tr",
        "appid": API_KEY
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error(f"Hata: {e}")
        return {"error": "Hava durumu verisi alınamadı."}

    forecast = []
    seen_days = set()

   
    for item in data.get("list", []):
        dt_object = datetime.fromtimestamp(item["dt"])
        day_name = DAYS_TR[dt_object.weekday()]
        hour = dt_object.hour

        if day_name not in seen_days and (11 <= hour <= 14):
            forecast.append({
                "day": day_name,
                "temp": round(item["main"]["temp"]),
                "weather": item["weather"][0]["description"].capitalize(),
                "icon": item["weather"][0]["icon"]
            })
            seen_days.add(day_name)

        if len(forecast) == 5: break

    if forecast:
        CACHE[city] = {"time": now, "data": forecast}
        return forecast
    return {"error": "Veri işlenemedi."}



@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, cities=CITIES)


@app.route("/api/weather")
def api_weather():
    city = request.args.get("city", "Istanbul").strip()
    data = get_weather_data(city)
    if isinstance(data, dict) and "error" in data:
        return jsonify(data), 400
    return jsonify(data)



HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Haftalık Akıllı Kombin Asistanı</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #4f46e5;
            --bg-grad: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        body { margin: 0; font-family: 'Inter', sans-serif; background: var(--bg-grad); min-height: 100vh; color: #333; }
        .container { max-width: 1000px; margin: 40px auto; background: rgba(255,255,255,0.95); border-radius: 30px; padding: 40px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
        h1 { text-align: center; color: #1e293b; font-size: 2rem; margin-bottom: 30px; }

        .controls { display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-bottom: 30px; }
        select, button { padding: 12px 20px; border-radius: 15px; border: 1px solid #ddd; font-size: 1rem; outline: none; transition: 0.3s; }
        button { background: var(--primary); color: white; border: none; cursor: pointer; font-weight: 600; }
        button:hover { background: #4338ca; transform: translateY(-2px); }

        .week-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .day-card { background: white; border-radius: 20px; padding: 20px; text-align: center; border: 1px solid #f0f0f0; transition: 0.4s; }
        .day-card:hover { transform: scale(1.05); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
        .day-card img { width: 64px; height: 64px; }
        .temp { font-size: 2rem; font-weight: 800; color: #1e293b; margin: 10px 0; }
        .day-name { font-weight: 600; color: #64748b; text-transform: uppercase; font-size: 0.85rem; }

        .outfit-section { background: #f8fafc; border-radius: 25px; padding: 30px; display: none; border-left: 8px solid var(--primary); }
        .outfit-card { background: white; margin-bottom: 10px; padding: 15px 20px; border-radius: 15px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .outfit-card b { color: var(--primary); min-width: 100px; display: inline-block; }
        .tag-sick { background: #fee2e2; color: #dc2626; padding: 2px 8px; border-radius: 5px; font-size: 0.8rem; margin-left: 10px; }
    </style>
</head>
<body>

<div class="container">
    <h1>👔 Akıllı Kombin Asistanı</h1>

    <div class="controls">
        <select id="citySelect">
            {% for city in cities %}
            <option value="{{ city }}">{{ city }}</option>
            {% endfor %}
        </select>

        <select id="sickStatus">
            <option value="no">Sağlıklıyım</option>
            <option value="yes">Hastayım / Halsizim</option>
        </select>

        <button onclick="fetchWeather()">Kombinleri Hazırla</button>
    </div>

    <div class="week-grid" id="weatherDisplay"></div>

    <div class="outfit-section" id="outfitSection">
        <h2 style="margin-top:0">📋 Günlük Stil Önerilerin</h2>
        <div id="outfitList"></div>
    </div>
</div>

<script>
async function fetchWeather() {
    const city = document.getElementById("citySelect").value;
    const isSick = document.getElementById("sickStatus").value === "yes";
    const weatherDisplay = document.getElementById("weatherDisplay");
    const outfitList = document.getElementById("outfitList");
    const outfitSection = document.getElementById("outfitSection");

    try {
        const res = await fetch(`/api/weather?city=${city}`);
        const data = await res.json();

        if(data.error) return alert(data.error);

        weatherDisplay.innerHTML = "";
        outfitList.innerHTML = "";
        outfitSection.style.display = "block";

        data.forEach(day => {
            // Hava Durumu Kartları
            weatherDisplay.innerHTML += `
                <div class="day-card">
                    <div class="day-name">${day.day}</div>
                    <img src="https://openweathermap.org/img/wn/${day.icon}@2x.png" alt="icon">
                    <div class="temp">${day.temp}°C</div>
                    <div style="font-size:0.9rem; color:#667eea">${day.weather}</div>
                </div>
            `;

            // Kombin Mantığı
            let suggestion = "";
            if(day.temp < 7) suggestion = "Termal içlik, kalın yün kazak, kaban ve bot";
            else if(day.temp < 14) suggestion = "Kardigan veya hafif ceket, uzun kollu tişört, kanvas pantolon";
            else if(day.temp < 21) suggestion = "İnce bir sweatshirt veya denim ceket, spor ayakkabı";
            else suggestion = "Pamuklu tişört, şort veya ince pantolon, sandalet/hafif ayakkabı";

            if(day.weather.toLowerCase().includes("yağmur")) suggestion += " ☔ (Yağmurluk ve şemsiye almalısın!)";
            if(isSick) suggestion += ' <span class="tag-sick">+ Ekstra atkı/bere</span>';

            outfitList.innerHTML += `
                <div class="outfit-card">
                    <span><b>${day.day}:</b> ${suggestion}</span>
                </div>
            `;
        });
    } catch (err) {
        alert("Bağlantı hatası oluştu.");
    }
}
</script>

</body>
</html>
"""

if __name__ == "__main__":

    app.run(debug=True)
