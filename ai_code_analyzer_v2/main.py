import argparse
import logging
from datetime import datetime
from pathlib import Path

from analyzer import AnalyzerAI
from knowledge_base import KnowledgeBase
from synthesizer import SynthesizerAI

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input_zips"
GENERATED_DIR = BASE_DIR / "generated_code"
LOG_DIR = BASE_DIR / "logs"
KB_PATH = BASE_DIR / "knowledge_base.json"

LOG_DIR.mkdir(exist_ok=True)
GENERATED_DIR.mkdir(exist_ok=True)
INPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "analyzer.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def handle_analysis(args: argparse.Namespace) -> None:
    """Orkiestruje procesem analizy."""
    zip_path = INPUT_DIR / args.zipfile
    if not zip_path.exists():
        logging.error("Plik %s nie istnieje!", zip_path)
        return

    analysis_id = f"{zip_path.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    analyzer = AnalyzerAI(zip_path, BASE_DIR, analysis_id)
    analysis_result = analyzer.analyze_repository()
    analysis_result["analysis_id"] = analysis_id
    analysis_result["source_zip"] = zip_path.name

    with KnowledgeBase(KB_PATH) as kb:
        kb.add_record(analysis_result)

    synthesizer = SynthesizerAI()
    generated_code = synthesizer.generate_code_from_analysis(analysis_result)

    output_path = GENERATED_DIR / f"generated_{analysis_id}.py"
    output_path.write_text(generated_code, encoding="utf-8")
    logging.info("Nowy kod zapisany w: %s", output_path)


def handle_query(args: argparse.Namespace) -> None:
    """Obsługuje odpytywanie Bazy Wiedzy."""
    with KnowledgeBase(KB_PATH) as kb:
        results = kb.query_by_type(args.type)

    print(f"\n--- WYNIKI Z BAZY WIEDZY DLA TYPU '{args.type}' ---")
    if not results:
        print("Brak wyników.")
    for record in results:
        manifest = (record.get("action_manifests") or [{}])[0] or {}
        print(f"- Nazwa: {manifest.get('name')} (Źródło: {record.get('source_zip')})")
    print("--- KONIEC WYNIKÓW ---")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ulepszony szkielet AI do analizy kodu.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_analyze = subparsers.add_parser("analyze", help="Analizuje nowy plik ZIP z kodem.")
    parser_analyze.add_argument("--zipfile", required=True, help="Nazwa pliku ZIP w folderze input_zips.")
    parser_analyze.set_defaults(func=handle_analysis)

    parser_query = subparsers.add_parser("query", help="Odpytuje Bazę Wiedzy.")
    parser_query.add_argument(
        "--type",
        choices=["node", "docker", "composite", "unknown"],
        required=True,
        help="Typ akcji do wyszukania.",
    )
    parser_query.set_defaults(func=handle_query)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":  # pragma: no cover - punkt wejścia CLI
    main()
