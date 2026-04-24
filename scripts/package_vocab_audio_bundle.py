import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.vocab_audio_pack import create_vocab_audio_deploy_bundle


def parse_args():
    parser = argparse.ArgumentParser(
        description="Package the generated vocab audio wav files and manifest into one zip bundle for production upload."
    )
    parser.add_argument(
        "--manifest-path",
        default=str(Path("instance") / "exports" / "vocab_audio_manifest.csv"),
        help="CSV manifest input path.",
    )
    parser.add_argument(
        "--output-zip",
        default=str(Path("instance") / "exports" / "vocab_audio_bundle.zip"),
        help="Zip bundle output path.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app()

    with app.app_context():
        stats = create_vocab_audio_deploy_bundle(
            manifest_path=args.manifest_path,
            output_zip_path=args.output_zip,
        )

    print(f"Manifest rows: {stats['manifest_entries']}")
    print(f"Audio files bundled: {stats['audio_files']}")
    print(f"Bundle created: {stats['bundle_path']}")


if __name__ == "__main__":
    main()
