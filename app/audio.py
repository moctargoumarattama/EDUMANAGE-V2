import hashlib
import os
import subprocess
import tempfile

from flask import current_app

from app.storage import build_asset_url, relative_asset_path, resolve_asset_path


def _iter_text_candidates(values):
    for value in values or []:
        cleaned = (value or "").strip()
        if cleaned:
            yield cleaned


def _text_is_arabic(value):
    if not value:
        return False
    return any("\u0600" <= char <= "\u06ff" for char in value)


def _build_static_url(relative_path):
    return build_asset_url(relative_path)


def _build_audio_url(path):
    cleaned = (path or "").strip()
    if not cleaned:
        return None

    if cleaned.startswith(("http://", "https://", "data:", "blob:")):
        return cleaned

    absolute_path = resolve_asset_path(cleaned)
    if absolute_path is not None:
        if not os.path.isfile(absolute_path):
            return None
        relative_path = relative_asset_path(absolute_path)
        return _build_static_url(relative_path)

    if cleaned.startswith("/"):
        return cleaned

    return _build_static_url(cleaned)


def _normalized_vocab_key(value):
    from app.utils import normalize_arabic_lookup

    return normalize_arabic_lookup(value)


def _find_vocabulaire_entry(text):
    from app.models import Vocabulaire

    normalized = _normalized_vocab_key(text)
    if not normalized:
        return None
    return Vocabulaire.query.filter_by(mot_arabe=normalized).first()


def _piper_ready():
    return bool(
        (current_app.config.get("PIPER_BINARY") or "").strip()
        and (current_app.config.get("PIPER_MODEL") or "").strip()
    )


def _piper_cache_folder():
    folder = current_app.config.get("PIPER_CACHE_FOLDER")
    if folder:
        return folder
    return os.path.join(current_app.config["AUDIO_FOLDER"], "generated")


def _piper_cache_name(text):
    model = (current_app.config.get("PIPER_MODEL") or "").strip()
    speaker = str(current_app.config.get("PIPER_SPEAKER") or "").strip()
    payload = f"{model}|{speaker}|{text}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"piper_{digest}.wav"


def _run_piper(text, output_path):
    command = [
        current_app.config["PIPER_BINARY"],
        "--model",
        current_app.config["PIPER_MODEL"],
        "--output_file",
        output_path,
    ]
    config_path = (current_app.config.get("PIPER_CONFIG") or "").strip()
    if config_path:
        command.extend(["--config", config_path])
    speaker = str(current_app.config.get("PIPER_SPEAKER") or "").strip()
    if speaker:
        command.extend(["--speaker", speaker])

    subprocess.run(
        command,
        input=text.encode("utf-8"),
        capture_output=True,
        check=True,
    )


def ensure_piper_audio(text):
    phrase = (text or "").strip()
    if not phrase or not _text_is_arabic(phrase) or not _piper_ready():
        return None

    cache_folder = _piper_cache_folder()
    os.makedirs(cache_folder, exist_ok=True)

    final_path = os.path.join(cache_folder, _piper_cache_name(phrase))
    if os.path.exists(final_path):
        return relative_asset_path(final_path)

    temp_handle = tempfile.NamedTemporaryFile(
        suffix=".wav",
        dir=cache_folder,
        delete=False,
    )
    temp_handle.close()

    try:
        _run_piper(phrase, temp_handle.name)
        if not os.path.exists(temp_handle.name) or os.path.getsize(temp_handle.name) == 0:
            return None
        os.replace(temp_handle.name, final_path)
        return relative_asset_path(final_path)
    except (OSError, subprocess.SubprocessError) as exc:
        current_app.logger.warning("Generation Piper indisponible pour '%s': %s", phrase, exc)
        return None
    finally:
        if os.path.exists(temp_handle.name):
            try:
                os.remove(temp_handle.name)
            except OSError:
                pass


def resolve_vocab_entry_audio_url(vocabulaire):
    if vocabulaire is None:
        return None
    manual_url = _build_audio_url(vocabulaire.audio_url)
    if manual_url:
        return manual_url
    generated_path = ensure_piper_audio(vocabulaire.mot_arabe)
    return _build_audio_url(generated_path)


def resolve_vocab_audio_url_for_text(text):
    vocabulaire = _find_vocabulaire_entry(text)
    if vocabulaire is None:
        return None
    return resolve_vocab_entry_audio_url(vocabulaire)


def resolve_audio_url(manual_paths=None, vocab_terms=None, generated_terms=None):
    for path in manual_paths or []:
        manual_url = _build_audio_url(path)
        if manual_url:
            return manual_url

    for term in _iter_text_candidates(vocab_terms):
        vocab_url = resolve_vocab_audio_url_for_text(term)
        if vocab_url:
            return vocab_url

    for term in _iter_text_candidates(generated_terms):
        generated_path = ensure_piper_audio(term)
        generated_url = _build_audio_url(generated_path)
        if generated_url:
            return generated_url

    return None


def resolve_choice_audio_url(choix):
    return resolve_audio_url(
        manual_paths=[choix.audio_url],
        vocab_terms=[choix.texte],
        generated_terms=[choix.texte],
    )


def resolve_question_audio_url(question, lecon=None, correct_choice=None):
    question_type = question.type_exercice or "qcm"
    correct_text = correct_choice.texte if correct_choice is not None else None

    if question_type == "ecoute":
        fallback_terms = [question.bonne_reponse_texte, correct_text]
    elif question_type in {"dictee", "speaking"}:
        fallback_terms = [question.bonne_reponse_texte, question.texte]
    else:
        fallback_terms = [question.bonne_reponse_texte, correct_text]

    return resolve_audio_url(
        manual_paths=[question.audio_url, getattr(lecon, "audio_url", None)],
        vocab_terms=fallback_terms,
        generated_terms=fallback_terms,
    )
