import json
import logging
import re
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


class AnalyzerAI:
    """Agent odpowiedzialny za analizę i ekstrakcję ustrukturyzowanej wiedzy z kodu."""

    URL_REGEX = re.compile(r"https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s'\"`]*)?")

    LANGUAGE_BY_EXT = {
        ".go": "Go",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".py": "Python",
        ".sh": "Shell",
        ".bash": "Shell",
        ".ps1": "PowerShell",
        ".yml": "YAML",
        ".yaml": "YAML",
        ".json": "JSON",
        ".md": "Markdown",
    }

    def __init__(self, zip_path: Path, base_dir: Path, analysis_id: str):
        self.zip_path = zip_path
        self.analysis_id = analysis_id
        self.temp_dir = base_dir / f"temp_{self.analysis_id}"
        logging.info(f"[{self.analysis_id}] Inicjalizacja Analityka dla: {zip_path.name}")

    def analyze_repository(self) -> Dict[str, Any]:
        """Główna metoda orkiestrująca analizę."""
        try:
            repo_root = self._extract_zip()

            analysis_result = {
                "action_manifests": [
                    self._parse_manifest(p, repo_root) for p in self._find_manifests(repo_root)
                ],
                "languages": self._detect_languages(repo_root),
                "dependencies": self._collect_dependencies(repo_root),
                "api_endpoints": self._extract_api_endpoints(repo_root),
            }
            logging.info(f"[{self.analysis_id}] Analiza zakończona sukcesem.")
            return analysis_result
        finally:
            self._cleanup()

    def _extract_zip(self) -> Path:
        logging.info("Rozpakowywanie archiwum...")
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir()

        with zipfile.ZipFile(self.zip_path, "r") as zf:
            zf.extractall(self.temp_dir)

        subs = [p for p in self.temp_dir.iterdir() if p.is_dir()]
        if len(subs) == 1 and len(list(self.temp_dir.iterdir())) == 1:
            return subs[0]
        return self.temp_dir

    def _cleanup(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logging.info(f"Katalog tymczasowy {self.temp_dir.name} został usunięty.")

    @staticmethod
    def _safe_read(path: Path) -> str:
        try:
            return path.read_text("utf-8", errors="ignore")
        except OSError:
            return ""

    def _find_manifests(self, root: Path) -> List[Path]:
        return [p for p in root.glob("**/action.y*ml") if ".github" not in p.parts]

    def _parse_manifest(self, path: Path, root: Path) -> Dict[str, Any]:
        try:
            data = yaml.safe_load(self._safe_read(path)) or {}
            runs = data.get("runs", {})
            using = runs.get("using", "unknown") if isinstance(runs, dict) else "unknown"
            if isinstance(using, str):
                using_lower = using.lower()
            else:
                using_lower = "unknown"

            if "docker" in using_lower or (isinstance(runs, dict) and runs.get("image")):
                manifest_type = "docker"
            elif "node" in using_lower:
                manifest_type = "node"
            elif using_lower == "composite":
                manifest_type = "composite"
            else:
                manifest_type = "unknown"

            return {
                "path": str(path.relative_to(root)),
                "name": data.get("name"),
                "description": data.get("description"),
                "type": manifest_type,
                "inputs": list((data.get("inputs") or {}).keys()),
            }
        except Exception as exc:  # pragma: no cover - defensywne logowanie błędów
            logging.error("[%s] Nie udało się sparsować manifestu %s: %s", self.analysis_id, path, exc)
            return {"path": str(path.relative_to(root)), "error": f"Failed to parse: {exc}"}

    def _detect_languages(self, root: Path) -> Dict[str, int]:
        counts: Counter[str] = Counter()
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.name == "Dockerfile":
                counts["Dockerfile"] += 1
                continue
            counts[self.LANGUAGE_BY_EXT.get(file_path.suffix.lower(), "Other")] += 1
        return dict(counts)

    def _collect_dependencies(self, root: Path) -> Dict[str, Any]:
        dependencies: Dict[str, Any] = {}

        package_files = list(root.rglob("package.json"))
        if package_files:
            dependencies["node"] = [self._parse_package_json(p) for p in package_files]

        go_modules = list(root.rglob("go.mod"))
        if go_modules:
            dependencies["go"] = [self._parse_go_mod(p) for p in go_modules]

        requirements_files = list(root.rglob("requirements.txt"))
        if requirements_files:
            dependencies["python"] = [self._parse_requirements_txt(p) for p in requirements_files]

        dockerfiles = list(root.rglob("Dockerfile"))
        if dockerfiles:
            dependencies["docker"] = [
                {"path": str(p.relative_to(root)), "parsed": self._parse_dockerfile(self._safe_read(p))}
                for p in dockerfiles
            ]

        return dependencies

    def _extract_api_endpoints(self, root: Path) -> List[str]:
        """NOWA FUNKCJA: Przeszukuje pliki w poszukiwaniu potencjalnych endpointów API."""
        logging.info("Rozpoczynanie ekstrakcji endpointów API...")
        endpoints = set()
        for pattern in ["*.js", "*.py", "*.ts", "*.sh"]:
            for file_path in root.rglob(pattern):
                content = self._safe_read(file_path)
                for url in self.URL_REGEX.findall(content):
                    if "schema.json" in url or "github.com" in url:
                        continue
                    endpoints.add(url)
        logging.info(f"Znaleziono {len(endpoints)} unikalnych potencjalnych endpointów.")
        return sorted(endpoints)

    @staticmethod
    def _parse_package_json(path: Path) -> Dict[str, Any]:
        try:
            data = json.loads(path.read_text("utf-8"))
        except json.JSONDecodeError:
            logging.warning("Niepoprawny JSON w pliku %s", path)
            data = {}
        return {
            "path": str(path),
            "name": data.get("name"),
            "version": data.get("version"),
            "description": data.get("description"),
            "main": data.get("main"),
            "scripts": data.get("scripts"),
            "dependencies": data.get("dependencies"),
            "devDependencies": data.get("devDependencies"),
            "engines": data.get("engines"),
            "type": data.get("type"),
        }

    @staticmethod
    def _parse_go_mod(path: Path) -> Dict[str, Any]:
        text = path.read_text("utf-8", errors="ignore")
        module: Optional[str] = None
        go_version: Optional[str] = None
        requires: List[Tuple[str, str]] = []
        in_block = False

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("module "):
                module = stripped.split()[1]
            elif stripped.startswith("go "):
                go_version = stripped.split()[1]
            elif stripped.startswith("require ("):
                in_block = True
            elif stripped == ")":
                in_block = False
            elif stripped.startswith("require "):
                parts = stripped.split()
                if len(parts) >= 3:
                    requires.append((parts[1], parts[2]))
            elif in_block and stripped and not stripped.startswith("//"):
                parts = re.split(r"\s+", stripped)
                if len(parts) >= 2:
                    requires.append((parts[0], parts[1]))

        return {"path": str(path), "module": module, "go": go_version, "requires": requires}

    @staticmethod
    def _parse_requirements_txt(path: Path) -> Dict[str, Any]:
        packages: List[str] = []
        for line in path.read_text("utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            packages.append(stripped)
        return {"path": str(path), "requirements": packages}

    @staticmethod
    def _parse_dockerfile(text: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "from": [],
            "workdir": None,
            "entrypoint": None,
            "cmd": None,
            "runs": [],
        }
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            upper = stripped.upper()
            if upper.startswith("FROM "):
                info["from"].append(stripped.split(None, 1)[1].strip())
            elif upper.startswith("WORKDIR "):
                info["workdir"] = stripped.split(None, 1)[1].strip()
            elif upper.startswith("ENTRYPOINT"):
                info["entrypoint"] = stripped.partition(" ")[2].strip()
            elif upper.startswith("CMD"):
                info["cmd"] = stripped.partition(" ")[2].strip()
            elif upper.startswith("RUN "):
                info["runs"].append(stripped[4:].strip())
        return info
