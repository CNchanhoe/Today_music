import json
import re
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

HERE = Path(__file__).resolve().parent
if (HERE / "index.html").exists():
    DB_PATH = HERE / "music.db"
    FRONTEND_PATH = HERE / "index.html"
else:
    BASE_DIR = HERE.parent
    DB_PATH = BASE_DIR / "backend" / "music.db"
    FRONTEND_PATH = BASE_DIR / "frontend" / "index.html"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="오늘의 음악 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CLASSICAL_COMPOSER_WHITELIST_RE = re.compile(r"albeniz|albinoni|albéniz|bach|barber|bartok|bartók|beethoven|berlioz|bizet|boccherini|borodin|brahms|bruch|bruckner|chopin|clementi|copland|corelli|debussy|dvorak|dvořák|elgar|falla|faure|fauré|franck|gluck|granados|grieg|handel|haydn|holst|liszt|mahler|mendelssohn|monteverdi|mozart|mussorgsky|paganini|prokofiev|puccini|purcell|rachmaninoff|rameau|ravel|respighi|rimsky-korsakov|rossini|saint-saens|saint-saëns|sarasate|satie|scarlatti|schubert|schumann|scriabin|shostakovich|sibelius|smetana|strauss|stravinsky|tchaikovsky|telemann|vaughan williams|verdi|vivaldi|wagner|wieniawski", re.I)
CLASSICAL_EXCLUDE_RE = re.compile(r"yiruma|hisaishi|sakamoto|einaudi|richter|tiersen|clayderman|2cellos|garrett|maksim|soundtrack|\bost\b|anime|game|cover|tribute|karaoke|remix|8-bit|lullaby|medley|jazz|rock|metal|hip.?hop|\bpop\b|synth|electronic|new age|ambient|crossover|cinematic|lofi|lo-fi|avant.?garde|atonal|serialism|twelve.?tone|electroacoustic|musique concrète|microtonal|experimental|noise|cage|stockhausen|xenakis|boulez|penderecki|ligeti|ferneyhough|schoenberg|webern|berg|feldman|berio|nono|feat\.|이루마|히사이시|류이치|커버|리믹스|자장가", re.I)

GENRE_ARTISTS = {
    "pop": [
        "Taylor Swift",
        "The Weeknd",
        "Bruno Mars",
        "Dua Lipa",
        "Ed Sheeran",
        "Billie Eilish",
        "Ariana Grande",
        "Charlie Puth",
        "Justin Bieber",
        "Coldplay",
        "Maroon 5",
        "Lauv",
        "Shawn Mendes",
        "Harry Styles",
        "Adele",
        "Sabrina Carpenter",
        "Olivia Rodrigo",
        "Troye Sivan"
    ],
    "kpop": [
        "IU",
        "BTS",
        "NewJeans",
        "DAY6",
        "AKMU",
        "Taeyeon",
        "aespa",
        "BLACKPINK",
        "SEVENTEEN",
        "Red Velvet",
        "EXO",
        "Paul Kim",
        "Heize",
        "10CM",
        "Jannabi",
        "Younha",
        "Crush",
        "Zion.T",
        "Baek Yerin",
        "BOL4"
    ],
    "rnb": [
        "Frank Ocean",
        "Daniel Caesar",
        "SZA",
        "H.E.R.",
        "Bruno Major",
        "The Weeknd",
        "Khalid",
        "Giveon",
        "Brent Faiyaz",
        "Mac Ayres",
        "Summer Walker",
        "Dean",
        "Crush",
        "Colde",
        "Usher",
        "Alicia Keys",
        "John Legend"
    ],
    "soul": [
        "Stevie Wonder",
        "Aretha Franklin",
        "Marvin Gaye",
        "Silk Sonic",
        "Leon Bridges",
        "Amy Winehouse",
        "Corinne Bailey Rae",
        "Sam Cooke",
        "Otis Redding",
        "Erykah Badu",
        "Al Green",
        "Bill Withers",
        "John Mayer",
        "Norah Jones",
        "Michael Kiwanuka"
    ],
    "indie": [
        "The 1975",
        "LANY",
        "Cigarettes After Sex",
        "Tame Impala",
        "Arctic Monkeys",
        "Mac DeMarco",
        "Men I Trust",
        "Clairo",
        "Rex Orange County",
        "Beach House",
        "The Black Skirts",
        "HYUKOH",
        "Jannabi",
        "Baek Yerin",
        "wave to earth",
        "Phoebe Bridgers"
    ],
    "rock": [
        "Queen",
        "Coldplay",
        "Oasis",
        "Radiohead",
        "Linkin Park",
        "Imagine Dragons",
        "Muse",
        "The Beatles",
        "Nirvana",
        "Green Day",
        "Foo Fighters",
        "Maroon 5",
        "DAY6",
        "Younha",
        "OneRepublic",
        "U2",
        "Red Hot Chili Peppers",
        "The Killers"
    ],
    "hiphop": [
        "Kendrick Lamar",
        "Drake",
        "Kanye West",
        "Travis Scott",
        "Tyler, The Creator",
        "J. Cole",
        "Post Malone",
        "Mac Miller",
        "Nujabes",
        "EPIK HIGH",
        "ZICO",
        "beenzino",
        "Kid Cudi",
        "A$AP Rocky",
        "Eminem",
        "Jay-Z"
    ],
    "jazz": [
        "Chet Baker",
        "Miles Davis",
        "Bill Evans",
        "John Coltrane",
        "Norah Jones",
        "Frank Sinatra",
        "Ella Fitzgerald",
        "Louis Armstrong",
        "Nat King Cole",
        "Stan Getz",
        "João Gilberto",
        "Nina Simone",
        "Herbie Hancock",
        "Kamasi Washington",
        "Robert Glasper",
        "Laufey"
    ],
    "lofi": [
        "Nujabes",
        "Jinsang",
        "Idealism",
        "potsu",
        "Kupla",
        "eevee",
        "SwuM",
        "Jhove",
        "Lofi Girl",
        "Tomppabeats",
        "Bsd.u",
        "In Love With a Ghost",
        "Ryuichi Sakamoto",
        "Joe Hisaishi",
        "Yiruma"
    ],
    "ambient": [
        "Brian Eno",
        "Ryuichi Sakamoto",
        "Max Richter",
        "Ludovico Einaudi",
        "Ólafur Arnalds",
        "Nils Frahm",
        "Yiruma",
        "Joe Hisaishi",
        "Hammock",
        "Stars of the Lid",
        "Tycho",
        "Aphex Twin",
        "Sigur Rós",
        "M83",
        "Explosions in the Sky",
        "Bonobo"
    ],
    "citypop": [
        "Tatsuro Yamashita",
        "Mariya Takeuchi",
        "Anri",
        "Miki Matsubara",
        "Taeko Onuki",
        "Junko Yagami",
        "Toshiki Kadomatsu",
        "Omega Tribe",
        "Meiko Nakahara",
        "Yukika",
        "Yubin",
        "Bronze",
        "Fujii Kaze",
        "Kirinji",
        "Casiopea"
    ],
    "acoustic": [
        "Jason Mraz",
        "Ed Sheeran",
        "John Mayer",
        "Jack Johnson",
        "10CM",
        "IU",
        "Jukjae",
        "Kwak Jin Eon",
        "Damien Rice",
        "James Taylor",
        "Simon & Garfunkel",
        "Norah Jones",
        "Ben Howard",
        "Bon Iver",
        "Sufjan Stevens",
        "Iron & Wine"
    ]
}

GENRE_TO_MB_TAGS = {
    "pop": ["pop", "synthpop", "dance pop"],
    "kpop": ["k-pop", "korean", "kpop"],
    "rnb": ["rnb", "contemporary rnb"],
    "soul": ["soul", "neo soul", "funk"],
    "indie": ["indie", "indie pop", "indie folk"],
    "rock": ["rock", "alternative rock", "modern rock"],
    "hiphop": ["hip hop", "rap", "boom bap"],
    "jazz": ["jazz", "smooth jazz", "bossa nova"],
    "classical": ["symphony", "concerto", "violin concerto", "piano concerto", "cello concerto", "piano sonata", "violin sonata", "cello sonata", "string quartet", "chamber music", "nocturne", "prelude", "etude", "symphonic poem", "overture", "baroque", "romanticism", "impressionism", "classical"],
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
    ("s17", "Merry Christmas Mr. Lawrence", "Ryuichi Sakamoto", ["ambient"], ["early_morning", "night", "late_night"], ["snowy", "foggy", "cloudy"], ["focused", "calm", "lonely", "sad"], ["focus", "sleep", "calm_down", "reflective"]),
    ("s18", "Matsuri", "Fujii Kaze", ["citypop", "pop"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "windy"], ["stressed", "frustrated", "happy", "drowsy"], ["refresh", "excited_up", "energize"]),
    ("s19", "River Flows in You", "이루마 (Yiruma)", ["ambient"], ["early_morning", "night", "late_night"], ["rainy", "snowy", "drizzle", "foggy"], ["focused", "tired", "calm", "sad"], ["focus", "sleep", "rest", "calm_down"]),
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
    ("s43", "Summer", "Joe Hisaishi", ["ambient", "lofi"], ["morning", "afternoon"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "excited", "calm"], ["refresh", "comfort", "energize"]),
    ("s44", "Ride on Time", "Tatsuro Yamashita", ["citypop"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "windy"], ["happy", "excited", "tired"], ["energize", "excited_up", "refresh"]),
    ("s45", "Remember Summer Days", "Anri", ["citypop"], ["afternoon", "sunset", "night"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "drowsy", "calm"], ["refresh", "excited_up", "reflective"]),
    ("s46", "Aruarian Dance", "Nujabes", ["lofi", "hiphop"], ["afternoon", "night", "late_night"], ["rainy", "cloudy", "clear_breeze"], ["focused", "calm", "tired"], ["focus", "calm_down", "rest"]),
    ("s47", "Affection", "Jinsang", ["lofi"], ["early_morning", "night", "late_night"], ["rainy", "drizzle", "snowy"], ["drowsy", "calm", "focused"], ["focus", "sleep", "rest"]),
    ("s48", "Controlla", "Idealism", ["lofi", "ambient"], ["night", "late_night"], ["rainy", "foggy", "snowy"], ["lonely", "tired", "focused"], ["sleep", "calm_down", "focus"]),
    ("s49", "Luv(sic) pt.3 (feat. Shing02)", "Nujabes", ["hiphop", "lofi"], ["sunset", "night", "late_night"], ["rainy", "cloudy", "windy"], ["lonely", "calm", "focused"], ["reflective", "comfort", "focus"]),
    ("s50", "I'm Yours", "Jason Mraz", ["acoustic"], ["morning", "afternoon"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "calm", "stressed"], ["refresh", "comfort", "rest"]),
    ("s51", "Cello Suite No.1 in G Major, BWV 1007: I. Prélude", "Johann Sebastian Bach", ["classical"], ["early_morning", "morning", "afternoon", "night"], ["sunny", "clear_breeze", "cloudy", "rainy"], ["calm", "focused", "tired"], ["focus", "calm_down", "rest"]),
    ("s52", "Piano Sonata No.14 'Moonlight': I. Adagio sostenuto", "Ludwig van Beethoven", ["classical"], ["night", "late_night", "sunset"], ["rainy", "snowy", "foggy", "cloudy"], ["sad", "lonely", "focused", "calm"], ["reflective", "sleep", "calm_down", "focus"]),
    ("s53", "The Four Seasons: Spring, Op.8 No.1: I. Allegro", "Antonio Vivaldi", ["classical"], ["early_morning", "morning", "afternoon"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "excited", "drowsy"], ["energize", "refresh", "excited_up"]),
    ("s54", "Liebestraum No.3 in A-Flat Major, S.541", "Franz Liszt", ["classical"], ["sunset", "night", "late_night"], ["clear_breeze", "rainy", "snowy", "cloudy"], ["calm", "lonely", "sad", "excited"], ["comfort", "reflective", "rest"]),
    ("s55", "Pavane pour une infante défunte", "Maurice Ravel", ["classical"], ["early_morning", "sunset", "late_night"], ["drizzle", "foggy", "rainy", "snowy"], ["tired", "calm", "drowsy", "sad"], ["calm_down", "sleep", "rest", "comfort"]),
    ("s56", "Swan Lake, Op.20: Scene (Moderato)", "Pyotr Ilyich Tchaikovsky", ["classical"], ["sunset", "night"], ["snowy", "windy", "cloudy", "stormy"], ["stressed", "frustrated", "sad", "focused"], ["reflective", "confident", "comfort"]),
    ("s57", "Piano Concerto No.21 in C Major, K.467: II. Andante", "Wolfgang Amadeus Mozart", ["classical"], ["early_morning", "morning", "afternoon"], ["sunny", "clear_breeze", "partly_cloudy"], ["calm", "happy", "focused"], ["calm_down", "focus", "rest", "comfort"]),
    ("s58", "Violin Concerto in E Minor, Op.64: I. Allegro molto appassionato", "Felix Mendelssohn", ["classical"], ["morning", "afternoon", "sunset"], ["windy", "clear_breeze", "cloudy"], ["excited", "stressed", "focused"], ["energize", "confident", "reflective"]),
    ("s59", "Cello Concerto in E Minor, Op.85: I. Adagio - Moderato", "Edward Elgar", ["classical"], ["sunset", "night", "late_night"], ["rainy", "foggy", "cloudy", "windy"], ["sad", "lonely", "tired"], ["reflective", "comfort", "calm_down"]),
    ("s60", "Symphony No.9 'From the New World': II. Largo", "Antonín Dvořák", ["classical"], ["early_morning", "sunset", "night"], ["cloudy", "clear_breeze", "snowy"], ["tired", "calm", "lonely"], ["comfort", "rest", "reflective"]),
    ("s61", "Étude in C-Sharp Minor, Op.2 No.1", "Alexander Scriabin", ["classical"], ["night", "late_night", "sunset"], ["rainy", "snowy", "foggy", "cloudy"], ["sad", "lonely", "focused"], ["reflective", "comfort", "calm_down"]),
    ("s62", "Má vlast: Vltava (The Moldau)", "Bedřich Smetana", ["classical"], ["early_morning", "morning", "afternoon"], ["sunny", "clear_breeze", "windy"], ["calm", "excited", "happy"], ["refresh", "energize", "reflective"]),
    ("s63", "An der schönen blauen Donau (The Blue Danube), Op.314", "Johann Strauss II", ["classical"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "excited", "drowsy"], ["excited_up", "refresh", "energize"]),
    ("s64", "Morgen!, Op.27 No.4 (Orchestral Version)", "Richard Strauss", ["classical"], ["early_morning", "sunset", "night"], ["clear_breeze", "drizzle", "cloudy"], ["calm", "tired", "lonely"], ["comfort", "calm_down", "rest"]),
    ("s65", "Superstition", "Stevie Wonder", ["soul"], ["morning", "afternoon"], ["sunny", "clear_breeze"], ["happy", "excited", "drowsy"], ["energize", "excited_up", "refresh"]),
    ("s66", "What's Going On", "Marvin Gaye", ["soul"], ["sunset", "night"], ["cloudy", "rainy", "windy"], ["sad", "stressed", "focused"], ["comfort", "reflective", "calm_down"]),
    ("s67", "Valerie", "Amy Winehouse", ["soul"], ["afternoon", "sunset", "night"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "frustrated", "tired"], ["excited_up", "refresh", "energize"]),
    ("s68", "Stay With Me", "Miki Matsubara", ["citypop"], ["sunset", "night", "late_night"], ["rainy", "clear_breeze", "windy"], ["lonely", "drowsy", "calm"], ["reflective", "refresh", "comfort"]),
    ("s69", "4:00 A.M.", "Taeko Onuki", ["citypop"], ["night", "late_night"], ["foggy", "rainy", "cloudy"], ["lonely", "tired", "calm"], ["calm_down", "reflective", "sleep"]),
    ("s70", "Midnight Pretenders", "Tomoko Aran", ["citypop"], ["night", "late_night"], ["clear_breeze", "cloudy", "rainy"], ["drowsy", "lonely", "focused"], ["reflective", "rest", "calm_down"]),
    ("s71", "Feather", "Nujabes", ["lofi"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "partly_cloudy"], ["focused", "calm", "happy"], ["focus", "refresh", "calm_down"]),
    ("s72", "I'm Closing My Eyes", "potsu", ["lofi"], ["night", "late_night"], ["rainy", "drizzle", "snowy"], ["tired", "drowsy", "sad"], ["sleep", "rest", "calm_down"]),
    ("s73", "Snowfall", "Øneheart & reidenshi", ["lofi"], ["early_morning", "night", "late_night"], ["snowy", "foggy", "rainy"], ["lonely", "tired", "focused"], ["sleep", "focus", "calm_down"]),
    ("s74", "Better Together", "Jack Johnson", ["acoustic"], ["early_morning", "morning", "afternoon"], ["sunny", "clear_breeze", "partly_cloudy"], ["calm", "happy", "drowsy"], ["rest", "comfort", "refresh"]),
    ("s75", "Gravity", "John Mayer", ["acoustic"], ["sunset", "night", "late_night"], ["rainy", "cloudy", "foggy"], ["sad", "stressed", "tired"], ["reflective", "comfort", "calm_down"]),
    ("s76", "Photograph", "Ed Sheeran", ["acoustic"], ["sunset", "night"], ["snowy", "cloudy", "clear_breeze"], ["lonely", "sad", "calm"], ["comfort", "reflective", "rest"]),
    ("s77", "별 보러 가자", "적재", ["acoustic", "kpop"], ["night", "late_night", "sunset"], ["clear_breeze", "sunny", "partly_cloudy"], ["calm", "excited", "lonely"], ["comfort", "rest", "calm_down"]),
    ("s78", "Nuvole Bianche", "Ludovico Einaudi", ["ambient"], ["early_morning", "night", "late_night"], ["snowy", "rainy", "foggy", "cloudy"], ["focused", "sad", "calm"], ["focus", "sleep", "calm_down", "reflective"]),
    ("s79", "On the Nature of Daylight", "Max Richter", ["ambient"], ["sunset", "night", "late_night"], ["rainy", "cloudy", "foggy"], ["sad", "lonely", "focused"], ["reflective", "comfort", "calm_down"]),
    ("s80", "Autumn Leaves", "Chet Baker", ["jazz"], ["sunset", "night"], ["windy", "cloudy", "rainy"], ["calm", "lonely", "drowsy"], ["calm_down", "rest", "reflective"]),
    ("s81", "From The Start", "Laufey", ["jazz"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "partly_cloudy"], ["excited", "happy", "calm"], ["refresh", "excited_up", "comfort"]),
    ("s82", "Sunflower", "Post Malone & Swae Lee", ["hiphop"], ["morning", "afternoon", "sunset"], ["sunny", "clear_breeze", "partly_cloudy"], ["happy", "excited", "tired"], ["energize", "refresh", "excited_up"]),
    ("s83", "See You Again", "Tyler, The Creator (feat. Kali Uchis)", ["hiphop"], ["afternoon", "sunset"], ["sunny", "clear_breeze", "partly_cloudy"], ["excited", "happy", "drowsy"], ["refresh", "reflective", "comfort"]),
    ("s84", "bad", "wave to earth", ["indie"], ["afternoon", "sunset", "night"], ["clear_breeze", "partly_cloudy", "drizzle"], ["calm", "drowsy", "happy"], ["calm_down", "rest", "refresh"]),
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
            INSERT OR REPLACE INTO songs
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
    favArtists: List[str] = []


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


async def fetch_artist_tags(name: str) -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=2.5, headers={"User-Agent": "TodaysMusicApp/1.0 (https://example.com)"}) as client:
            res = await client.get("https://musicbrainz.org/ws/2/artist/", params={"query": name, "limit": 1, "fmt": "json"})
            if res.status_code != 200:
                return []
            artists = res.json().get("artists") or []
            if not artists:
                return []
            tags = sorted(artists[0].get("tags") or [], key=lambda t: t.get("count", 0), reverse=True)
            return [t["name"] for t in tags[:4] if t.get("name")]
    except Exception:
        return []


async def sync_musicbrainz_into_db(genre: str, fav_artists: List[str]) -> int:
    tags = GENRE_TO_MB_TAGS.get(genre, ["pop", "indie", "jazz"]) if genre != "all" else ["pop", "indie", "jazz", "rnb", "classical"]
    queries = []
    if fav_artists and genre != "classical":
        pick_fav = random.choice(fav_artists)
        queries.append((f'artist:"{pick_fav}"', random.randint(0, 20)))
        taste_tags = await fetch_artist_tags(pick_fav)
        if taste_tags:
            queries.append((f'tag:"{random.choice(taste_tags)}"', random.randint(0, 120)))
    if genre == "classical":
        ctags = random.sample(GENRE_TO_MB_TAGS["classical"], 2)
        for ct in ctags:
            queries.append((f'tag:"{ct}" AND status:official', random.randint(0, 2500)))
    else:
        chosen_tag = random.choice(tags)
        queries.append((f'tag:"{chosen_tag}" AND status:official', random.randint(0, 2000)))
        pool = GENRE_ARTISTS.get(genre) if (genre != "all" and genre in GENRE_ARTISTS) else [a for lst in GENRE_ARTISTS.values() for a in lst]
        for art in random.sample(pool, min(2, len(pool))):
            queries.append((f'artist:"{art}"', random.randint(0, 25)))

    recordings = []
    try:
        async with httpx.AsyncClient(timeout=4.0, headers={"User-Agent": "TodaysMusicApp/1.0 (https://example.com)"}) as client:
            for q_str, off in queries:
                res = await client.get("https://musicbrainz.org/ws/2/recording/", params={"query": q_str, "limit": 15, "offset": off, "fmt": "json"})
                if res.status_code == 200:
                    items = res.json().get("recordings", [])
                    if q_str.startswith('artist:"'):
                        last_name = q_str[8:-1].strip().split()[-1].lower()
                        filtered_items = []
                        for it in items:
                            ac = "".join((c.get("name") or (c.get("artist") or {}).get("name") or "") for c in (it.get("artist-credit") or [])).lower()
                            if last_name in ac:
                                filtered_items.append(it)
                        recordings.extend(filtered_items)
                    else:
                        recordings.extend(items)
    except Exception:
        pass
    if not recordings:
        return 0
    data = {"recordings": recordings}

    conn = get_conn()
    cur = conn.cursor()
    added = 0
    for r in data.get("recordings", []):
        title = (r.get("title") or "").strip()
        credits = r.get("artist-credit") or []
        artist = "".join((c.get("name") or (c.get("artist") or {}).get("name") or "") + (c.get("joinphrase") or "") for c in credits).strip()
        if not title or not artist or artist == "[unknown]":
            continue
        if genre == "classical" and CLASSICAL_EXCLUDE_RE.search(f"{title} {artist}"):
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
    await sync_musicbrainz_into_db(req.genre, req.favArtists)

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
        if req.genre == "classical":
            if CLASSICAL_EXCLUDE_RE.search(f"{r['title']} {r['artist']}"):
                continue
            if r["source"] != "musicbrainz" and not CLASSICAL_COMPOSER_WHITELIST_RE.search(r['artist']):
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
        if req.favArtists:
            hay = f"{r['artist']} {r['title']}".lower()
            if any(f.lower() in hay for f in req.favArtists):
                score += 4.0

        penalty = 0.0
        if r["id"] in req.excludeIds:
            penalty -= 200.0
        elif r["id"] in recent_ids:
            penalty -= 40.0

        total = score + penalty + random.uniform(0.0, 4.5)
        candidates.append((total, {"id": r["id"], "title": r["title"], "artist": r["artist"]}))

    candidates.sort(key=lambda x: x[0], reverse=True)
    top_pool = [c[1] for c in candidates[:20]]
    random.shuffle(top_pool)
    picked = []
    seen_artists = set()
    for c in top_pool:
        ak = c["artist"].lower()
        if ak in seen_artists:
            continue
        seen_artists.add(ak)
        picked.append(c)
        if len(picked) >= 4:
            break

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
