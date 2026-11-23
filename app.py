import json
import random
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "backend" / "music.db"
FRONTEND_PATH = BASE_DIR / "frontend" / "index.html"

app = FastAPI(title="오늘의 음악 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GENRE_TO_MB_TAGS = {
    "pop": ["pop", "synthpop", "dance pop"],
    "kpop": ["k-pop", "korean", "kpop"],
    "rnb": ["rnb", "contemporary rnb"],
    "soul": ["soul", "neo soul", "funk"],
    "indie": ["indie", "indie pop", "indie folk"],
    "rock": ["rock", "alternative rock", "modern rock"],
    "hiphop": ["hip hop", "rap", "boom bap"],
    "jazz": ["jazz", "smooth jazz", "bossa nova"],
    "classical": ["classical", "piano", "orchestral"],
    "lofi": ["lo-fi", "chillhop", "instrumental"],
    "ambient": ["ambient", "chillout", "dream pop"],
    "citypop": ["city pop", "japanese pop", "disco"],
    "acoustic": ["acoustic", "singer-songwriter", "folk"],
}

SEED_SONGS = [
    ("s1", "Paris in the Rain", "Lauv", ["pop", "rnb", "acoustic"], ["morning", "afternoon", "sunset"], ["drizzle", "rainy", "partly_cloudy"], ["calm", "drowsy", "excited", "happy"], ["refresh", "comfort", "rest"]),
    ("s2", "Happy", "Pharrell Williams", ["pop", "soul"], ["early_morning", "morning", "afternoon"], ["sunny", "clear_breeze"], ["happy", "stressed", "frustrated", "drowsy"], ["excited_up", "energize", "refresh"]),
    ("s3", "Don't Know Why", "Norah Jones", ["jazz", "pop"], ["early_morning", "morning", "afternoon", "late_night"], ["drizzle", "rainy", "cloudy", "foggy"], ["calm", "drowsy", "tired", "focused"], ["calm_down", "focus", "rest", "sleep"]),
    ("s4", "Almost Blue", "Chet Baker", ["jazz"], ["night", "late_night"], ["rainy", "snowy", "foggy", "cloudy"], ["lonely", "sad", "focused", "calm"], ["calm_down", "focus", "sleep", "reflective"]),
    ("s5", "Viva La Vida", "Coldplay", ["rock", "indie", "pop"], ["early_morning", "morning", "afternoon"], ["sunny", "windy", "stormy", "cloudy"], ["stressed", "frustrated", "tired", "happy"], ["energize", "confident", "excited_up"]),
    ("s6", "Day 1 ◐", "HONNE", ["pop", "lofi"], ["early_morning", "morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "excited", "calm", "focused"], ["refresh", "focus", "energize"]),
    ("s7", "BIRDS OF A FEATHER", "Billie Eilish", ["pop"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "partly_cloudy", "windy"], ["happy", "excited", "stressed", "frustrated"], ["refresh", "excited_up", "energize"]),
    ("s8", "Leave The Door Open", "Silk Sonic", ["rnb", "soul"], ["sunset", "night"], ["clear_breeze", "partly_cloudy", "windy"], ["drowsy", "calm", "excited", "tired"], ["calm_down", "refresh", "rest"]),
    ("s9", "Easily", "Bruno Major", ["rnb", "acoustic"], ["night", "late_night"], ["rainy", "drizzle", "cloudy", "snowy"], ["lonely", "sad", "tired", "calm"], ["comfort", "rest", "sleep", "reflective"]),
    ("s10", "Best Part (feat. H.E.R.)", "Daniel Caesar", ["rnb", "soul"], ["early_morning", "sunset", "night"], ["clear_breeze", "sunny", "partly_cloudy"], ["calm", "excited", "happy", "drowsy"], ["comfort", "rest", "calm_down"]),
    ("s11", "Easy", "Mac Ayres", ["rnb", "lofi"], ["afternoon", "sunset", "late_night"], ["drizzle", "cloudy", "foggy", "rainy"], ["drowsy", "tired", "calm", "focused"], ["rest", "calm_down", "focus"]),
    ("s12", "Slow Dancing in a Burning Room", "John Mayer", ["rock", "indie"], ["sunset", "night", "late_night"], ["cloudy", "rainy", "foggy", "windy"], ["sad", "lonely", "stressed"], ["reflective", "comfort", "calm_down"]),
    ("s13", "Apocalypse", "Cigarettes After Sex", ["indie", "ambient"], ["night", "late_night"], ["foggy", "rainy", "snowy", "stormy"], ["lonely", "sad", "calm", "focused"], ["reflective", "sleep", "calm_down"]),
    ("s14", "Pink + White", "Frank Ocean", ["rnb", "hiphop"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "partly_cloudy"], ["calm", "happy", "drowsy", "excited"], ["refresh", "rest", "reflective"]),
    ("s15", "Cruel Summer", "Taylor Swift", ["pop"], ["afternoon", "sunset"], ["sunny", "clear_breeze", "windy"], ["happy", "excited", "frustrated", "stressed"], ["excited_up", "energize", "refresh"]),
    ("s16", "Don't Stop Me Now", "Queen", ["rock", "pop"], ["early_morning", "morning", "afternoon"], ["sunny", "windy", "partly_cloudy"], ["happy", "tired", "stressed", "frustrated"], ["energize", "excited_up", "confident"]),
    ("s17", "Merry Christmas Mr. Lawrence", "Ryuichi Sakamoto", ["classical", "ambient"], ["early_morning", "night", "late_night"], ["snowy", "foggy", "cloudy"], ["focused", "calm", "lonely", "sad"], ["focus", "sleep", "calm_down", "reflective"]),
    ("s18", "Matsuri", "Fujii Kaze", ["citypop", "pop"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "windy"], ["stressed", "frustrated", "happy", "drowsy"], ["refresh", "excited_up", "energize"]),
    ("s19", "River Flows in You", "이루마 (Yiruma)", ["classical", "ambient"], ["early_morning", "night", "late_night"], ["rainy", "snowy", "drizzle", "foggy"], ["focused", "tired", "calm", "sad"], ["focus", "sleep", "rest", "calm_down"]),
    ("s20", "비 오는 날 듣기 좋은 노래 (Feat. Colde)", "에픽하이 (EPIK HIGH)", ["kpop", "hiphop"], ["afternoon", "sunset", "night"], ["rainy", "drizzle", "cloudy", "foggy"], ["sad", "lonely", "tired", "calm"], ["comfort", "calm_down", "reflective"]),
    ("s21", "비도 오고 그래서 (Feat. 신용재)", "헤이즈 (Heize)", ["kpop", "rnb"], ["sunset", "night", "late_night"], ["rainy", "stormy", "drizzle"], ["sad", "lonely", "tired"], ["comfort", "reflective", "calm_down"]),
    ("s22", "한 페이지가 될 수 있게", "데이식스 (DAY6)", ["kpop", "rock"], ["early_morning", "morning", "afternoon"], ["sunny", "clear_breeze", "partly_cloudy", "windy"], ["happy", "excited", "tired", "stressed"], ["energize", "excited_up", "refresh", "confident"]),
    ("s23", "사건의 지평선", "윤하", ["kpop", "rock"], ["afternoon", "sunset", "night"], ["sunny", "windy", "stormy", "cloudy"], ["sad", "stressed", "frustrated", "happy"], ["energize", "confident", "refresh"]),
    ("s24", "밤편지", "아이유 (IU)", ["kpop", "acoustic"], ["night", "late_night"], ["snowy", "rainy", "cloudy", "clear_breeze"], ["calm", "tired", "lonely", "sad"], ["comfort", "rest", "sleep", "calm_down"]),
    ("s25", "Square (2017)", "백예린", ["kpop", "indie", "rnb"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "partly_cloudy", "windy"], ["happy", "excited", "calm", "frustrated"], ["refresh", "comfort", "excited_up"]),
    ("s26", "EVERYTHING", "검정치마", ["kpop", "indie"], ["night", "late_night"], ["snowy", "rainy", "foggy", "cloudy"], ["calm", "lonely", "sad", "focused"], ["calm_down", "sleep", "rest", "reflective"]),
    ("s27", "Put Your Records On", "Corinne Bailey Rae", ["soul", "acoustic"], ["morning", "afternoon"], ["sunny", "clear_breeze", "partly_cloudy"], ["calm", "happy", "drowsy"], ["refresh", "comfort", "rest"]),
    ("s28", "Sunday Morning", "Maroon 5", ["pop"], ["early_morning", "morning"], ["rainy", "drizzle", "sunny", "clear_breeze"], ["calm", "drowsy", "happy"], ["rest", "refresh", "calm_down"]),
    ("s29", "Come Away With Me", "Norah Jones", ["jazz"], ["night", "late_night", "sunset"], ["rainy", "drizzle", "cloudy", "foggy"], ["tired", "calm", "lonely"], ["sleep", "rest", "comfort"]),
    ("s30", "Fly Me to the Moon", "Frank Sinatra", ["jazz", "pop"], ["sunset", "night"], ["clear_breeze", "sunny", "partly_cloudy"], ["happy", "excited", "calm"], ["refresh", "rest", "excited_up"]),
    ("s31", "Vienna", "Billy Joel", ["pop", "acoustic"], ["sunset", "night", "late_night"], ["cloudy", "windy", "rainy"], ["stressed", "frustrated", "tired", "sad"], ["comfort", "calm_down", "reflective"]),
    ("s32", "Fix You", "Coldplay", ["rock", "pop"], ["night", "late_night", "sunset"], ["rainy", "stormy", "cloudy", "snowy"], ["sad", "lonely", "tired"], ["comfort", "reflective", "confident"]),
    ("s33", "Nights", "Frank Ocean", ["rnb", "hiphop"], ["night", "late_night"], ["foggy", "rainy", "windy"], ["focused", "lonely", "stressed"], ["reflective", "focus", "calm_down"]),
    ("s34", "Plastic Love", "Mariya Takeuchi", ["citypop", "pop"], ["sunset", "night"], ["rainy", "clear_breeze", "windy"], ["drowsy", "lonely", "excited"], ["refresh", "excited_up", "reflective"]),
    ("s35", "Clair de Lune", "Claude Debussy", ["classical", "ambient"], ["early_morning", "late_night", "night"], ["snowy", "foggy", "drizzle"], ["calm", "focused", "tired"], ["sleep", "focus", "calm_down", "rest"]),
    ("s36", "Isn't She Lovely", "Stevie Wonder", ["soul", "pop"], ["morning", "afternoon"], ["sunny", "clear_breeze"], ["happy", "excited"], ["excited_up", "energize", "refresh"]),
    ("s37", "Golden Hour", "JVKE", ["pop"], ["sunset", "afternoon"], ["sunny", "clear_breeze", "partly_cloudy"], ["excited", "happy", "calm"], ["reflective", "comfort", "excited_up"]),
    ("s38", "주저하는 연인들을 위해", "잔나비", ["kpop", "indie"], ["sunset", "night"], ["windy", "cloudy", "foggy"], ["sad", "lonely", "calm"], ["reflective", "comfort", "calm_down"]),
    ("s39", "Ditto", "뉴진스 (NewJeans)", ["kpop"], ["afternoon", "sunset", "night"], ["snowy", "cloudy", "partly_cloudy"], ["calm", "drowsy", "focused"], ["refresh", "focus", "reflective"]),
    ("s40", "봄날", "방탄소년단 (BTS)", ["kpop", "hiphop"], ["early_morning", "sunset", "night"], ["snowy", "cloudy", "windy"], ["sad", "lonely", "tired"], ["comfort", "refresh", "confident"]),
    ("s41", "Nocturne Op.9 No.2", "Frédéric Chopin", ["classical"], ["early_morning", "night", "late_night"], ["rainy", "snowy", "foggy", "cloudy"], ["calm", "lonely", "sad", "focused"], ["sleep", "calm_down", "focus", "rest"]),
    ("s42", "Gymnopédie No.1", "Erik Satie", ["classical", "ambient"], ["early_morning", "afternoon", "late_night"], ["drizzle", "rainy", "foggy", "snowy"], ["tired", "calm", "drowsy", "focused"], ["rest", "sleep", "calm_down", "focus"]),
    ("s43", "Summer", "Joe Hisaishi", ["classical"], ["morning", "afternoon"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "excited", "calm"], ["refresh", "comfort", "energize"]),
    ("s44", "Ride on Time", "Tatsuro Yamashita", ["citypop"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "windy"], ["happy", "excited", "tired"], ["energize", "excited_up", "refresh"]),
    ("s45", "Remember Summer Days", "Anri", ["citypop"], ["afternoon", "sunset", "night"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "drowsy", "calm"], ["refresh", "excited_up", "reflective"]),
    ("s46", "Aruarian Dance", "Nujabes", ["lofi", "hiphop"], ["afternoon", "night", "late_night"], ["rainy", "cloudy", "clear_breeze"], ["focused", "calm", "tired"], ["focus", "calm_down", "rest"]),
    ("s47", "Affection", "Jinsang", ["lofi"], ["early_morning", "night", "late_night"], ["rainy", "drizzle", "snowy"], ["drowsy", "calm", "focused"], ["focus", "sleep", "rest"]),
    ("s48", "Controlla", "Idealism", ["lofi", "ambient"], ["night", "late_night"], ["rainy", "foggy", "snowy"], ["lonely", "tired", "focused"], ["sleep", "calm_down", "focus"]),
    ("s49", "Luv(sic) pt.3 (feat. Shing02)", "Nujabes", ["hiphop", "lofi"], ["sunset", "night", "late_night"], ["rainy", "cloudy", "windy"], ["lonely", "calm", "focused"], ["reflective", "comfort", "focus"]),
    ("s50", "I'm Yours", "Jason Mraz", ["acoustic"], ["morning", "afternoon"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "calm", "stressed"], ["refresh", "comfort", "rest"]),
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS songs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            genres TEXT NOT NULL,
            times TEXT NOT NULL,
            weathers TEXT NOT NULL,
            current_moods TEXT NOT NULL,
            target_moods TEXT NOT NULL,
            source TEXT DEFAULT 'seed'
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time_id TEXT NOT NULL,
            time_label TEXT NOT NULL,
            weather_id TEXT NOT NULL,
            weather_label TEXT NOT NULL,
            current_mood_id TEXT NOT NULL,
            current_mood_label TEXT NOT NULL,
            target_mood_id TEXT NOT NULL,
            target_mood_label TEXT NOT NULL,
            genre_label TEXT NOT NULL,
            song_id TEXT NOT NULL,
            title TEXT NOT NULL,
            artist TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS recent_history (
            song_id TEXT PRIMARY KEY,
            shown_at TEXT NOT NULL
        )
        """
    )
    for row in SEED_SONGS:
        cur.execute(
            """
            INSERT OR IGNORE INTO songs
            (id, title, artist, genres, times, weathers, current_moods, target_moods, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'seed')
            """,
            (
                row[0], row[1], row[2],
                json.dumps(row[3], ensure_ascii=False),
                json.dumps(row[4], ensure_ascii=False),
                json.dumps(row[5], ensure_ascii=False),
                json.dumps(row[6], ensure_ascii=False),
                json.dumps(row[7], ensure_ascii=False),
            ),
        )
    conn.commit()
    conn.close()


init_db()


class RecommendRequest(BaseModel):
    timeOfDay: str
    weather: str
    currentMood: str
    targetMood: str
    genre: str = "all"
    excludeIds: List[str] = []


class SaveRecordRequest(BaseModel):
    date: str
    timeId: str
    timeLabel: str
    weatherId: str
    weatherLabel: str
    currentMoodId: str
    currentMoodLabel: str
    targetMoodId: str
    targetMoodLabel: str
    genreLabel: str = "전체"
    songId: str
    title: str
    artist: str


async def sync_musicbrainz_into_db(genre: str) -> int:
    tags = GENRE_TO_MB_TAGS.get(genre, ["pop", "indie", "jazz"]) if genre != "all" else ["pop", "indie", "jazz", "rnb", "classical"]
    chosen_tag = random.choice(tags)
    offset = random.randint(0, 200)
    url = f"https://musicbrainz.org/ws/2/recording/?query=tag:%22{chosen_tag}%22&limit=20&offset={offset}&fmt=json"
    try:
        async with httpx.AsyncClient(timeout=4.0, headers={"User-Agent": "TodaysMusicApp/1.0 (https://example.com)"}) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return 0
            data = res.json()
    except Exception:
        return 0

    conn = get_conn()
    cur = conn.cursor()
    added = 0
    for r in data.get("recordings", []):
        title = (r.get("title") or "").strip()
        credits = r.get("artist-credit") or []
        artist = "".join((c.get("name") or (c.get("artist") or {}).get("name") or "") + (c.get("joinphrase") or "") for c in credits).strip()
        if not title or not artist or artist == "[unknown]":
            continue
        mb_id = f"mb_{r['id']}"
        genres = [genre] if genre != "all" else [chosen_tag]
        cur.execute(
            """
            INSERT OR IGNORE INTO songs
            (id, title, artist, genres, times, weathers, current_moods, target_moods, source)
            VALUES (?, ?, ?, ?, '[]', '[]', '[]', '[]', 'musicbrainz')
            """,
            (mb_id, title, artist, json.dumps(genres, ensure_ascii=False)),
        )
        if cur.rowcount > 0:
            added += 1
    conn.commit()
    conn.close()
    return added


@app.post("/api/recommend")
async def recommend(req: RecommendRequest):
    await sync_musicbrainz_into_db(req.genre)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT song_id FROM recent_history ORDER BY shown_at DESC LIMIT 16")
    recent_ids = {r["song_id"] for r in cur.fetchall()}

    cur.execute("SELECT * FROM songs")
    rows = cur.fetchall()

    candidates = []
    for r in rows:
        genres = json.loads(r["genres"])
        if req.genre != "all" and req.genre not in genres:
            continue
        score = 0.0
        if req.timeOfDay in json.loads(r["times"]):
            score += 2.5
        if req.weather in json.loads(r["weathers"]):
            score += 2.5
        if req.currentMood in json.loads(r["current_moods"]):
            score += 2.5
        if req.targetMood in json.loads(r["target_moods"]):
            score += 3.5
        if r["source"] == "musicbrainz":
            score += 2.0

        penalty = 0.0
        if r["id"] in req.excludeIds:
            penalty -= 200.0
        elif r["id"] in recent_ids:
            penalty -= 40.0

        total = score + penalty + random.uniform(0.0, 4.5)
        candidates.append((total, {"id": r["id"], "title": r["title"], "artist": r["artist"]}))

    candidates.sort(key=lambda x: x[0], reverse=True)
    top_pool = [c[1] for c in candidates[:10]]
    random.shuffle(top_pool)
    picked = top_pool[:4]

    now = datetime.utcnow().isoformat()
    for p in picked:
        cur.execute("INSERT OR REPLACE INTO recent_history (song_id, shown_at) VALUES (?, ?)", (p["id"], now))
    conn.commit()
    conn.close()
    return {"tracks": picked}


@app.get("/api/saved")
def list_saved():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM saved_records ORDER BY id DESC").fetchall()
    conn.close()
    return {"records": [dict(r) for r in rows]}


@app.post("/api/saved")
def add_saved(req: SaveRecordRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO saved_records
        (date, time_id, time_label, weather_id, weather_label, current_mood_id, current_mood_label, target_mood_id, target_mood_label, genre_label, song_id, title, artist)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            req.date, req.timeId, req.timeLabel, req.weatherId, req.weatherLabel,
            req.currentMoodId, req.currentMoodLabel, req.targetMoodId, req.targetMoodLabel,
            req.genreLabel, req.songId, req.title, req.artist,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}


@app.delete("/api/saved/{record_id}")
def delete_saved(record_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM saved_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/saved")
def clear_saved():
    conn = get_conn()
    conn.execute("DELETE FROM saved_records")
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/")
def serve_frontend():
    if not FRONTEND_PATH.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(FRONTEND_PATH)
