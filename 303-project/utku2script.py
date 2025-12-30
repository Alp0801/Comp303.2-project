import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
import requests
from flask import Flask, jsonify, request, render_template_string
from google import genai


# --- API KEYS ---
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)

# DB AYARLARI

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///favorites.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class FavoriteOutfit(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    city = db.Column(db.String(50), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    temp = db.Column(db.Integer, nullable=False)
    weather = db.Column(db.String(100), nullable=False)
    sick = db.Column(db.Boolean, default=False)

    option_number = db.Column(db.Integer, nullable=False)  # 1/2/3

    ust = db.Column(db.String(200), nullable=False)
    alt = db.Column(db.String(200), nullable=False)
    ayakkabi = db.Column(db.String(200), nullable=False)
    dis_giyim = db.Column(db.String(200), nullable=False)
    aksesuar = db.Column(db.String(200), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()

# --- AYARLAR ---


DAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
CITIES = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana", "Konya", "Gaziantep", "Kayseri", "Trabzon"]

CACHE = {}
CACHE_TTL = 600
USERS = {
    "alperen": {
        "password": "1234",
        "style": "spor",
        "colors": "koyu renkler",
        "budget": "orta"
    }
}

CURRENT_USER = "alperen"


# --- GEMINI
def get_gemini_suggestion(temp, weather, day, is_sick):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        u = USERS[CURRENT_USER]

        def weather_context(t):
            if t <= 5:
                return "Çok soğuk hava"
            elif t <= 15:
                return "Serin hava"
            elif t <= 25:
                return "Ilık hava"
            else:
                return "Sıcak hava"

        prompt = f'''
        Sen profesyonel bir moda stilistisin.

        GÜN: {day}
        HAVA:
        - {temp}°C
        - {weather}
        - {weather_context(temp)}

        KULLANICI:
        - Stil: {u['style']}
        - Renk tercihi: {u['colors']}
        - Bütçe: {u['budget']}
        - Hasta: {"Evet" if is_sick else "Hayır"}

        KURALLAR:
        - Net ve kısa yaz
        - Ürün kategorilerini ayır
        - Marka ismi YAZMA
        - Türkiye iklimine uygun öner
        - Hastaysa katmanlı giyim öner

        SADECE JSON DÖN:
        {{
          "secenek1": {{
            "ust": "",
            "alt": "",
            "ayakkabi": "",
            "dis_giyim": "",
            "aksesuar": ""
          }},
          "secenek2": {{
            "ust": "",
            "alt": "",
            "ayakkabi": "",
            "dis_giyim": "",
            "aksesuar": ""
          }},
          "secenek3": {{
            "ust": "",
            "alt": "",
            "ayakkabi": "",
            "dis_giyim": "",
            "aksesuar": ""
          }}
        }}

        '''

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        # Clean response text (remove markdown code blocks if present)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        elif text.startswith("```"):
            text = text[3:]  # Remove ```
        if text.endswith("```"):
            text = text[:-3]  # Remove trailing ```
        text = text.strip()

        return json.loads(text)

    except Exception as e:
        print("Gemini error:", e)

        return {
            "secenek1": {"ust": "Hata", "alt": "Hata", "ayakkabi": "Hata", "dis_giyim": "Hata", "aksesuar": "Hata"},
            "secenek2": {"ust": "Hata", "alt": "Hata", "ayakkabi": "Hata", "dis_giyim": "Hata", "aksesuar": "Hata"},
            "secenek3": {"ust": "Hata", "alt": "Hata", "ayakkabi": "Hata", "dis_giyim": "Hata", "aksesuar": "Hata"}
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


@app.route("/api/favorites", methods=["POST"])
def add_favorite():
    data = request.json or {}

    required = ["city", "day", "temp", "weather", "sick", "option_number", "outfit"]
    for key in required:
        if key not in data:
            return jsonify({"error": f"Missing field: {key}"}), 400

    outfit = data["outfit"]

    fav = FavoriteOutfit(
        city=data["city"],
        day=data["day"],
        temp=int(data["temp"]),
        weather=data["weather"],
        sick=bool(data["sick"]),
        option_number=int(data["option_number"]),
        ust=outfit["ust"],
        alt=outfit["alt"],
        ayakkabi=outfit["ayakkabi"],
        dis_giyim=outfit["dis_giyim"],
        aksesuar=outfit["aksesuar"]
    )

    db.session.add(fav)
    db.session.commit()

    return jsonify({"ok": True, "id": fav.id})


@app.route("/api/favorites", methods=["GET"])
def list_favorites():
    items = FavoriteOutfit.query.order_by(FavoriteOutfit.created_at.desc()).all()

    return jsonify([
        {
            "id": f.id,
            "city": f.city,
            "day": f.day,
            "temp": f.temp,
            "weather": f.weather,
            "sick": f.sick,
            "option_number": f.option_number,
            "ust": f.ust,
            "alt": f.alt,
            "ayakkabi": f.ayakkabi,
            "dis_giyim": f.dis_giyim,
            "aksesuar": f.aksesuar,
            "created_at": f.created_at.isoformat()
        }
        for f in items
    ])


@app.route("/api/kombin-iste", methods=["POST"])
def api_kombin():
    data = request.json
    hasta_durumu = data.get('sick', False)
    # Frontend'den gelen verileri alıyoruz
    sonuc = get_gemini_suggestion(data['temp'], data['weather'], data['day'], hasta_durumu)
    return jsonify(sonuc)


@app.route("/api/profile", methods=["POST"])
def update_profile():
    global CURRENT_USER

    if not CURRENT_USER:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    USERS[CURRENT_USER]["style"] = data["style"]
    USERS[CURRENT_USER]["colors"] = data["colors"]
    USERS[CURRENT_USER]["budget"] = data["budget"]

    return jsonify({"success": True})


# --- HTML ---
HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>AI Stil Asistanı</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body{
  margin:0;
  font-family:'Segoe UI',sans-serif;
  min-height:100vh;
  background:
    radial-gradient(circle at top left, #7f6ae6, transparent 40%),
    radial-gradient(circle at bottom right, #6a7cf7, transparent 40%),
    linear-gradient(135deg, #0f172a, #1e293b);
  background-attachment: fixed;
}



.container{
  max-width:1500px;
  margin:30px auto;
  padding:30px;

  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);

  border-radius:24px;
  border:1px solid rgba(255,255,255,0.25);
  box-shadow:
    0 20px 50px rgba(0,0,0,0.25),
    inset 0 1px 0 rgba(255,255,255,0.2);
}

h1{text-align:center;margin-bottom:20px}
.controls{display:flex;justify-content:center;gap:12px;margin-bottom:25px;}
select, button{
  padding:8px 12px;
  border-radius:8px;
  border:1px solid #ccc;
  font-size:14px;
}

.main-btn{
  background:#4CAF50;
  color:white;
  cursor:pointer;
  border:none;
  padding:8px 14px;
  border-radius:8px;
  font-size:14px;
}

.week{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;}
.day-card{
  background:#f4f6f8;
  border-radius:18px;
  padding:18px;
  text-align:center;
  position:relative;
  overflow:hidden;
  cursor:pointer;
  transition: 
    transform .35s ease,
    box-shadow .35s ease,
    background .35s ease;
}


.day-card:hover{
  transform:translateY(-10px) scale(1.04);
  box-shadow:0 20px 35px rgba(0,0,0,.22);
}


.day-card::after{
  content:"";
  position:absolute;
  inset:0;
  background:linear-gradient(
    120deg,
    transparent,
    rgba(255,255,255,.7),
    transparent
  );
  transform:translateX(-130%);
  transition:.7s;
}
.day-card:hover::after{
  transform:translateX(130%);
}


.day-card:hover .icon{
  animation:float 1.5s ease-in-out infinite;
}

@keyframes float{
  0%{transform:translateY(0)}
  50%{transform:translateY(-8px)}
  100%{transform:translateY(0)}
}


.day-card.active{
  background:#6a7cf7 !important;
  color:white;
}
.day-card.active .desc{
  opacity:.9;
}

.icon{font-size:36px;}
.temp{font-size:28px;font-weight:700}

/* KOMBİN BÖLÜMÜ */
.outfits{margin-top:35px;background:#ecfdf3;border-radius:22px;padding:25px;display:none;}
.outfit-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:20px;}
.day-select-btn{
  width:auto;
  padding:10px 14px;
  background:white;
  border:1px solid #ddd;
  border-radius:8px;
  font-weight:600;
  cursor:pointer;
  transition:.2s;
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
#tabs button{
  padding:10px 16px;
  margin:0 6px;
  border:none;
  border-radius:20px;
  cursor:pointer;
  background:#eee;
  font-weight:600;
}

#tabs button.active{
  background:#6a7cf7;
  color:white;
}

</style>
</head>
<body>
<div class="container">
<h1>🌤️ AI Stil Asistanı</h1>

<div class="controls">
<div style="margin-top:20px; display:flex; gap:10px; justify-content:center;">
  <select id="style">
    <option value="spor">Spor</option>
    <option value="klasik">Klasik</option>
    <option value="oversize">Oversize</option>
  </select>

  <select id="colors">
    <option value="açık renkler">Açık Renkler</option>
    <option value="koyu renkler">Koyu Renkler</option>
  </select>

  <select id="budget">
    <option value="düşük">Düşük</option>
    <option value="orta">Orta</option>
    <option value="yüksek">Yüksek</option>
  </select>

  <button onclick="saveProfile()">Profil Kaydet</button>
</div>

<select id="city"></select>
<button class="main-btn" onclick="loadAll()">Görüntüle</button>
    <button class="main-btn" onclick="loadFavorites()">📌 Favoriler</button>
<label style="display:flex; align-items:center; gap:5px; background:white; padding:10px; border-radius:12px; border:1px solid #ddd;">
    <input type="checkbox" id="sickCheck"> 🤧 Hastayım
</label>
</div>
<p style="text-align:center" id="favInfo"></p>

<div class="week" id="weather"></div>

<div class="outfits" id="outfits">
<div id="favoritesBox" style="display:none; margin-top:20px; background:#fff; padding:20px; border-radius:16px;"></div>


  <div class="outfit-grid" id="outfitList"></div>

  <!-- 🔽 SEKME BUTONLARI BURAYA -->
  <div id="tabs" style="display:none; text-align:center; margin-bottom:20px;">
    <button onclick="showTab(1)">Seçenek 1</button>
    <button onclick="showTab(2)">Seçenek 2</button>
    <button onclick="showTab(3)">Seçenek 3</button>
  </div>

  <h3 id="selectedDayTitle" style="text-align:center; display:none; margin-top:30px;"></h3>

  <!-- 🔽 KOMBİN DETAYLARI -->
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
window.selectedContext = { day, temp, weather };
  const hastaMi = document.getElementById("sickCheck").checked;

  selectedDayTitle.style.display = "block";
  selectedDayTitle.innerText = `${day} İçin Yapay Zeka Önerileri (${temp}°C, ${weather})`;

  // Sekmeleri gizle
  document.getElementById("tabs").style.display = "none";

  // Loading
  detailsContainer.innerHTML = `
    <div class="detail-box">🤖 Düşünüyor...</div>
    <div class="detail-box">👕 Kombinleniyor...</div>
    <div class="detail-box">👟 Seçiliyor...</div>
    <div class="detail-box">🧥 Hazırlanıyor...</div>
    <div class="detail-box">🕶️ Tamamlanıyor...</div>
  `;

  try {
    const res = await fetch('/api/kombin-iste', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ day, temp, weather, sick: hastaMi })
    });

    const data = await res.json();
    console.log("AI DATA:", data);

    // 🔥 EN ÖNEMLİ KISIM
    kombinData = data;

    // Sekmeleri aç
    document.getElementById("tabs").style.display = "block";

    // İlk sekmeyi göster
    showTab(1);

  } catch(err){
    detailsContainer.innerHTML = "<p>Bir hata oluştu 😢</p>";
    console.error(err);
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
      <div class="day-card" data-temp="${d.temp}" onclick="showDetails('${d.day}', ${d.temp}, '${d.weather}')">
        <div class="icon">${icon(d.weather)}</div>
        <h3>${d.day}</h3>
        <div class="temp">${d.temp}°C</div>
        <div class="desc">${d.weather}</div>
      </div>
    `;
  });

  // Renklendirme
  document.querySelectorAll(".day-card").forEach(c=>{
    const t=parseInt(c.dataset.temp);
    c.style.background = t<=5?"#e3f2fd":t<=15?"#e8f5e9":t<=25?"#fffde7":"#fff3e0";
  });

  document.getElementById("outfits").style.display="block";
}

async function saveSelectedFavorite(){
  if(!kombinData) return alert("Önce bir kombin al.");

  const city = citySelect.value || localStorage.getItem("favCity");
  const hastaMi = document.getElementById("sickCheck").checked;

  const option_number = aktifTab;
  const outfit = kombinData["secenek" + aktifTab];

  const payload = {
    city: city,
    day: window.selectedContext.day,
    temp: window.selectedContext.temp,
    weather: window.selectedContext.weather,
    sick: hastaMi,
    option_number: option_number,
    outfit: outfit
  };

  const res = await fetch("/api/favorites", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if(data.ok) alert("✅ Favoriye kaydedildi!");
  else alert("❌ Hata: " + (data.error || "Bilinmeyen hata"));
}
async function loadFavorites(){
  const box = document.getElementById("favoritesBox");
  box.style.display = "block";
  box.innerHTML = "<p class='loading'>📥 Favoriler yükleniyor...</p>";

  try{
    const res = await fetch("/api/favorites");
    const items = await res.json();

    if(!Array.isArray(items)){
      box.innerHTML = "<b>❌ Hata:</b> Favoriler okunamadı (API JSON liste dönmedi).";
      console.log("Favorites API response:", items);
      return;
    }

    if(items.length === 0){
      box.innerHTML = "<b>Henüz favori yok.</b>";
      return;
    }

    box.innerHTML = `
      <h2 style="margin-top:0;">📌 Favoriler</h2>
      ${items.map(f => `
        <div style="border:1px solid #eee; border-radius:12px; padding:12px; margin-bottom:10px;">
          <b>${f.city} - ${f.day}</b> (${f.temp}°C, ${f.weather}) ${f.sick ? "🤧" : ""}
          <div style="margin-top:8px;">👕 ${f.ust}</div>
          <div>👖 ${f.alt}</div>
          <div>👟 ${f.ayakkabi}</div>
          <div>🧥 ${f.dis_giyim}</div>
          <div>🕶️ ${f.aksesuar}</div>
          <small style="color:#666;">${f.created_at}</small>
        </div>
      `).join("")}
    `;
  }catch(err){
    box.innerHTML = "<b>❌ Hata:</b> Favoriler yüklenirken sorun oluştu. Konsolu kontrol et.";
    console.error(err);
  }
}

async function saveProfile(){
  await fetch("/api/profile",{
    method:"POST",
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      style: style.value,
      colors: colors.value,
      budget: budget.value
    })
  });
  alert("Profil kaydedildi");
}
let kombinData = null;
let aktifTab = 1;

function showTab(n){
  aktifTab = n;

  document.querySelectorAll("#tabs button")
    .forEach((b,i)=> b.classList.toggle("active", i+1===n));

  const k = kombinData["secenek"+n];

  detailsContainer.innerHTML = `
    <div class="detail-box"><h3>👕 Üst</h3><p>${k.ust}</p></div>
    <div class="detail-box"><h3>👖 Alt</h3><p>${k.alt}</p></div>
    <div class="detail-box"><h3>👟 Ayakkabı</h3><p>${k.ayakkabi}</p></div>
    <div class="detail-box"><h3>🧥 Dış Giyim</h3><p>${k.dis_giyim}</p></div>
    <div class="detail-box"><h3>🕶️ Aksesuar</h3><p>${k.aksesuar}</p></div>


     <div class="detail-box" style="flex-basis:100%;">
      <button class="main-btn" onclick="saveSelectedFavorite()">⭐ Bu kombini kaydet</button>


    </div>
  `;
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