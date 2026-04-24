import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.vocab_audio_pack import DEFAULT_OUTPUT_PREFIX, generate_vocab_audio_pack


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a local Piper audio pack for Arabic vocabulary and export a DB update manifest."
    )
    parser.add_argument(
        "--manifest-path",
        default=str(Path("instance") / "exports" / "vocab_audio_manifest.csv"),
        help="CSV manifest output path.",
    )
    parser.add_argument(
        "--output-prefix",
        default=DEFAULT_OUTPUT_PREFIX,
        help="Relative uploads prefix used for generated wav files.",
    )
    parser.add_argument("--piper-binary", default="", help="Path to the Piper executable.")
    parser.add_argument("--piper-model", default="", help="Path to the Piper model file.")
    parser.add_argument("--piper-config", default="", help="Optional path to the Piper config file.")
    parser.add_argument("--piper-speaker", default="", help="Optional Piper speaker id.")
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="Include non pedagogical vocabulary instead of limiting the run to est_pedagogique entries.",
    )
    parser.add_argument(
        "--overwrite-files",
        action="store_true",
        help="Regenerate wav files even if they already exist locally.",
    )
    parser.add_argument(
        "--overwrite-existing-audio",
        action="store_true",
        help="Replace audio_url values that are already set in the database.",
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Apply generated audio_url values to the current local database immediately.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of entries to generate.")
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app()
    app.config["PIPER_BINARY"] = args.piper_binary or app.config.get("PIPER_BINARY", "")
    app.config["PIPER_MODEL"] = args.piper_model or app.config.get("PIPER_MODEL", "")
    app.config["PIPER_CONFIG"] = args.piper_config or app.config.get("PIPER_CONFIG", "")
    app.config["PIPER_SPEAKER"] = args.piper_speaker or app.config.get("PIPER_SPEAKER", "")

    with app.app_context():
        stats = generate_vocab_audio_pack(
            manifest_path=args.manifest_path,
            output_prefix=args.output_prefix,
            pedagogical_only=not args.include_all,
            overwrite_files=args.overwrite_files,
            overwrite_existing_audio=args.overwrite_existing_audio,
            write_db=args.write_db,
            limit=args.limit,
        )

    print(f"Generated files: {stats['generated']}")
    print(f"Reused files: {stats['reused_files']}")
    print(f"Manifest rows: {stats['manifest_rows']}")
    print(f"DB rows updated locally: {stats['updated_db']}")
    print(f"Skipped existing audio: {stats['skipped_existing_audio']}")
    print(f"Manifest written to: {args.manifest_path}")


if __name__ == "__main__":
    main()
