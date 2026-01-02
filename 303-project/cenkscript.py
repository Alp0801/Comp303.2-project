import streamlit as st
from dotenv import load_dotenv
load_dotenv()
import json
import time
from datetime import datetime
import requests
import os
from google import genai
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime
)
from sqlalchemy.orm import declarative_base, sessionmaker

# =====================================================
# AYARLAR
# =====================================================

st.set_page_config(page_title="AI Stil Asistanı", layout="wide")
st.markdown("""
<style>

/* GENEL ARKA PLAN */
.stApp {
    background: 
      radial-gradient(circle at top left, #7f6ae6, transparent 40%),
      radial-gradient(circle at bottom right, #6a7cf7, transparent 40%),
      linear-gradient(135deg, #0f172a, #1e293b);
    background-attachment: fixed;
    color: #fff;
}

/* BAŞLIK */
h1, h2, h3 {
    color: #fff;
}

/* KART GENEL */
.weather-card {
    position: relative;
    overflow: hidden;
    border-radius: 18px;
    padding: 18px;
    text-align: center;
    cursor: pointer;

    backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.25);

    box-shadow: 0 20px 40px rgba(0,0,0,.25);

  min-height: 230px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;

    transition:
        transform .35s ease,
        box-shadow .35s ease,
        background .6s ease,
        filter .35s ease;

}

/* SICAKLIĞA GÖRE KART İÇİ RENKLER */
.weather-card.cold {
    background: linear-gradient(
        135deg,
        rgba(77,171,247,0.35),
        rgba(255,255,255,0.12)
    );
}

.weather-card.mild {
    background: linear-gradient(
        135deg,
        rgba(81,207,102,0.35),
        rgba(255,255,255,0.12)
    );
}

.weather-card.hot {
    background: linear-gradient(
        135deg,
        rgba(255,146,43,0.4),
        rgba(255,255,255,0.12)
    );
}

/* HOVER EFEKT */
.weather-card:hover {
    transform: translateY(-10px) scale(1.05);
    box-shadow: 0 30px 60px rgba(0,0,0,.45);
    filter: saturate(1.15) brightness(1.05);
}

/* IŞIK / GLOW EFEKTİ */
.weather-card::after {
    content: "";
    position: absolute;
    inset: -40%;
    background: radial-gradient(
        circle,
        rgba(255,255,255,0.45),
        transparent 60%
    );
    opacity: 0;
    transform: translate(-30%, -30%);
    transition:
        opacity .4s ease,
        transform .6s ease;
    pointer-events: none;
}

.weather-card:hover::after {
    opacity: 1;
    transform: translate(0, 0);
}

/* SICAKLIK */
.weather-temp {
    font-size: 28px;
    font-weight: 700;
}

/* AÇIKLAMA */
.weather-desc {
    opacity: .85;
    font-size: 14px;
}

/* BUTON */
.stButton > button {
    background: linear-gradient(135deg,#6a7cf7,#7f6ae6);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 10px 16px;
    font-weight: 600;
    transition: .3s;
}

.stButton > button:hover {
    transform: scale(1.05);
    box-shadow: 0 10px 25px rgba(0,0,0,.3);
}

.weather-card.selected {
    outline: 2px solid rgba(255,255,255,.6);
    box-shadow:
        0 0 0 4px rgba(255,255,255,.15),
        0 30px 60px rgba(0,0,0,.45);
}



</style>
""", unsafe_allow_html=True)



WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DAYS_TR = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
CITIES = ["Istanbul","Ankara","Izmir","Bursa","Antalya","Adana","Konya","Gaziantep","Kayseri","Trabzon"]

CACHE = {}
CACHE_TTL = 600

USERS = {
    "alperen": {
        "style": "spor",
        "colors": "koyu renkler",
        "budget": "orta"
    }
}
CURRENT_USER = "alperen"

# =====================================================
# DATABASE (SQLite)
# =====================================================

Base = declarative_base()
engine = create_engine("sqlite:///favorites.db", echo=False)
Session = sessionmaker(bind=engine)
db = Session()

class FavoriteOutfit(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True)
    city = Column(String)
    day = Column(String)
    temp = Column(Integer)
    weather = Column(String)
    sick = Column(Boolean)
    option_number = Column(Integer)
    ust = Column(String)
    alt = Column(String)
    ayakkabi = Column(String)
    dis_giyim = Column(String)
    aksesuar = Column(String)
    aciklama = Column(String)
    puan = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)


def delete_favorite(fav_id: int) -> bool:
    "DBDEN Favori Silme FuNC"
    fav = db.query(FavoriteOutfit).filter(FavoriteOutfit.id == fav_id).first()
    if fav is None:
        return False
    db.delete(fav)
    db.commit()
    return True

# =====================================================
# WEATHER
# =====================================================

def get_weather(city):
    now = time.time()
    if city in CACHE and now - CACHE[city]["time"] < CACHE_TTL:
        return CACHE[city]["data"]

    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&lang=tr&appid={WEATHER_API_KEY}"
    data = requests.get(url).json()

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

# =====================================================
# GEMINI
# =====================================================

def get_gemini_suggestion(temp, weather, day, is_sick):
    client = genai.Client(api_key=GEMINI_API_KEY)
    u = USERS[CURRENT_USER]

    prompt = f"""
    Sen profesyonel bir moda stilistisin.

    GÜN: {day}
    HAVA: {temp}°C, {weather}
    STİL: {u['style']}
    RENK: {u['colors']}
    BÜTÇE: {u['budget']}
    HASTA: {"Evet" if is_sick else "Hayır"}

    SADECE JSON DÖN.
    HTML, <h3>, <p>, emoji veya markdown KULLANMA.
    SADECE DÜZ METİN yaz.

    {{
      "secenek1": {{
        "ust": "",
        "alt": "",
        "ayakkabi": "",
        "dis_giyim": "",
        "aksesuar": "",
        "aciklama": "",
        "puan": 0
      }},
      "secenek2": {{
        "ust": "",
        "alt": "",
        "ayakkabi": "",
        "dis_giyim": "",
        "aksesuar": "",
        "aciklama": "",
        "puan": 0
      }},
      "secenek3": {{
        "ust": "",
        "alt": "",
        "ayakkabi": "",
        "dis_giyim": "",
        "aksesuar": "",
        "aciklama": "",
        "puan": 0
      }}
    }}
    """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.replace("```json","").replace("```","").strip()

    try:
        return json.loads(text)
    except Exception:
        st.error("🤖 AI yanıtı okunamadı, tekrar dene")
        return None


def render_item(icon, title, value):
    if value and value.strip():
        return f"<h3>{icon} {title}</h3><p>{value}</p>"
    return ""


def select_day(day_data):
    st.session_state["selected_day"] = day_data

    # Gün değiştiyse eski kombin silinsin
    if "kombin" in st.session_state:
        del st.session_state["kombin"]

    # yeni gün seçildi, tekrar üretmeye hazır
    st.session_state["need_generate"] = True

# =====================================================
# SIDEBAR (PROFİL)
# =====================================================

st.sidebar.title("👤 Stil Profili")

style = st.sidebar.selectbox("Stil", ["spor","klasik","oversize"])
colors = st.sidebar.selectbox("Renk", ["açık renkler","koyu renkler"])
budget = st.sidebar.selectbox("Bütçe", ["düşük","orta","yüksek"])
hasta = st.sidebar.checkbox("🤧 Hastayım")

if st.sidebar.button("💾 Profil Kaydet"):
    USERS[CURRENT_USER].update({
        "style": style,
        "colors": colors,
        "budget": budget
    })
    st.sidebar.success("Profil kaydedildi")

# =====================================================
# MAIN UI
# =====================================================

st.title("🌤️ AI Stil Asistanı")

city = st.selectbox("📍 Şehir Seç", CITIES)

if st.button("🌦️ Hava Durumunu Göster"):
    st.session_state["weather"] = get_weather(city)

# =====================================================
# WEATHER CARDS
# =====================================================

if "weather" in st.session_state:
    cols = st.columns(len(st.session_state["weather"]))

    for col, d in zip(cols, st.session_state["weather"]):
        temp = d["temp"]

        if temp < 8:
            temp_class = "cold"
        elif temp <= 22:
            temp_class = "mild"
        else:
            temp_class = "hot"

        selected = (
            "selected"
            if "selected_day" in st.session_state
            and st.session_state["selected_day"]["day"] == d["day"]
            else ""
        )

        with col:
            st.markdown(
                f"""
                <div class="weather-card {temp_class} {selected}">
                    <h3>{d['day']}</h3>
                    <div class="weather-temp">{d['temp']}°C</div>
                    <div class="weather-desc">{d['weather']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(
                    f"{d['day']} Kombin",
                    key=d["day"],
                    on_click=select_day,
                    args=(d,)
            ):
                pass

# =====================================================
# AI KOMBIN
# =====================================================

if "selected_day" in st.session_state:
    d = st.session_state["selected_day"]


    if st.session_state.get("need_generate", False):
        with st.spinner("🤖 Yapay zeka kombin hazırlıyor..."):
            st.session_state["kombin"] = get_gemini_suggestion(
                d["temp"], d["weather"], d["day"], hasta
            )

        st.session_state["need_generate"] = False

# =====================================================
# TABS
# =====================================================

if "kombin" in st.session_state:
    tabs = st.tabs(["Seçenek 1","Seçenek 2","Seçenek 3"])

    for i, tab in enumerate(tabs, start=1):
        with tab:
            if hasta:
                st.markdown("🤒 **Konfor öncelikli kombin**")

            k = st.session_state["kombin"][f"secenek{i}"]

            st.markdown(
                f"""
                <div class="weather-card" style="margin-bottom:20px">
                    {render_item("👕", "Üst", k["ust"])}
                    {render_item("👖", "Alt", k["alt"])}
                    {render_item("👟", "Ayakkabı", k["ayakkabi"])}
                    {render_item("🧥", "Dış Giyim", k["dis_giyim"])}
                    {render_item("🕶️", "Aksesuar", k["aksesuar"])}
                    {f"<p style='opacity:.8'>💡 {k['aciklama']}</p>" if k.get("aciklama") else ""}

                </div>
                """,
                unsafe_allow_html=True
            )
            if k.get("puan"):
                st.progress(k["puan"] / 10)
                st.caption(f"⭐ Uyumluluk Puanı: {k['puan']}/10")

            if st.button("⭐ Favoriye Kaydet", key=f"fav{i}"):
                fav = FavoriteOutfit(
                    city=city,
                    day=d["day"],
                    temp=d["temp"],
                    weather=d["weather"],
                    sick=hasta,
                    option_number=i,
                    **k
                )
                db.add(fav)
                db.commit()
                st.success("Favoriye eklendi")

# =====================================================
# FAVORİLER
# =====================================================

st.subheader("📌 Favoriler")

favorites = db.query(FavoriteOutfit).order_by(FavoriteOutfit.created_at.desc()).all()

if len(favorites) == 0:
    st.info("Henüz favori yok.")
else:
    for f in favorites:
        left, right = st.columns([8, 2])

        with left:
            st.markdown(
                f"""
                **{f.city} - {f.day}** ({f.temp}°C, {f.weather}) {"🤧" if f.sick else ""}  
                🧾 Seçenek: {f.option_number}  
                👕 {f.ust} | 👖 {f.alt} | 👟 {f.ayakkabi} | 🧥 {f.dis_giyim} | 🕶️ {f.aksesuar}  
                {f"💡 {f.aciklama}<br>" if f.aciklama else ""}
                {f"⭐ Puan: {f.puan}/10" if f.puan else ""}
                <small>{f.created_at}</small>
                """,
                unsafe_allow_html=True
            )

        with right:

            if st.button("🗑️ Sil", key=f"del_{f.id}"):
                ok = delete_favorite(f.id)
                if ok:
                    st.success("Favori silindi ✅")
                    st.rerun()
                else:
                    st.error("Silinecek favori bulunamadı ❌")

