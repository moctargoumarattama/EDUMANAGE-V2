import argparse
import gzip
import json
import re
import shutil
import sqlite3
import sys
import tempfile
import urllib.request
from pathlib import Path


DEFAULT_URL = "https://kaikki.org/dictionary/Arabic/kaikki.org-dictionary-Arabic.jsonl"
DEFAULT_DB = Path("instance") / "ecole.db"
DEFAULT_DOWNLOAD = Path("instance") / "imports" / "kaikki-arabic.jsonl"
BATCH_SIZE = 1000

ARABIC_CHAR_RE = re.compile(r"[\u0600-\u06FF]")
ARABIC_CLEAN_RE = re.compile(r"[^\u0600-\u06FF0-9\s]")
QUOTE_RE = re.compile(r"[“\"']([^\"”']+)[\"”']")
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
    "comparative of ",
    "superlative of ",
)


def normalize_arabic(value):
    if not value:
        return ""
    value = "".join(char for char in value if not ("\u064B" <= char <= "\u065F"))
    value = value.replace("\u0640", "")
    value = ARABIC_CLEAN_RE.sub(" ", value)
    return " ".join(value.split()).strip()


def looks_arabic(value):
    return bool(value and ARABIC_CHAR_RE.search(value))


def simplify_gloss(gloss):
    if not gloss:
        return None
    gloss = " ".join(str(gloss).split()).strip(" -;,.")
    if not gloss:
        return None

    lowered = gloss.lower()
    quoted = QUOTE_RE.findall(gloss)

    for prefix in TECHNICAL_PREFIXES:
        if lowered.startswith(prefix):
            if quoted:
                return quoted[-1].strip()[:300]
            return None

    if lowered.startswith("verbal noun of "):
        if "," in gloss:
            tail = gloss.split(",", 1)[1].strip(" .;")
            if tail:
                return tail[:300]
        if quoted:
            return quoted[-1].strip()[:300]
        return None

    if "letter of the arabic alphabet" in lowered:
        return "Arabic letter"

    # Remove long parenthetical explanations and keep the learner-facing core.
    gloss = re.sub(r"\s*\([^)]{8,}\)", "", gloss)
    gloss = gloss.split(";", 1)[0].strip(" -;,.")
    if "): " in gloss:
        gloss = gloss.split("): ", 1)[1].strip(" -;,.")
    if ": " in gloss and len(gloss) > 80:
        gloss = gloss.split(": ", 1)[0].strip(" -;,.")
    if "," in gloss and len(gloss) > 90:
        gloss = gloss.split(",", 1)[0].strip(" -;,.")

    return gloss[:300] if gloss else None


def gloss_score(gloss):
    if not gloss:
        return -10_000

    lowered = gloss.lower()
    score = 100

    if any(lowered.startswith(prefix) for prefix in TECHNICAL_PREFIXES):
        score -= 80
    if lowered.startswith("verbal noun of "):
        score -= 70
    if "letter of the arabic alphabet" in lowered:
        score -= 40
    if "(" in gloss or ")" in gloss:
        score -= 10
    if ";" in gloss:
        score -= 10
    if len(gloss) > 120:
        score -= 25
    if len(gloss.split()) > 12:
        score -= 15
    if 2 <= len(gloss.split()) <= 6:
        score += 10

    return score


def pick_gloss(entry):
    best = None
    best_score = -10_000

    for sense in entry.get("senses", []):
        glosses = sense.get("glosses") or []
        for gloss in glosses:
            simplified = simplify_gloss(gloss)
            score = gloss_score(gloss) + (5 if simplified else 0)
            candidate = simplified or " ".join(str(gloss).split()).strip()
            if candidate and score > best_score:
                best = candidate[:300]
                best_score = score

    return best


def pick_example(entry):
    for sense in entry.get("senses", []):
        for example in sense.get("examples") or []:
            if isinstance(example, dict):
                text = example.get("text") or example.get("example")
            else:
                text = str(example)
            cleaned = " ".join(str(text or "").split()).strip()
            if looks_arabic(cleaned):
                return cleaned[:5000]
    return None


def pick_audio(entry):
    for sound in entry.get("sounds") or []:
        if not isinstance(sound, dict):
            continue
        for key in ("mp3_url", "ogg_url"):
            value = sound.get(key)
            if value:
                return str(value)[:500]
    return None


def pick_transliteration(entry):
    candidates = []

    for form in entry.get("forms") or []:
        if not isinstance(form, dict):
            continue
        tags = {str(tag).lower() for tag in form.get("tags") or []}
        if {"romanization", "romanisation", "transliteration"} & tags:
            value = form.get("form")
            if value:
                candidates.append(str(value))

    for sound in entry.get("sounds") or []:
        if not isinstance(sound, dict):
            continue
        tags = {str(tag).lower() for tag in sound.get("tags") or []}
        if {"romanization", "romanisation", "transliteration"} & tags:
            value = sound.get("text") or sound.get("ipa")
            if value:
                candidates.append(str(value))

    for candidate in candidates:
        cleaned = " ".join(candidate.split()).strip()
        if cleaned and not looks_arabic(cleaned):
            return cleaned[:200]
    return None


def iter_jsonl(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def download_file(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, open(destination, "wb") as target:
        shutil.copyfileobj(response, target)


def upsert_rows(conn, rows):
    conn.executemany(
        """
        INSERT INTO vocabulaire (
            mot_arabe,
            translitteration,
            traduction_fr,
            traduction_en,
            traduction_es,
            audio_url,
            exemple_phrase
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(mot_arabe) DO UPDATE SET
            translitteration = COALESCE(excluded.translitteration, vocabulaire.translitteration),
            traduction_fr = COALESCE(vocabulaire.traduction_fr, excluded.traduction_fr),
            traduction_en = COALESCE(excluded.traduction_en, vocabulaire.traduction_en),
            traduction_es = COALESCE(vocabulaire.traduction_es, excluded.traduction_es),
            audio_url = COALESCE(vocabulaire.audio_url, excluded.audio_url),
            exemple_phrase = COALESCE(vocabulaire.exemple_phrase, excluded.exemple_phrase)
        """,
        rows,
    )


def ensure_table_exists(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vocabulaire (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mot_arabe VARCHAR(200) NOT NULL UNIQUE,
            translitteration VARCHAR(200),
            traduction_fr VARCHAR(300),
            traduction_en VARCHAR(300),
            traduction_es VARCHAR(300),
            audio_url VARCHAR(500),
            exemple_phrase TEXT,
            date_ajout DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def import_dump(db_path, dump_path, min_words=10000):
    conn = sqlite3.connect(db_path)
    ensure_table_exists(conn)

    conn.execute("DELETE FROM vocabulaire WHERE mot_arabe LIKE '%?%' OR mot_arabe IS NULL OR TRIM(mot_arabe) = ''")
    conn.commit()

    imported = 0
    batch = []
    seen = set()

    for entry in iter_jsonl(dump_path):
        lang_code = (entry.get("lang_code") or "").lower()
        if lang_code != "ar":
            continue

        raw_word = entry.get("word") or entry.get("title") or ""
        word = normalize_arabic(str(raw_word))
        if not word or not looks_arabic(word):
            continue
        if word in seen:
            continue

        gloss = pick_gloss(entry)
        transliteration = pick_transliteration(entry)
        audio_url = pick_audio(entry)
        example = pick_example(entry)

        batch.append((word, transliteration, None, gloss, None, audio_url, example))
        seen.add(word)

        if len(batch) >= BATCH_SIZE:
            upsert_rows(conn, batch)
            conn.commit()
            imported += len(batch)
            print(f"Imported {imported} entries...", flush=True)
            batch.clear()

    if batch:
        upsert_rows(conn, batch)
        conn.commit()
        imported += len(batch)

    total = conn.execute("SELECT COUNT(*) FROM vocabulaire").fetchone()[0]
    with_audio = conn.execute("SELECT COUNT(*) FROM vocabulaire WHERE audio_url IS NOT NULL AND audio_url != ''").fetchone()[0]
    conn.close()

    if total < min_words:
        raise RuntimeError(f"Import finished, but only {total} entries are available (expected at least {min_words}).")

    return total, with_audio


def parse_args():
    parser = argparse.ArgumentParser(description="Download and import Kaikki Arabic dictionary into the local vocabulaire table.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Kaikki JSONL download URL")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to the SQLite database")
    parser.add_argument("--download-path", default=str(DEFAULT_DOWNLOAD), help="Path where the dump will be stored temporarily")
    parser.add_argument("--local-file", help="Use an existing local JSONL or JSONL.GZ file instead of downloading")
    parser.add_argument("--keep-download", action="store_true", help="Keep the downloaded dump file after import")
    parser.add_argument("--min-words", type=int, default=10000, help="Fail if fewer than this many entries are imported")
    return parser.parse_args()


def main():
    args = parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    if args.local_file:
        dump_path = Path(args.local_file)
        if not dump_path.exists():
            raise FileNotFoundError(f"Local dump not found: {dump_path}")
    else:
        dump_path = Path(args.download_path)
        print(f"Downloading dump from {args.url} ...", flush=True)
        download_file(args.url, dump_path)
        print(f"Dump saved to {dump_path}", flush=True)

    try:
        total, with_audio = import_dump(db_path, dump_path, min_words=args.min_words)
    finally:
        if not args.local_file and not args.keep_download and dump_path.exists():
            dump_path.unlink()

    print(f"Import complete: {total} entries in vocabulaire, {with_audio} with audio.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
