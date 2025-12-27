import requests, time
from flask import Flask, jsonify, request, render_template_string
from datetime import datetime

app = Flask(__name__)

API_KEY = "23005d9ad6a0c145d2cd791af1500b4e"

DAYS_TR = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
CITIES = ["Istanbul","Ankara","Izmir","Bursa","Antalya","Adana","Konya","Gaziantep","Kayseri","Trabzon"]

# 🔥 BACKEND CACHE
CACHE = {}
CACHE_TTL = 600  # 10 dakika

def get_weather(city):
    now = time.time()

    if city in CACHE and now - CACHE[city]["time"] < CACHE_TTL:
        return CACHE[city]["data"]

    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&lang=tr&appid={API_KEY}"
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

        if len(forecast) == 7:
            break

    CACHE[city] = {"time": now, "data": forecast}
    return forecast


@app.route("/api/weather")
def api_weather():
    city = request.args.get("city", "Istanbul")
    return jsonify(get_weather(city))


HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Haftalık Akıllı Kombin Asistanı</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body{
  margin:0;
  font-family:'Segoe UI',Arial,sans-serif;
  background:linear-gradient(120deg,#6a7cf7,#7f6ae6);
}

.container{
  max-width:1200px;
  margin:30px auto;
  background:#fff;
  border-radius:24px;
  padding:30px;
}

h1{text-align:center;margin-bottom:20px}

.controls{
  display:flex;
  justify-content:center;
  gap:12px;
  flex-wrap:wrap;
  margin-bottom:25px;
}

select,button{
  padding:10px 14px;
  border-radius:12px;
  border:1px solid #ddd;
}

button{
  background:#4CAF50;
  color:white;
  border:none;
  cursor:pointer;
}

.week{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:16px;
}

/* DAY CARD */
.day-card{
  background:#f4f6f8;
  border-radius:18px;
  padding:18px;
  text-align:center;
  position:relative;
  overflow:hidden;
  transition:.35s;
}

.day-card:hover{
  transform:translateY(-8px);
  box-shadow:0 18px 30px rgba(0,0,0,.18);
}

.day-card::after{
  content:"";
  position:absolute;
  inset:0;
  background:linear-gradient(120deg,transparent,rgba(255,255,255,.6),transparent);
  transform:translateX(-120%);
  transition:.6s;
}
.day-card:hover::after{transform:translateX(120%)}

/* ICON */
.icon{
  font-size:36px;
}
.day-card:hover .icon{
  animation:float 1.6s ease-in-out infinite;
}
@keyframes float{
  0%{transform:translateY(0)}
  50%{transform:translateY(-8px)}
  100%{transform:translateY(0)}
}

.temp{font-size:28px;font-weight:700}
.desc{opacity:.8}

/* Kombin */
.outfits{
  margin-top:35px;
  background:#ecfdf3;
  border-radius:22px;
  padding:25px;
}

.outfit-grid{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:15px;
}

.outfit-card{
  background:white;
  border-radius:16px;
  padding:15px;
}

.outfit-card b{
  display:block;
  color:#2e7d32;
  margin-bottom:6px;
}
</style>
</head>

<body>
<div class="container">

<h1>🌤️ Haftalık Akıllı Kombin Asistanı</h1>

<div class="controls">
<select id="city"></select>

<select id="sick">
<option value="hayir">Hasta değilim</option>
<option value="evet">Hastayım</option>
</select>

<button onclick="loadAll()">👕 Kombin Öner</button>
<button onclick="saveFav()">⭐ Favori</button>
</div>

<p style="text-align:center" id="favInfo"></p>

<div class="week" id="weather"></div>

<div class="outfits" id="outfits" style="display:none">
<h2>👔 Haftalık Kombin Önerileri</h2>
<div class="outfit-grid" id="outfitList"></div>
</div>

</div>

<script>
const cities = {{ cities|tojson }};
const citySelect = document.getElementById("city");
const favInfo = document.getElementById("favInfo");

citySelect.innerHTML = '<option value="">Şehir seç</option>';
cities.forEach(c=> citySelect.innerHTML+=`<option>${c}</option>`);

const fav = localStorage.getItem("favCity");
if(fav){
  citySelect.value = fav;
  favInfo.innerText = "⭐ Favori şehir: " + fav;
}

function saveFav(){
  if(!citySelect.value) return;
  localStorage.setItem("favCity", citySelect.value);
  favInfo.innerText = "⭐ Favori şehir: " + citySelect.value;
}

function icon(desc){
  desc=desc.toLowerCase();
  if(desc.includes("yağmur")) return "🌧️";
  if(desc.includes("kar")) return "❄️";
  if(desc.includes("bulut")) return "☁️";
  return "☀️";
}

async function loadAll(){
  const city = citySelect.value || localStorage.getItem("favCity");
  if(!city) return alert("Şehir seç");

  const sick=document.getElementById("sick").value;
  const res=await fetch(`/api/weather?city=${city}`);
  const data=await res.json();

  weather.innerHTML="";
  outfitList.innerHTML="";
  outfits.style.display="none";

  data.forEach(d=>{
    weather.innerHTML+=`
      <div class="day-card" data-temp="${d.temp}">
        <div class="icon">${icon(d.weather)}</div>
        <h3>${d.day}</h3>
        <div class="temp">${d.temp}°C</div>
        <div class="desc">${d.weather}</div>
      </div>
    `;

    let t="";
    if(d.temp<8) t="Kalın mont, atkı, bot";
    else if(d.temp<15) t="Ceket, kazak";
    else if(d.temp<22) t="Hafif ceket";
    else t="Tişört";

    if(d.weather.toLowerCase().includes("yağmur")) t+=", yağmurluk";
    if(sick==="evet") t+=", ekstra kalın giyin";

    outfitList.innerHTML+=`
      <div class="outfit-card"><b>${d.day}</b>${t}</div>
    `;
  });

  document.querySelectorAll(".day-card").forEach(c=>{
    const t=parseInt(c.dataset.temp);
    c.onmouseenter=()=> c.style.background =
      t<=5 ? "#e3f2fd" :
      t<=15 ? "#e8f5e9" :
      t<=25 ? "#fffde7" : "#fff3e0";
    c.onmouseleave=()=> c.style.background="#f4f6f8";
  });

  outfits.style.display="block";
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
