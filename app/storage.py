import os
from pathlib import Path

from flask import current_app


EXTERNAL_URL_PREFIXES = ("http://", "https://", "data:", "blob:")


def _safe_path(root, relative_path):
    root_path = Path(root).resolve()
    candidate = (root_path / relative_path.replace("/", os.sep)).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError:
        return None
    return candidate


def normalize_asset_path(path):
    cleaned = (path or "").strip()
    if not cleaned:
        return None
    if cleaned.startswith(EXTERNAL_URL_PREFIXES):
        return cleaned

    static_url = (current_app.static_url_path or "/static").rstrip("/")
    media_url = (current_app.config.get("MEDIA_URL") or "/media").rstrip("/")
    for prefix in (f"{media_url}/", f"{static_url}/"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) + 1 :]
            break

    if cleaned.startswith("/"):
        return None
    return cleaned.lstrip("/")


def is_media_asset(path):
    cleaned = normalize_asset_path(path)
    return bool(cleaned and not cleaned.startswith(EXTERNAL_URL_PREFIXES) and cleaned.startswith("uploads/"))


def build_asset_url(path):
    cleaned = normalize_asset_path(path)
    if not cleaned:
        return None
    if cleaned.startswith(EXTERNAL_URL_PREFIXES):
        return cleaned
    if cleaned.startswith("uploads/"):
        media_url = (current_app.config.get("MEDIA_URL") or "/media").rstrip("/")
        return f"{media_url}/{cleaned}"
    return f"{current_app.static_url_path.rstrip('/')}/{cleaned}"


def resolve_asset_path(path, allow_legacy_uploads=True):
    cleaned = normalize_asset_path(path)
    if not cleaned or cleaned.startswith(EXTERNAL_URL_PREFIXES):
        return None

    if cleaned.startswith("uploads/"):
        media_candidate = _safe_path(current_app.config["MEDIA_ROOT"], cleaned)
        if media_candidate is None:
            return None
        if media_candidate.exists() or not allow_legacy_uploads:
            return str(media_candidate)

        legacy_root = current_app.config.get("LEGACY_STATIC_UPLOADS_ROOT") or os.path.join(
            current_app.static_folder,
            "uploads",
        )
        legacy_relative = cleaned[len("uploads/") :]
        legacy_candidate = _safe_path(legacy_root, legacy_relative)
        if legacy_candidate and legacy_candidate.exists():
            return str(legacy_candidate)
        return str(media_candidate)

    static_candidate = _safe_path(current_app.static_folder, cleaned)
    return str(static_candidate) if static_candidate is not None else None


def relative_asset_path(absolute_path):
    if not absolute_path:
        return None

    resolved = Path(absolute_path).resolve()
    media_root = Path(current_app.config["MEDIA_ROOT"]).resolve()
    static_root = Path(current_app.static_folder).resolve()

    try:
        return resolved.relative_to(media_root).as_posix()
    except ValueError:
        pass

    try:
        return resolved.relative_to(static_root).as_posix()
    except ValueError:
        return None


def delete_asset_file(path, expected_prefix=None):
    cleaned = normalize_asset_path(path)
    if not cleaned:
        return False
    if expected_prefix and not cleaned.startswith(expected_prefix):
        return False

    absolute_path = resolve_asset_path(cleaned)
    if absolute_path and os.path.exists(absolute_path):
        os.remove(absolute_path)
        return True
    return False
