import csv
import hashlib
import os
from pathlib import Path
import zipfile

from flask import current_app

from app import db
from app.audio import _run_piper
from app.models import Vocabulaire
from app.storage import resolve_asset_path
from app.utils import normalize_arabic_lookup, text_is_arabic


DEFAULT_OUTPUT_PREFIX = "uploads/audios/vocab_pack"


def _normalize_output_prefix(output_prefix):
    return (output_prefix or DEFAULT_OUTPUT_PREFIX).strip().replace("\\", "/").strip("/")


def build_vocab_audio_relative_path(text, output_prefix=DEFAULT_OUTPUT_PREFIX):
    cleaned = (text or "").strip()
    normalized = normalize_arabic_lookup(cleaned) or cleaned
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    prefix = _normalize_output_prefix(output_prefix)
    return f"{prefix}/vocab_{digest}.wav"


def _resolve_output_absolute_path(relative_path):
    resolved = resolve_asset_path(relative_path, allow_legacy_uploads=False)
    if resolved:
        return resolved
    return str((Path(current_app.config["MEDIA_ROOT"]) / relative_path).resolve())


def _default_piper_runner(text, output_path):
    binary = (current_app.config.get("PIPER_BINARY") or "").strip()
    model = (current_app.config.get("PIPER_MODEL") or "").strip()
    if not binary or not model:
        raise RuntimeError("PIPER_BINARY and PIPER_MODEL must be configured before audio generation.")

    _run_piper(text, output_path)
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"Piper did not produce a usable audio file for '{text}'.")


def write_vocab_audio_manifest(rows, manifest_path):
    manifest = Path(manifest_path)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mot_arabe", "audio_url"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return manifest


def load_vocab_audio_manifest(manifest_path):
    manifest = Path(manifest_path)
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _project_root():
    return Path(current_app.root_path).resolve().parent


def _archive_name_for_path(path):
    resolved = Path(path).resolve()
    media_root = Path(current_app.config["MEDIA_ROOT"]).resolve()
    instance_root = Path(current_app.config["INSTANCE_DIR"]).resolve()
    project_root = _project_root()

    try:
        return Path("media").joinpath(resolved.relative_to(media_root)).as_posix()
    except ValueError:
        pass

    try:
        return Path("instance").joinpath(resolved.relative_to(instance_root)).as_posix()
    except ValueError:
        pass

    try:
        return resolved.relative_to(project_root).as_posix()
    except ValueError:
        return resolved.name


def generate_vocab_audio_pack(
    *,
    manifest_path,
    output_prefix=DEFAULT_OUTPUT_PREFIX,
    pedagogical_only=True,
    overwrite_files=False,
    overwrite_existing_audio=False,
    write_db=False,
    piper_runner=None,
    limit=None,
):
    runner = piper_runner or _default_piper_runner
    rows = []
    stats = {
        "generated": 0,
        "reused_files": 0,
        "updated_db": 0,
        "manifest_rows": 0,
        "skipped_existing_audio": 0,
        "skipped_non_pedagogical": 0,
        "skipped_non_arabic": 0,
    }
    normalized_output_prefix = _normalize_output_prefix(output_prefix)

    query = Vocabulaire.query.order_by(Vocabulaire.id.asc())

    for entry in query.all():
        if limit is not None and stats["manifest_rows"] >= limit:
            break

        if pedagogical_only and not entry.est_pedagogique:
            stats["skipped_non_pedagogical"] += 1
            continue

        phrase = (entry.mot_arabe or "").strip()
        if not phrase or not text_is_arabic(phrase):
            stats["skipped_non_arabic"] += 1
            continue

        existing_audio = (entry.audio_url or "").strip()
        if existing_audio and not overwrite_existing_audio:
            cleaned_existing_audio = existing_audio.replace("\\", "/").strip("/")
            if cleaned_existing_audio.startswith(f"{normalized_output_prefix}/"):
                existing_absolute_path = _resolve_output_absolute_path(cleaned_existing_audio)
                if os.path.exists(existing_absolute_path):
                    rows.append({"mot_arabe": phrase, "audio_url": cleaned_existing_audio})
                    stats["manifest_rows"] += 1
                    stats["reused_files"] += 1
                    continue
            stats["skipped_existing_audio"] += 1
            continue

        relative_path = build_vocab_audio_relative_path(phrase, output_prefix=output_prefix)
        absolute_path = _resolve_output_absolute_path(relative_path)
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        if overwrite_files or not os.path.exists(absolute_path):
            runner(phrase, absolute_path)
            stats["generated"] += 1
        else:
            stats["reused_files"] += 1

        rows.append({"mot_arabe": phrase, "audio_url": relative_path})
        stats["manifest_rows"] += 1

        if write_db and entry.audio_url != relative_path:
            entry.audio_url = relative_path
            stats["updated_db"] += 1

    if write_db:
        db.session.commit()

    write_vocab_audio_manifest(rows, manifest_path)
    return stats


def apply_vocab_audio_manifest(manifest_path, *, overwrite_existing_audio=False):
    stats = {
        "updated": 0,
        "skipped_existing_audio": 0,
        "missing_entries": 0,
        "invalid_rows": 0,
    }

    for row in load_vocab_audio_manifest(manifest_path):
        mot_arabe = (row.get("mot_arabe") or "").strip()
        audio_url = (row.get("audio_url") or "").strip()
        if not mot_arabe or not audio_url:
            stats["invalid_rows"] += 1
            continue

        entry = Vocabulaire.query.filter_by(mot_arabe=mot_arabe).first()
        if entry is None:
            normalized = normalize_arabic_lookup(mot_arabe)
            entry = Vocabulaire.query.filter_by(mot_arabe=normalized).first() if normalized else None
        if entry is None:
            stats["missing_entries"] += 1
            continue

        existing_audio = (entry.audio_url or "").strip()
        if existing_audio and not overwrite_existing_audio:
            stats["skipped_existing_audio"] += 1
            continue

        if entry.audio_url != audio_url:
            entry.audio_url = audio_url
            stats["updated"] += 1

    db.session.commit()
    return stats


def create_vocab_audio_deploy_bundle(
    *,
    manifest_path,
    output_zip_path,
    output_prefix=DEFAULT_OUTPUT_PREFIX,
):
    manifest = Path(manifest_path).resolve()
    if not manifest.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest}")

    audio_root = Path(_resolve_output_absolute_path(output_prefix)).resolve()
    if not audio_root.exists():
        raise FileNotFoundError(f"Audio folder not found: {audio_root}")

    bundle_path = Path(output_zip_path)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)

    audio_files = sorted(path for path in audio_root.rglob("*.wav") if path.is_file())
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(manifest, arcname=_archive_name_for_path(manifest))
        for audio_file in audio_files:
            archive.write(audio_file, arcname=_archive_name_for_path(audio_file))

    manifest_entries = sum(1 for _ in load_vocab_audio_manifest(manifest))
    return {
        "bundle_path": str(bundle_path),
        "manifest_entries": manifest_entries,
        "audio_files": len(audio_files),
    }
