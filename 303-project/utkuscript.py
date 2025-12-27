import requests, time
import json
from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
from google import genai
from google.genai import types

app = Flask(__name__)

# --- AYARLAR ---
WEATHER_API_KEY = "23005d9ad6a0c145d2cd791af1500b4e"
GEMINI_API_KEY = "AIzaSyCqRsosX5CLQ1vgVoWoDJ9PAMCkggvJ0cQ"

DAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
CITIES = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana", "Konya", "Gaziantep", "Kayseri", "Trabzon"]


CACHE = {}
CACHE_TTL = 600


# --- GEMINI
def get_gemini_suggestion(sicaklik, durum, gun,is_sick):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        ekstra_hasta = ""
        if is_sick:
            ekstra_hasta = "DİKKAT: Kullanıcı hasta. Lütfen kalın, rahat, boğazı koruyan ve sıcak tutan şeyler öner. Şıklıktan çok sağlığa odaklan."

        prompt = f"""
        Sen bir stilist ve moda asistanısın.
        Gün: {gun}, Hava: {sicaklik} derece ve {durum}.

        GÖREV:
        Bu hava durumu için 3 farklı, modern kıyafet kombini öner.

        ÖNEMLİ KURAL:
        Cevabı SADECE aşağıdaki JSON formatında ver. Başka hiçbir açıklama yazma.
        {{
            "kutu1": "Birinci öneri (Kısa ve net)",
            "kutu2": "İkinci öneri (Kısa ve net)",
            "kutu3": "Üçüncü öneri (Kısa ve net)"
        }}
        """

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print("Gemini Hatası:", e)
        return {
            "kutu1": "Hata oluştu.",
            "kutu2": "Lütfen tekrar dene.",
            "kutu3": "Bağlantı sorunu."
        }


# --- ENDPOINTS ---

def get_weather(city):
    now = time.time()
    if city in CACHE and now - CACHE[city]["time"] < CACHE_TTL:
        return CACHE[city]["data"]

    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&lang=tr&appid={WEATHER_API_KEY}"
    data = requests.get(url).json()

    if "list" not in data:
        return {"error": "Şehir bulunamadı"}

    forecast, used = [], set()
    for item in data["list"]:
        date = datetime.fromtimestamp(item["dt"])
        day = DAYS_TR[date.weekday()]
        if day not in used:
            forecast.append({
                "day": day,
                "temp": round(item["main"]["temp"]),
                "weather": item["weather"][0]["description"].capitalize()
            })
            used.add(day)
        if len(forecast) == 7: break

    CACHE[city] = {"time": now, "data": forecast}
    return forecast


@app.route("/api/weather")
def api_weather():
    city = request.args.get("city", "Istanbul")
    return jsonify(get_weather(city))


@app.route("/api/kombin-iste", methods=["POST"])
def api_kombin():
    data = request.json
    hasta_durumu = data.get('sick', False)
    # Frontend'den gelen verileri alıyoruz
    sonuc = get_gemini_suggestion(data['temp'], data['weather'], data['day'],hasta_durumu)
    return jsonify(sonuc)


# --- HTML ---
HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>AI Stil Asistanı</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body{margin:0;font-family:'Segoe UI',sans-serif;background:linear-gradient(120deg,#6a7cf7,#7f6ae6);}
.container{max-width:1500px;margin:30px auto;background:#fff;border-radius:24px;padding:30px;}
h1{text-align:center;margin-bottom:20px}
.controls{display:flex;justify-content:center;gap:12px;margin-bottom:25px;}
select,button{padding:10px 14px;border-radius:12px;border:1px solid #ddd;}
.main-btn{background:#4CAF50;color:white;cursor:pointer;border:none;}
.week{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;}
.day-card{background:#f4f6f8;border-radius:18px;padding:18px;text-align:center;transition:.3s;}
.day-card:hover{transform:translateY(-5px);box-shadow:0 10px 20px rgba(0,0,0,.1);}
.icon{font-size:36px;}
.temp{font-size:28px;font-weight:700}

/* KOMBİN BÖLÜMÜ */
.outfits{margin-top:35px;background:#ecfdf3;border-radius:22px;padding:25px;display:none;}
.outfit-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:20px;}
.day-select-btn{
  width:100%;padding:15px;background:white;border:2px solid #eee;
  border-radius:12px;font-weight:bold;cursor:pointer;transition:.2s;
}
.day-select-btn:hover{background:#6a7cf7;color:white;border-color:#6a7cf7;}

/* DETAY KUTULARI */
.details-section{display:flex;gap:20px;justify-content:space-between;flex-wrap:wrap;}
.detail-box{
  flex:1;min-width:250px;
  background:white;border-radius:15px;padding:20px;
  text-align:center;box-shadow:0 4px 12px rgba(0,0,0,0.05);border:1px solid #eee;
}
.loading {color: #666; font-style: italic;}
</style>
</head>
<body>
<div class="container">
<h1>🌤️ AI Stil Asistanı</h1>

<div class="controls">
<select id="city"></select>
<button class="main-btn" onclick="loadAll()">Görüntüle</button>
<button class="main-btn" onclick="saveFav()">⭐ Favori</button>
<label style="display:flex; align-items:center; gap:5px; background:white; padding:10px; border-radius:12px; border:1px solid #ddd;">
    <input type="checkbox" id="sickCheck"> 🤧 Hastayım
</label>
</div>
<p style="text-align:center" id="favInfo"></p>

<div class="week" id="weather"></div>

<div class="outfits" id="outfits">
  <h2>👇 Öneri Almak İçin Güne Tıkla</h2>
  <div class="outfit-grid" id="outfitList"></div>

  <h3 id="selectedDayTitle" style="text-align:center; display:none; margin-top:30px;"></h3>
  <div id="detailsContainer" class="details-section"></div>
</div>

</div>

<script>
const cities = {{ cities|tojson }};
const citySelect = document.getElementById("city");
const favInfo = document.getElementById("favInfo");
const detailsContainer = document.getElementById("detailsContainer");
const selectedDayTitle = document.getElementById("selectedDayTitle");

citySelect.innerHTML = '<option value="">Şehir seç</option>';
cities.forEach(c=> citySelect.innerHTML+=`<option>${c}</option>`);

if(localStorage.getItem("favCity")){
  citySelect.value = localStorage.getItem("favCity");
  favInfo.innerText = "⭐ Favori: " + citySelect.value;
}

function saveFav(){
  if(citySelect.value) localStorage.setItem("favCity", citySelect.value);
}

function icon(d){
  d=d.toLowerCase();
  if(d.includes("yağmur")) return "🌧️";
  if(d.includes("kar")) return "❄️";
  if(d.includes("bulut")) return "☁️";
  return "☀️";
}

async function showDetails(day, temp, weather){
  // Başlık güncelle
  const hastaMi = document.getElementById("sickCheck").checked;
  selectedDayTitle.style.display = "block";
  selectedDayTitle.innerText = `${day} İçin Yapay Zeka Önerileri (${temp}°C, ${weather})`;

  // Kutuları yükleniyor moduna al
  detailsContainer.innerHTML = `
    <div class="detail-box"><p class="loading">🤖 AI Düşünüyor...</p></div>
    <div class="detail-box"><p class="loading">👕 Dolap karıştırılıyor...</p></div>
    <div class="detail-box"><p class="loading">👟 Ayakkabı seçiliyor...</p></div>
  `;

  // Backend'e sor
  try {
    const res = await fetch('/api/kombin-iste', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ day: day, temp: temp, weather: weather , sick: hastaMi })
    });

    const data = await res.json();

    // Cevap gelince kutuları güncelle
    detailsContainer.innerHTML = `
      <div class="detail-box"><h3>💡 Seçenek 1</h3><p>${data.kutu1}</p></div>
      <div class="detail-box"><h3>✨ Seçenek 2</h3><p>${data.kutu2}</p></div>
      <div class="detail-box"><h3>🔥 Seçenek 3</h3><p>${data.kutu3}</p></div>
    `;

  } catch(err) {
    detailsContainer.innerHTML = "<p>Bir hata oluştu :(</p>";
  }
}

async function loadAll(){
  const city = citySelect.value || localStorage.getItem("favCity");
  if(!city) return alert("Şehir seç");

  const res=await fetch(`/api/weather?city=${city}`);
  const data=await res.json();

  const wDiv = document.getElementById("weather");
  const oDiv = document.getElementById("outfitList");

  wDiv.innerHTML="";
  oDiv.innerHTML="";
  document.getElementById("outfits").style.display="none";
  detailsContainer.innerHTML=""; 
  selectedDayTitle.style.display="none";

  data.forEach(d=>{
    wDiv.innerHTML+=`
      <div class="day-card" data-temp="${d.temp}">
        <div class="icon">${icon(d.weather)}</div>
        <h3>${d.day}</h3>
        <div class="temp">${d.temp}°C</div>
        <div class="desc">${d.weather}</div>
      </div>
    `;

    // Butona tıklayınca showDetails fonksiyonunu çağırıyoruz
    // Parametreleri (gün, sıcaklık, hava) gönderiyoruz
    oDiv.innerHTML+=`
      <button class="day-select-btn" onclick="showDetails('${d.day}', ${d.temp}, '${d.weather}')">
        ${d.day}
      </button>
    `;
  });

  // Renklendirme
  document.querySelectorAll(".day-card").forEach(c=>{
    const t=parseInt(c.dataset.temp);
    c.style.background = t<=5?"#e3f2fd":t<=15?"#e8f5e9":t<=25?"#fffde7":"#fff3e0";
  });

  document.getElementById("outfits").style.display="block";
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML, cities=CITIES)


if __name__ == "__main__":
    app.run(debug=True)