import html
import math

import requests
from flask import current_app, session
from flask_login import current_user
from sqlalchemy import or_

from app import db
from app.audio import resolve_audio_url
from app.models import Vocabulaire
from app.utils import normalize_arabic_lookup


SUPPORTED_TRANSLATION_LANGUAGES = {"fr", "en", "es"}
PREFIX_LETTERS = {"و", "ف", "ب", "ك", "ل"}
SUFFIXES = ("ات", "ون", "ين", "ان", "هما", "هم", "هن", "كما", "كم", "كن", "نا", "ها", "ه", "ة", "ي", "ك")
QUALITY_KEEP_THRESHOLD = 35
QUALITY_REMOTE_ACCEPT_THRESHOLD = 45


def get_translation_language():
    langue = (session.get("langue") or session.get("lang") or "").lower()
    if langue not in SUPPORTED_TRANSLATION_LANGUAGES and getattr(current_user, "is_authenticated", False):
        langue = (getattr(current_user, "langue_preferee", None) or "").lower()
        if langue in SUPPORTED_TRANSLATION_LANGUAGES:
            session["langue"] = langue
            session["lang"] = langue
    if langue not in SUPPORTED_TRANSLATION_LANGUAGES:
        return "fr"
    return langue


def get_translation_field_name(langue):
    return {
        "fr": "traduction_fr",
        "en": "traduction_en",
        "es": "traduction_es",
    }.get(langue, "traduction_fr")


def _clean_text(value):
    cleaned = html.unescape((value or "").strip())
    return cleaned or None


def _remote_translation_enabled():
    value = current_app.config.get("ONLINE_TRANSLATION_ENABLED", True)
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)


def _http_timeout():
    timeout = current_app.config.get("TRANSLATION_HTTP_TIMEOUT", 4)
    try:
        return float(timeout)
    except (TypeError, ValueError):
        return 4.0


def _count_arabic_chars(value):
    return sum(1 for char in value if "\u0600" <= char <= "\u06ff")


def _count_latin_chars(value):
    return sum(1 for char in value if ("a" <= char.lower() <= "z"))


def translation_quality_score(source_text, translated_text, langue):
    cleaned = _clean_text(translated_text)
    if not cleaned:
        return -math.inf

    source_normalized = normalize_arabic_lookup(source_text)
    cleaned_normalized = normalize_arabic_lookup(cleaned)
    if source_normalized and source_normalized == cleaned_normalized:
        return -200

    latin_chars = _count_latin_chars(cleaned)
    arabic_chars = _count_arabic_chars(cleaned)
    lowered = cleaned.casefold()
    words = cleaned.split()
    score = 0

    if latin_chars:
        score += 35
    if arabic_chars:
        score -= min(arabic_chars * 3, 30)
    if latin_chars and arabic_chars == 0:
        score += 15

    if 1 <= len(words) <= 4:
        score += 12
    elif len(words) > 8:
        score -= 15

    if 2 <= len(cleaned) <= 40:
        score += 10
    elif len(cleaned) > 90:
        score -= 20

    if ":" in cleaned:
        score -= 10
    if ";" in cleaned:
        score -= 8
    if source_normalized and source_normalized in cleaned_normalized:
        score -= 25

    for marker in (
        "abrégée",
        "abregée",
        "abbreviated",
        "feminine of",
        "féminin",
        "feminin",
        "masculin",
        "masculine",
        "plural",
        "pluriel",
        "singulier",
        "variant",
        "short form",
        "forme",
    ):
        if marker in lowered:
            score -= 18

    if langue == "fr" and any(char in cleaned for char in "éèêàùçôî"):
        score += 4

    return score


def _best_translation_candidate(source_text, langue, candidates):
    best_translation = None
    best_score = -math.inf

    for candidate in candidates or []:
        cleaned = _clean_text(candidate)
        score = translation_quality_score(source_text, cleaned, langue)
        if score > best_score:
            best_translation = cleaned
            best_score = score

    return best_translation, best_score


def build_arabic_lookup_candidates(term):
    normalized = normalize_arabic_lookup(term)
    if not normalized:
        return []

    candidates = []
    queue = [normalized]
    seen = set()

    while queue:
        current = queue.pop(0)
        if not current or current in seen:
            continue
        seen.add(current)
        candidates.append(current)

        if len(current) > 2 and current[0] in PREFIX_LETTERS:
            queue.append(current[1:])

        if len(current) > 3 and current.startswith("ال"):
            queue.append(current[2:])

        for suffix in SUFFIXES:
            if current.endswith(suffix) and len(current) - len(suffix) >= 3:
                queue.append(current[: -len(suffix)])

    return candidates


def _find_vocabulaire_by_pattern(candidate):
    if not candidate or len(candidate) < 3:
        return None

    like_prefix = f"{candidate}%"
    like_contains = f"%{candidate}%"
    rows = (
        Vocabulaire.query.filter(
            or_(
                Vocabulaire.mot_arabe.like(like_prefix),
                Vocabulaire.mot_arabe.like(like_contains),
            )
        )
        .limit(25)
        .all()
    )
    if not rows:
        return None

    best_entry = None
    best_score = -math.inf
    for row in rows:
        row_term = normalize_arabic_lookup(row.mot_arabe)
        score = 0
        if row_term == candidate:
            score += 100
        if row_term.startswith(candidate):
            score += 25
        if candidate in row_term:
            score += 15
        score -= abs(len(row_term) - len(candidate))
        if score > best_score:
            best_entry = row
            best_score = score

    return best_entry


def find_vocabulaire_match(term):
    for candidate in build_arabic_lookup_candidates(term):
        vocabulaire = Vocabulaire.query.filter_by(mot_arabe=candidate).first()
        if vocabulaire is not None:
            return vocabulaire, candidate

    for candidate in build_arabic_lookup_candidates(term):
        vocabulaire = _find_vocabulaire_by_pattern(candidate)
        if vocabulaire is not None:
            return vocabulaire, normalize_arabic_lookup(vocabulaire.mot_arabe)

    return None, normalize_arabic_lookup(term)


def _primary_translation(vocabulaire, langue):
    if vocabulaire is None:
        return None
    return _clean_text(getattr(vocabulaire, get_translation_field_name(langue), None))


def best_available_translation(vocabulaire, langue):
    if vocabulaire is None:
        return None

    primary = _primary_translation(vocabulaire, langue)
    if primary:
        return primary

    for field_name in ("traduction_fr", "traduction_en", "traduction_es"):
        value = _clean_text(getattr(vocabulaire, field_name, None))
        if value:
            return value
    return None


def _normalize_remote_translation(source_text, translated_text):
    cleaned = _clean_text(translated_text)
    if not cleaned:
        return None
    if normalize_arabic_lookup(cleaned) == normalize_arabic_lookup(source_text):
        return None
    return cleaned


def _fetch_libretranslate(term, langue):
    endpoint = (current_app.config.get("LIBRETRANSLATE_URL") or "").strip()
    if not endpoint:
        return None
    if not endpoint.rstrip("/").endswith("/translate"):
        endpoint = f"{endpoint.rstrip('/')}/translate"

    payload = {
        "q": term,
        "source": "ar",
        "target": langue,
        "format": "text",
    }
    api_key = (current_app.config.get("LIBRETRANSLATE_API_KEY") or "").strip()
    if api_key:
        payload["api_key"] = api_key

    response = requests.post(endpoint, json=payload, timeout=_http_timeout())
    response.raise_for_status()
    data = response.json() or {}
    candidates = [data.get("translatedText")]
    alternatives = data.get("alternatives") or []
    if isinstance(alternatives, list):
        for item in alternatives:
            if isinstance(item, list):
                candidates.extend(item)
            else:
                candidates.append(item)
    return [_normalize_remote_translation(term, candidate) for candidate in candidates]


def _fetch_mymemory(term, langue):
    endpoint = (current_app.config.get("MYMEMORY_TRANSLATE_URL") or "").strip()
    if not endpoint:
        endpoint = "https://api.mymemory.translated.net/get"

    params = {
        "q": term,
        "langpair": f"ar|{langue}",
        "mt": 1,
    }
    contact_email = (current_app.config.get("MYMEMORY_CONTACT_EMAIL") or "").strip()
    if contact_email:
        params["de"] = contact_email

    response = requests.get(endpoint, params=params, timeout=_http_timeout())
    response.raise_for_status()
    data = response.json() or {}
    response_data = data.get("responseData") or {}
    candidates = [response_data.get("translatedText")]
    for match in data.get("matches") or []:
        candidates.append(match.get("translation"))
    return [_normalize_remote_translation(term, candidate) for candidate in candidates]


def fetch_online_translation(term, langue):
    if not _remote_translation_enabled():
        return None

    last_error = None
    best_translation = None
    best_score = -math.inf

    for candidate in build_arabic_lookup_candidates(term):
        for fetcher in (_fetch_libretranslate, _fetch_mymemory):
            try:
                translations = fetcher(candidate, langue)
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                continue

            translated, score = _best_translation_candidate(candidate, langue, translations)
            if score > best_score:
                best_translation = translated
                best_score = score
            if score >= QUALITY_REMOTE_ACCEPT_THRESHOLD:
                return translated

    if last_error is not None:
        current_app.logger.warning("Traduction distante indisponible pour '%s': %s", term, last_error)
    if best_score > -math.inf:
        return best_translation
    return None


def cache_translation(term, langue, translation, vocabulaire=None, source_term=None):
    normalized = normalize_arabic_lookup(term)
    cleaned_translation = _clean_text(translation)
    if not normalized or not cleaned_translation:
        return vocabulaire

    entry = vocabulaire or Vocabulaire.query.filter_by(mot_arabe=normalized).first()
    if entry is None:
        entry = Vocabulaire(mot_arabe=normalized)
        db.session.add(entry)

    field_name = get_translation_field_name(langue)
    current_value = _clean_text(getattr(entry, field_name, None))
    current_score = translation_quality_score(source_term or normalized, current_value, langue)
    new_score = translation_quality_score(source_term or normalized, cleaned_translation, langue)
    if not current_value or new_score > current_score:
        setattr(entry, field_name, cleaned_translation)
        db.session.commit()

    return entry


def _pronunciation_text(term, vocabulaire):
    normalized = normalize_arabic_lookup(term)
    if normalized:
        return normalized
    if vocabulaire is not None:
        return normalize_arabic_lookup(vocabulaire.mot_arabe)
    return None


def _popup_audio_url(term, vocabulaire):
    pronunciation_text = _pronunciation_text(term, vocabulaire)
    generated_terms = [pronunciation_text] if pronunciation_text else []
    if vocabulaire is not None and vocabulaire.mot_arabe and vocabulaire.mot_arabe != pronunciation_text:
        generated_terms.append(vocabulaire.mot_arabe)

    manual_paths = [vocabulaire.audio_url] if vocabulaire is not None else []
    return resolve_audio_url(
        manual_paths=manual_paths,
        generated_terms=generated_terms,
    )


def resolve_vocab_popup_payload(term):
    normalized = normalize_arabic_lookup(term)
    langue = get_translation_language()
    vocabulaire, _matched_term = find_vocabulaire_match(normalized)
    pronunciation_text = _pronunciation_text(normalized, vocabulaire)
    current_translation = _primary_translation(vocabulaire, langue)
    current_score = translation_quality_score(normalized, current_translation, langue)

    if normalized and current_score < QUALITY_KEEP_THRESHOLD:
        translated = fetch_online_translation(normalized, langue)
        if translated:
            vocabulaire = cache_translation(
                vocabulaire.mot_arabe if vocabulaire is not None else normalized,
                langue,
                translated,
                vocabulaire=vocabulaire,
                source_term=normalized,
            )

    return {
        "mot": normalized,
        "translitteration": vocabulaire.translitteration if vocabulaire is not None else None,
        "traduction": best_available_translation(vocabulaire, langue),
        "audio_url": _popup_audio_url(normalized, vocabulaire),
        "pronunciation_text": pronunciation_text,
        "pronunciation_lang": "ar" if pronunciation_text else None,
        "exemple": vocabulaire.exemple_phrase if vocabulaire is not None else None,
    }
