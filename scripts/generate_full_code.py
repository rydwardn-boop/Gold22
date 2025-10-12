"""Export the repository's key files as a single text blob.

This helper is meant for situations where you quickly need to copy the entire
project (e.g. to share it in a single message).  By default the script prints
content of the README, the main module and the unit tests, but you can provide
any list of files relative to the repository root.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Sequence


def _resolve_paths(root: Path, requested: Iterable[str]) -> list[tuple[str, Path]]:
    resolved: list[tuple[str, Path]] = []
    for raw_path in requested:
        path = (root / raw_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise ValueError(
                f"Ścieżka '{raw_path}' wychodzi poza katalog repozytorium."
            ) from exc
        if not path.exists():
            raise FileNotFoundError(f"Nie znaleziono pliku: {raw_path}")
        if not path.is_file():
            raise FileNotFoundError(f"Ścieżka nie wskazuje na plik: {raw_path}")
        resolved.append((raw_path, path))
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Zbiera wskazane pliki i wypisuje ich zawartość jeden po drugim, "
            "oddzielając je nagłówkami ułatwiającymi skopiowanie do jednego pliku."
        )
    )
    parser.add_argument(
        "files",
        nargs="*",
        default=[
            "README.md",
            "src/model_connector.py",
            "tests/test_model_connector.py",
        ],
        help="Lista plików do wyeksportowania (ścieżki względne od katalogu głównego).",
    )
    return parser


def generate_bundle(root: Path, paths: Sequence[tuple[str, Path]]) -> str:
    parts: list[str] = []
    for label, path in paths:
        content = path.read_text(encoding="utf-8")
        if content.endswith("\n"):
            content_to_use = content
        else:
            content_to_use = content + "\n"
        parts.append(f"===== {label} =====\n{content_to_use}")
    return "\n".join(parts)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]

    try:
        resolved = _resolve_paths(repo_root, args.files)
    except (ValueError, FileNotFoundError) as error:
        parser.error(str(error))

    bundle = generate_bundle(repo_root, resolved)
    sys.stdout.write(bundle)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
