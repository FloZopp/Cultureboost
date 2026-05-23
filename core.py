# -*- coding: utf-8 -*-
"""
core.py - Moteur de CultureBoost
================================
Toute la logique non graphique de l'application :
  * base de donnees locale (SQLite)
  * repetition espacee (algorithme inspire de SM-2)
  * recuperation de questions depuis PLUSIEURS sources d'API
  * statistiques et progression (XP, niveaux, series)
  * jeu de questions de secours pour le mode hors-ligne

Ce module ne depend que de la bibliotheque standard de Python
(+ 'certifi' s'il est disponible, pour la verification SSL sur Android).
"""

import json
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
import html
import hashlib
import random
import time
import os
import ssl
from datetime import date

try:
    import certifi
except Exception:  # pragma: no cover
    certifi = None

# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------

HTTP_TIMEOUT = 12
USER_AGENT = "CultureBoost/2.0 (entrainement personnel)"

LEVEL_TITLES = [
    "Curieux", "Apprenti", "Amateur eclaire", "Bon eleve",
    "Tete bien faite", "Erudit", "Savant", "Puits de science",
    "Maitre du savoir", "Encyclopedie vivante",
]
XP_PER_LEVEL = 250
XP_PER_CORRECT = 10

_DB_PATH = None  # defini par init_db()


# --------------------------------------------------------------------------
# Base de donnees
# --------------------------------------------------------------------------

def init_db(data_dir):
    """Initialise la base de donnees dans le dossier indique."""
    global _DB_PATH
    os.makedirs(data_dir, exist_ok=True)
    _DB_PATH = os.path.join(data_dir, "culture_boost.db")
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id TEXT PRIMARY KEY, question TEXT NOT NULL, correct TEXT NOT NULL,
            incorrect TEXT NOT NULL, category TEXT, difficulty TEXT,
            anecdote TEXT, source TEXT)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            question_id TEXT PRIMARY KEY, seen INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0, last_result INTEGER DEFAULT 0,
            ease REAL DEFAULT 2.3, interval_d REAL DEFAULT 0,
            next_review REAL DEFAULT 0)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)
    """)
    conn.commit()
    for k, v in {
        "total_answered": "0", "total_correct": "0", "xp": "0",
        "best_combo": "0", "day_streak": "0", "last_active": "",
    }.items():
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)",
                    (k, v))
    conn.commit()
    conn.close()


def _conn():
    if _DB_PATH is None:
        raise RuntimeError("init_db() doit etre appele avant tout acces.")
    c = sqlite3.connect(_DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def setting_get(key, default=None):
    conn = _conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def setting_set(key, value):
    conn = _conn()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
                 (key, str(value)))
    conn.commit()
    conn.close()


def setting_int(key, default=0):
    try:
        return int(setting_get(key, default))
    except (TypeError, ValueError):
        return default


def reset_progress():
    """Efface toute la progression (sans supprimer le fichier)."""
    conn = _conn()
    conn.execute("DELETE FROM progress")
    conn.execute("DELETE FROM questions")
    conn.execute("UPDATE settings SET value='0' WHERE key IN "
                 "('total_answered','total_correct','xp','best_combo','day_streak')")
    conn.execute("UPDATE settings SET value='' WHERE key='last_active'")
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# Repetition espacee (inspiree de SM-2)
# --------------------------------------------------------------------------

def _schedule(ease, interval_d, success):
    now = time.time()
    if success:
        interval_d = 1.0 if interval_d < 1 else interval_d * ease
        ease = min(2.8, ease + 0.05)
    else:
        interval_d = 1.0 / (60 * 24)  # ~1 minute
        ease = max(1.3, ease - 0.2)
    return ease, interval_d, now + interval_d * 86400


def record_answer(q, success):
    """Enregistre une reponse et met a jour progression + statistiques."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO questions
        (id, question, correct, incorrect, category, difficulty, anecdote, source)
        VALUES (?,?,?,?,?,?,?,?)
    """, (q["id"], q["question"], q["correct"], json.dumps(q["incorrect"]),
          q.get("category", ""), q.get("difficulty", ""),
          q.get("anecdote", ""), q.get("source", "")))

    row = cur.execute("SELECT * FROM progress WHERE question_id=?",
                       (q["id"],)).fetchone()
    if row:
        ease, interval_d = row["ease"], row["interval_d"]
        seen, correct = row["seen"], row["correct"]
    else:
        ease, interval_d, seen, correct = 2.3, 0.0, 0, 0

    ease, interval_d, next_review = _schedule(ease, interval_d, success)
    cur.execute("""
        INSERT OR REPLACE INTO progress
        (question_id, seen, correct, last_result, ease, interval_d, next_review)
        VALUES (?,?,?,?,?,?,?)
    """, (q["id"], seen + 1, correct + (1 if success else 0),
          1 if success else 0, ease, interval_d, next_review))
    conn.commit()
    conn.close()

    setting_set("total_answered", setting_int("total_answered") + 1)
    if success:
        setting_set("total_correct", setting_int("total_correct") + 1)
        setting_set("xp", setting_int("xp") + XP_PER_CORRECT)


def due_questions(limit=20):
    conn = _conn()
    rows = conn.execute("""
        SELECT q.* FROM questions q JOIN progress p ON p.question_id = q.id
        WHERE p.next_review <= ? ORDER BY p.next_review ASC LIMIT ?
    """, (time.time(), limit)).fetchall()
    conn.close()
    return [_row_to_question(r) for r in rows]


def due_count():
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) AS n FROM progress WHERE next_review<=?",
                      (time.time(),)).fetchone()["n"]
    conn.close()
    return n


def _row_to_question(r):
    return {
        "id": r["id"], "question": r["question"], "correct": r["correct"],
        "incorrect": json.loads(r["incorrect"]), "category": r["category"] or "",
        "difficulty": r["difficulty"] or "", "anecdote": r["anecdote"] or "",
        "source": r["source"] or "",
    }


# --------------------------------------------------------------------------
# Statistiques
# --------------------------------------------------------------------------

def level_info():
    xp = setting_int("xp")
    level = 1 + xp // XP_PER_LEVEL
    title = LEVEL_TITLES[min(level - 1, len(LEVEL_TITLES) - 1)]
    return level, title, xp, xp % XP_PER_LEVEL


def update_day_streak():
    today = date.today().isoformat()
    last = setting_get("last_active", "")
    if last == today:
        return
    streak = setting_int("day_streak")
    if last:
        try:
            streak = streak + 1 if (date.today() - date.fromisoformat(last)).days == 1 else 1
        except ValueError:
            streak = 1
    else:
        streak = 1
    setting_set("day_streak", streak)
    setting_set("last_active", today)


def global_stats():
    total = setting_int("total_answered")
    correct = setting_int("total_correct")
    level, title, xp, xp_in = level_info()
    return {
        "total": total, "correct": correct,
        "accuracy": round(100 * correct / total) if total else 0,
        "level": level, "title": title, "xp": xp, "xp_in_level": xp_in,
        "xp_per_level": XP_PER_LEVEL,
        "best_combo": setting_int("best_combo"),
        "day_streak": setting_int("day_streak"),
        "due": due_count(),
    }


def category_stats(limit=12):
    conn = _conn()
    rows = conn.execute("""
        SELECT q.category AS cat, SUM(p.seen) AS seen, SUM(p.correct) AS ok
        FROM questions q JOIN progress p ON p.question_id = q.id
        WHERE q.category != '' GROUP BY q.category
        ORDER BY seen DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    out = []
    for r in rows:
        seen = r["seen"] or 0
        ok = r["ok"] or 0
        if seen:
            out.append({"category": _prettify(r["cat"]), "seen": seen,
                        "correct": ok, "pct": round(100 * ok / seen)})
    return out


def _prettify(cat):
    cat = (cat or "").replace("_", " ").replace(":", " -").strip()
    return cat[:1].upper() + cat[1:] if cat else "Divers"


# --------------------------------------------------------------------------
# Reseau et sources d'API
# --------------------------------------------------------------------------

def _ssl_context():
    try:
        if certifi:
            return ssl.create_default_context(cafile=certifi.where())
        return ssl.create_default_context()
    except Exception:
        return None


def _http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = _ssl_context() if url.startswith("https") else None
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT, context=ctx) as r:
        return r.read().decode("utf-8", errors="replace")


def _make_id(text):
    norm = " ".join(text.strip().lower().split())
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def _normalize(question, correct, incorrect, category="", difficulty="",
               anecdote="", source=""):
    question = html.unescape(str(question)).strip()
    correct = html.unescape(str(correct)).strip()
    incorrect = [html.unescape(str(x)).strip() for x in incorrect if str(x).strip()]
    if not question or not correct or len(incorrect) < 1:
        return None
    return {
        "id": _make_id(question), "question": question, "correct": correct,
        "incorrect": incorrect[:3], "category": _prettify(category),
        "difficulty": str(difficulty).strip(),
        "anecdote": html.unescape(str(anecdote)).strip(), "source": source,
    }


# --- Source 1 : QuizzAPI (questions en francais) --------------------------

def fetch_quizzapi(amount=10):
    url = "https://quizzapi.jomoreschi.fr/api/v1/quiz?" + urllib.parse.urlencode(
        {"limit": max(1, min(amount, 40))})
    data = json.loads(_http_get(url))
    out = []
    for it in data.get("quizzes", []):
        q = _normalize(it.get("question", ""), it.get("answer", ""),
                       it.get("badAnswers", []) or it.get("bad_answers", []),
                       category=it.get("category", ""),
                       difficulty=it.get("difficulty", ""),
                       anecdote=it.get("anecdote", ""), source="QuizzAPI (FR)")
        if q:
            out.append(q)
    return out


# --- Sources de "decouverte" (faits, articles) ----------------------------

def fetch_wiki_fact():
    """Resume d'un article Wikipedia francais aleatoire."""
    data = json.loads(_http_get(
        "https://fr.wikipedia.org/api/rest_v1/page/random/summary"))
    return {
        "title": data.get("title", "Article"),
        "text": data.get("extract", ""),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
        "source": "Wikipedia",
    }


def fetch_useless_fact():
    """Un fait insolite, en francais."""
    data = json.loads(_http_get(
        "https://uselessfacts.jsph.pl/api/v2/facts/random?language=fr"))
    return {
        "title": "Le saviez-vous ?",
        "text": data.get("text", ""),
        "url": data.get("source_url", ""),
        "source": "Useless Facts",
    }


def get_facts(n=4):
    """Recupere n faits en melangeant les sources de decouverte."""
    fetchers = [fetch_wiki_fact, fetch_useless_fact]
    out = []
    attempts = 0
    while len(out) < n and attempts < n * 3:
        attempts += 1
        try:
            f = random.choice(fetchers)()
            if f["text"]:
                out.append(f)
        except Exception:
            break
    return out


# --------------------------------------------------------------------------
# Jeu de questions de secours (hors-ligne)
# --------------------------------------------------------------------------

OFFLINE_QUESTIONS = [
    ("Quelle est la capitale de l'Australie ?", "Canberra",
     ["Sydney", "Melbourne", "Perth"], "Geographie",
     "Sydney est la plus grande ville, mais Canberra fut creee comme capitale en 1913."),
    ("Combien d'os compte le squelette humain adulte ?", "206",
     ["198", "212", "224"], "Sciences",
     "Le bebe nait avec environ 270 os ; certains fusionnent durant la croissance."),
    ("Qui a peint la Joconde ?", "Leonard de Vinci",
     ["Michel-Ange", "Raphael", "Botticelli"], "Art",
     "Le tableau, dit 'Mona Lisa', est expose au musee du Louvre."),
    ("En quelle annee a commence la Revolution francaise ?", "1789",
     ["1776", "1799", "1804"], "Histoire",
     "La prise de la Bastille, le 14 juillet 1789, en est l'evenement symbolique."),
    ("Quelle est la planete la plus proche du Soleil ?", "Mercure",
     ["Venus", "Mars", "La Terre"], "Sciences",
     "Mercure fait le tour du Soleil en seulement 88 jours."),
    ("Qui a ecrit 'Les Miserables' ?", "Victor Hugo",
     ["Emile Zola", "Gustave Flaubert", "Honore de Balzac"], "Litterature",
     "Le roman est publie en 1862."),
    ("Quel est le plus grand ocean du monde ?", "L'ocean Pacifique",
     ["L'ocean Atlantique", "L'ocean Indien", "L'ocean Arctique"], "Geographie",
     "Le Pacifique couvre environ un tiers de la surface du globe."),
    ("Quelle est la monnaie du Japon ?", "Le yen",
     ["Le won", "Le yuan", "Le ringgit"], "Culture generale",
     "Le yen est introduit en 1871."),
    ("Quel organe du corps humain pompe le sang ?", "Le coeur",
     ["Le foie", "Les poumons", "Les reins"], "Sciences",
     "Le coeur bat environ 100 000 fois par jour."),
    ("Qui a formule la theorie de la relativite ?", "Albert Einstein",
     ["Isaac Newton", "Niels Bohr", "Galilee"], "Sciences",
     "La relativite restreinte date de 1905."),
    ("Quelle est la plus haute montagne du monde ?", "L'Everest",
     ["Le K2", "Le mont Blanc", "Le Kilimandjaro"], "Geographie",
     "L'Everest culmine a environ 8 849 metres."),
    ("Combien de joueurs compte une equipe de football sur le terrain ?", "11",
     ["9", "10", "12"], "Sport", "Onze joueurs par equipe, dont un gardien."),
    ("Quel est le symbole chimique de l'or ?", "Au",
     ["Or", "Ag", "Gd"], "Sciences", "Au vient du latin 'aurum'."),
    ("Qui a decouvert la penicilline ?", "Alexander Fleming",
     ["Louis Pasteur", "Marie Curie", "Robert Koch"], "Sciences",
     "Fleming l'observa par hasard en 1928."),
    ("Quelle est la capitale du Canada ?", "Ottawa",
     ["Toronto", "Montreal", "Vancouver"], "Geographie",
     "Toronto est la plus grande ville, mais Ottawa est la capitale federale."),
    ("En quelle annee l'homme a-t-il marche sur la Lune ?", "1969",
     ["1959", "1971", "1965"], "Histoire",
     "Neil Armstrong, lors de la mission Apollo 11."),
    ("Quel est le plus grand mammifere vivant ?", "La baleine bleue",
     ["L'elephant d'Afrique", "Le cachalot", "La girafe"], "Sciences",
     "Elle peut depasser 150 tonnes."),
    ("Combien de continents y a-t-il sur Terre ?", "7",
     ["5", "6", "8"], "Geographie",
     "Le decompte varie : la France en enseigne souvent 6."),
    ("Quel gaz les plantes absorbent-elles pour la photosynthese ?",
     "Le dioxyde de carbone", ["L'oxygene", "L'azote", "L'hydrogene"],
     "Sciences", "Elles rejettent de l'oxygene en retour."),
    ("Quelle langue compte le plus de locuteurs natifs au monde ?",
     "Le mandarin", ["L'anglais", "L'espagnol", "L'hindi"], "Culture generale",
     "Plus de 900 millions de locuteurs natifs."),
]


def offline_questions(amount=10):
    pool = []
    for q, c, bad, cat, anec in OFFLINE_QUESTIONS:
        nq = _normalize(q, c, bad, category=cat, difficulty="moyen",
                        anecdote=anec, source="Hors-ligne")
        if nq:
            pool.append(nq)
    random.shuffle(pool)
    return pool[:amount]


# --------------------------------------------------------------------------
# Recuperation unifiee (questions en francais)
# --------------------------------------------------------------------------

def get_questions(amount=10):
    """
    Renvoie (liste_de_questions, origine). Les questions sont en francais,
    fournies par QuizzAPI. Plusieurs appels sont combines : chaque appel
    renvoie un lot aleatoire, ce qui agrandit le reservoir effectif et varie
    les themes. En l'absence de connexion, l'application bascule sur la
    banque de questions integree (hors-ligne).
    """
    bag = []
    calls = 3 if amount > 12 else 2
    for _ in range(calls):
        try:
            qs = fetch_quizzapi(40)
            if qs:
                bag.extend(qs)
        except Exception:
            continue

    # Deduplication
    seen, uniq = set(), []
    for q in bag:
        if q["id"] not in seen:
            seen.add(q["id"])
            uniq.append(q)

    if not uniq:
        return offline_questions(amount), "hors-ligne"

    # Si QuizzAPI a renvoye trop peu de questions, on complete hors-ligne.
    if len(uniq) < amount:
        for q in offline_questions(amount):
            if q["id"] not in seen:
                seen.add(q["id"])
                uniq.append(q)

    random.shuffle(uniq)
    return uniq[:amount], "en ligne"
