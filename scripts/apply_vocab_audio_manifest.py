import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.vocab_audio_pack import apply_vocab_audio_manifest


def parse_args():
    parser = argparse.ArgumentParser(
        description="Apply a mot_arabe -> audio_url CSV manifest to the current vocabulaire table."
    )
    parser.add_argument(
        "--manifest-path",
        default=str(Path("instance") / "exports" / "vocab_audio_manifest.csv"),
        help="CSV manifest input path.",
    )
    parser.add_argument(
        "--overwrite-existing-audio",
        action="store_true",
        help="Replace audio_url values that are already set in the database.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app()

    with app.app_context():
        stats = apply_vocab_audio_manifest(
            args.manifest_path,
            overwrite_existing_audio=args.overwrite_existing_audio,
        )

    print(f"Updated rows: {stats['updated']}")
    print(f"Skipped existing audio: {stats['skipped_existing_audio']}")
    print(f"Missing entries: {stats['missing_entries']}")
    print(f"Invalid rows: {stats['invalid_rows']}")


if __name__ == "__main__":
    main()
