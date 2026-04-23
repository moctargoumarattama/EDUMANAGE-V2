import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

ARGOS_ROOT = Path("instance") / "argos_runtime"
os.environ.setdefault("XDG_CONFIG_HOME", str(ARGOS_ROOT / "config"))
os.environ.setdefault("XDG_CACHE_HOME", str(ARGOS_ROOT / "cache"))
os.environ.setdefault("XDG_DATA_HOME", str(ARGOS_ROOT / "data"))

import argostranslate.package
import argostranslate.sbd
import argostranslate.translate


DEFAULT_DB = Path("instance") / "ecole.db"


def _offline_split_sentences(self, text):
    text = (text or "").strip()
    return [text] if text else []


argostranslate.sbd.StanzaSentencizer.split_sentences = _offline_split_sentences

TECH_PREFIXES = (
    "alternative form of ",
    "plural of ",
    "singular of ",
    "dual of ",
    "feminine of ",
    "masculine of ",
    "accusative/genitive feminine of ",
    "accusative/genitive masculine of ",
    "nominative feminine of ",
    "nominative masculine of ",
    "ellipsis of ",
    "obsolete spelling of ",
    "misspelling of ",
    "active participle of ",
    "passive participle of ",
)

QUOTE_RE = re.compile(r"[“\"']([^\"”']+)[\"”']")


def simplify_english_gloss(gloss):
    if not gloss:
        return None
    gloss = " ".join(str(gloss).split()).strip(" -;,.")
    lowered = gloss.lower()

    if "letter of the arabic alphabet" in lowered:
        return "Arabic letter"

    for prefix in TECH_PREFIXES:
        if lowered.startswith(prefix):
            target = gloss[len(prefix):].strip(" .;,")
            quoted = QUOTE_RE.findall(gloss)
            if quoted:
                target = quoted[-1].strip()

            label = {
                "alternative form of ": "variant of",
                "plural of ": "plural of",
                "singular of ": "singular of",
                "dual of ": "dual form of",
                "feminine of ": "feminine form of",
                "masculine of ": "masculine form of",
                "accusative/genitive feminine of ": "feminine form of",
                "accusative/genitive masculine of ": "masculine form of",
                "nominative feminine of ": "feminine form of",
                "nominative masculine of ": "masculine form of",
                "ellipsis of ": "short form of",
                "obsolete spelling of ": "old spelling of",
                "misspelling of ": "incorrect spelling of",
                "active participle of ": "active participle of",
                "passive participle of ": "passive participle of",
            }[prefix]
            return f"{label} {target}".strip()

    if lowered.startswith("verbal noun of "):
        if "," in gloss:
            tail = gloss.split(",", 1)[1].strip(" .;")
            if tail:
                return tail
        quoted = QUOTE_RE.findall(gloss)
        if quoted:
            return quoted[-1].strip()
        return "verbal noun"

    gloss = re.sub(r"\s*\([^)]{8,}\)", "", gloss)
    gloss = gloss.split(";", 1)[0].strip(" -;,.")
    if len(gloss) > 140 and "," in gloss:
        gloss = gloss.split(",", 1)[0].strip(" -;,.")
    return gloss[:300] if gloss else None


def is_missing(value):
    return value is None or not str(value).strip()


def install_translation_package(from_code, to_code):
    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
    to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)
    if from_lang and to_lang and from_lang.get_translation(to_lang):
        return

    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    package = next(
        (
            pkg for pkg in available_packages
            if pkg.from_code == from_code and pkg.to_code == to_code
        ),
        None,
    )
    if package is None:
        raise RuntimeError(f"No Argos package available for {from_code}->{to_code}")
    download_path = package.download()
    argostranslate.package.install_from_path(download_path)


def get_translation(from_code, to_code):
    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
    to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)
    if not from_lang:
        raise RuntimeError(f"Source language not installed: {from_code}")
    if not to_lang:
        raise RuntimeError(f"Target language not installed: {to_code}")
    translation = from_lang.get_translation(to_lang)
    if translation is None:
        raise RuntimeError(f"Translation not installed: {from_code}->{to_code}")
    return translation


def enrich(db_path, limit=None, batch_size=200):
    install_translation_package("en", "fr")
    install_translation_package("en", "es")

    en_fr = get_translation("en", "fr")
    en_es = get_translation("en", "es")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    query = """
        SELECT id, mot_arabe, traduction_en, traduction_fr, traduction_es
        FROM vocabulaire
        WHERE traduction_en IS NOT NULL AND TRIM(traduction_en) != ''
        ORDER BY
            CASE
                WHEN traduction_fr IS NULL OR TRIM(traduction_fr) = '' THEN 0
                ELSE 1
            END,
            CASE
                WHEN traduction_es IS NULL OR TRIM(traduction_es) = '' THEN 0
                ELSE 1
            END,
            id
    """
    if limit:
        query += f"\nLIMIT {int(limit)}"
    rows = cur.execute(query).fetchall()

    translated_fr = 0
    translated_es = 0
    simplified_en = 0
    updates = []
    for row_id, mot, en, fr, es in rows:
        simple_en = simplify_english_gloss(en) or en
        if simple_en != en:
            simplified_en += 1

        new_fr = fr
        new_es = es

        if is_missing(fr):
            try:
                translated = en_fr.translate(simple_en).strip()
            except Exception:
                translated = ""
            new_fr = translated or None
            if new_fr:
                translated_fr += 1

        if is_missing(es):
            try:
                translated = en_es.translate(simple_en).strip()
            except Exception:
                translated = ""
            new_es = translated or None
            if new_es:
                translated_es += 1

        updates.append((simple_en[:300] if simple_en else None, new_fr, new_es, row_id))

        if len(updates) >= batch_size:
            cur.executemany(
                """
                UPDATE vocabulaire
                SET traduction_en = ?, traduction_fr = ?, traduction_es = ?
                WHERE id = ?
                """,
                updates,
            )
            conn.commit()
            updates.clear()

    if updates:
        cur.executemany(
            """
            UPDATE vocabulaire
            SET traduction_en = ?, traduction_fr = ?, traduction_es = ?
            WHERE id = ?
            """,
            updates,
        )
        conn.commit()

    remaining = {
        "missing_fr": cur.execute(
            "SELECT COUNT(*) FROM vocabulaire WHERE traduction_en IS NOT NULL AND TRIM(traduction_en) != '' AND (traduction_fr IS NULL OR TRIM(traduction_fr) = '')"
        ).fetchone()[0],
        "missing_es": cur.execute(
            "SELECT COUNT(*) FROM vocabulaire WHERE traduction_en IS NOT NULL AND TRIM(traduction_en) != '' AND (traduction_es IS NULL OR TRIM(traduction_es) = '')"
        ).fetchone()[0],
    }
    conn.close()

    return {
        "translated_fr": translated_fr,
        "translated_es": translated_es,
        "simplified_en": simplified_en,
        **remaining,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Fill missing FR/ES translations from English using offline Argos Translate.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=200)
    return parser.parse_args()


def main():
    args = parse_args()
    result = enrich(Path(args.db), limit=args.limit, batch_size=args.batch_size)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
