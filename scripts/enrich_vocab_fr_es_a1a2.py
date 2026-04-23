import argparse
import json
import re
import shutil
import sqlite3
import sys
import urllib.request
from pathlib import Path

from import_kaikki_vocab import iter_jsonl, normalize_arabic, pick_gloss


FR_URL = "https://kaikki.org/frwiktionary/Arabe/kaikki.org-dictionary-Arabe.jsonl"
ES_URL = "https://kaikki.org/eswiktionary/%C3%81rabe/kaikki.org-dictionary-%C3%81rabe.jsonl"
DEFAULT_DB = Path("instance") / "ecole.db"
IMPORT_DIR = Path("instance") / "imports"

COMMON_SHORT_WORDS = {
    "و", "في", "من", "مع", "لا", "ما", "هل", "عن", "إلى", "على", "هو", "هي", "أنا", "أنت", "نعم", "ثم",
}
TOKEN_RE = re.compile(r"[a-zà-ÿA-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ'’-]*")

TECHNICAL_PREFIXES = (
    "alternative form of ",
    "ellipsis of ",
    "plural of ",
    "singular of ",
    "feminine of ",
    "masculine of ",
    "dual of ",
    "obsolete spelling of ",
    "misspelling of ",
    "active participle of ",
    "passive participle of ",
    "verbal noun of ",
)

A1_THEMES = {
    "salutations": {
        "level": "A1",
        "keywords": [
            "hello", "welcome", "goodbye", "hi", "peace", "thanks", "please", "yes", "no", "question",
            "bonjour", "salut", "merci", "oui", "non", "hola", "gracias", "adiós",
        ],
    },
    "ecole": {
        "level": "A1",
        "keywords": [
            "school", "book", "pen", "teacher", "student", "class", "academy",
            "école", "livre", "stylo", "professeur", "élève", "clase", "libro", "escuela",
        ],
    },
    "maison": {
        "level": "A1",
        "keywords": [
            "house", "home", "room", "door", "window", "family",
            "maison", "famille", "porte", "fenêtre", "casa", "familia", "puerta", "ventana",
        ],
    },
    "quotidien": {
        "level": "A1",
        "keywords": [
            "eat", "drink", "sleep", "go", "come", "read", "write", "day", "night", "morning", "water",
            "manger", "boire", "dormir", "jour", "nuit", "eau", "comer", "beber", "día", "agua",
        ],
    },
    "nombres": {
        "level": "A1",
        "keywords": [
            "one", "two", "three", "four", "five", "number", "time",
            "un", "deux", "trois", "quatre", "cinq", "numéro", "uno", "dos", "tres", "cuatro", "cinco",
        ],
    },
    "nature": {
        "level": "A1",
        "keywords": [
            "sun", "moon", "water", "tree", "fish", "dog", "cat", "bird",
            "soleil", "lune", "arbre", "poisson", "chien", "chat", "sol", "luna", "árbol", "pez", "perro", "gato",
        ],
    },
    "corps": {
        "level": "A1",
        "keywords": [
            "hand", "head", "eye", "ear", "mouth", "heart",
            "main", "tête", "œil", "oreille", "bouche", "mano", "cabeza", "ojo", "boca",
        ],
    },
    "pays_courants": {
        "level": "A2",
        "keywords": [
            "morocco", "algeria", "egypt", "tunisia", "country", "city",
            "maroc", "algérie", "égypte", "tunisie", "pays", "ville",
            "marruecos", "argelia", "egipto", "túnez", "país", "ciudad",
        ],
    },
    "transport": {
        "level": "A2",
        "keywords": [
            "car", "bus", "train", "road", "travel", "airport",
            "voiture", "bus", "train", "route", "voyage", "avion",
            "coche", "autobús", "tren", "carretera", "viaje", "aeropuerto",
        ],
    },
    "sante": {
        "level": "A2",
        "keywords": [
            "doctor", "hospital", "pain", "medicine", "health",
            "docteur", "hôpital", "douleur", "médecine", "salud", "doctor", "hospital", "dolor", "medicina",
        ],
    },
    "travail": {
        "level": "A2",
        "keywords": [
            "work", "job", "office", "meeting", "business",
            "travail", "emploi", "bureau", "travajo", "oficina", "negocio",
        ],
    },
    "emotion": {
        "level": "A2",
        "keywords": [
            "happy", "sad", "love", "fear", "anger", "excitement",
            "heureux", "triste", "amour", "peur", "colère", "feliz", "triste", "amor", "miedo",
        ],
    },
}


def download_file(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, open(destination, "wb") as target:
        shutil.copyfileobj(response, target)


def build_gloss_map(path):
    mapping = {}
    for entry in iter_jsonl(path):
        raw_word = entry.get("word") or entry.get("title") or ""
        word = normalize_arabic(str(raw_word))
        if not word:
            continue
        gloss = pick_gloss(entry)
        if gloss and word not in mapping:
            mapping[word] = gloss[:300]
    return mapping


def is_technical(gloss):
    lowered = (gloss or "").lower().strip()
    return any(lowered.startswith(prefix) for prefix in TECHNICAL_PREFIXES) or "letter of the arabic alphabet" in lowered


def classify_entry(word, fr, en, es):
    text = " ".join(filter(None, [fr, en, es])).lower()
    if not text:
        return False, None, None
    if is_technical(en or fr or es):
        return False, None, None
    if len(word) == 1 and word not in COMMON_SHORT_WORDS:
        return False, None, None
    if len(text) > 220:
        return False, None, None

    tokens = set(TOKEN_RE.findall(text))
    best = None
    best_score = 0
    for theme, config in A1_THEMES.items():
        score = 0
        for keyword in config["keywords"]:
            lowered = keyword.lower()
            if " " in lowered:
                if lowered in text:
                    score += 2
            elif lowered in tokens:
                score += 1
        if score > best_score:
            best = (config["level"], theme)
            best_score = score

    if best_score < 1:
        return False, None, None
    return True, best[0], best[1]


def ensure_columns(conn):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(vocabulaire)")}
    if "niveau_cefr" not in existing:
        conn.execute("ALTER TABLE vocabulaire ADD COLUMN niveau_cefr VARCHAR(5)")
    if "theme" not in existing:
        conn.execute("ALTER TABLE vocabulaire ADD COLUMN theme VARCHAR(100)")
    if "est_pedagogique" not in existing:
        conn.execute("ALTER TABLE vocabulaire ADD COLUMN est_pedagogique BOOLEAN NOT NULL DEFAULT 0")
    conn.commit()


def enrich(db_path, fr_path, es_path):
    fr_map = build_gloss_map(fr_path)
    es_map = build_gloss_map(es_path)

    conn = sqlite3.connect(db_path)
    ensure_columns(conn)
    cur = conn.cursor()

    rows = cur.execute(
        "SELECT id, mot_arabe, traduction_fr, traduction_en, traduction_es FROM vocabulaire"
    ).fetchall()

    updated_fr = 0
    updated_es = 0
    pedagogical = 0
    a1 = 0
    a2 = 0

    updates = []
    for row_id, mot, fr, en, es in rows:
        normalized = normalize_arabic(mot)
        new_fr = fr or fr_map.get(normalized)
        new_es = es or es_map.get(normalized)
        if not fr and new_fr:
            updated_fr += 1
        if not es and new_es:
            updated_es += 1

        est_pedagogique, niveau, theme = classify_entry(normalized, new_fr, en, new_es)
        if est_pedagogique:
            pedagogical += 1
            if niveau == "A1":
                a1 += 1
            elif niveau == "A2":
                a2 += 1

        updates.append((new_fr, new_es, 1 if est_pedagogique else 0, niveau, theme, row_id))

    cur.executemany(
        """
        UPDATE vocabulaire
        SET traduction_fr = ?,
            traduction_es = ?,
            est_pedagogique = ?,
            niveau_cefr = ?,
            theme = ?
        WHERE id = ?
        """,
        updates,
    )
    conn.commit()
    conn.close()

    return {
        "updated_fr": updated_fr,
        "updated_es": updated_es,
        "pedagogical": pedagogical,
        "a1": a1,
        "a2": a2,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Enrich Arabic vocabulary with French/Spanish glosses and classify A1/A2.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--fr-url", default=FR_URL)
    parser.add_argument("--es-url", default=ES_URL)
    parser.add_argument("--fr-file")
    parser.add_argument("--es-file")
    parser.add_argument("--keep-download", action="store_true")
    return parser.parse_args()


def resolve_dump(path_arg, default_url, default_name):
    if path_arg:
        path = Path(path_arg)
        if not path.exists():
            raise FileNotFoundError(path)
        return path, False
    path = IMPORT_DIR / default_name
    download_file(default_url, path)
    return path, True


def main():
    args = parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    fr_path, fr_downloaded = resolve_dump(args.fr_file, args.fr_url, "kaikki-fr-arabe.jsonl")
    es_path, es_downloaded = resolve_dump(args.es_file, args.es_url, "kaikki-es-arabe.jsonl")

    try:
        result = enrich(db_path, fr_path, es_path)
    finally:
        if fr_downloaded and not args.keep_download and fr_path.exists():
            fr_path.unlink()
        if es_downloaded and not args.keep_download and es_path.exists():
            es_path.unlink()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
