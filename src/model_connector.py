"""Utility to load and run inference with pickled machine-learning models.

This module provides a small helper class ``ModelConnector`` that simplifies
loading a previously trained model stored in a pickle file and optionally a
matching pre-processing pipeline.  The class is intentionally lightweight so
that it can work with a broad range of Python based machine-learning stacks
without requiring additional dependencies.

Example
-------
The typical workflow expected by the tool is:

1. Persist your pre-processing pipeline and trained model as pickle files.
2. Load the objects with :class:`ModelConnector`.
3. Run predictions by passing raw input data.

The module can also be used as a command line tool.  A minimal example is::

    python -m src.model_connector \
        --model-path my_model.pkl \
        --input-data payload.json \
        --output predictions.json

The command reads input from ``payload.json`` (expected to be JSON encoded),
uses the loaded model to generate predictions and finally writes the output to
``predictions.json``.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path
from typing import Any, Optional, Sequence, Union

PathLike = Union[str, Path]


class ModelConnector:
    """Simple loader/executor for pickled machine-learning models.

    Parameters
    ----------
    model_path:
        Path to the pickle file that contains the trained model.  The object
        must either expose a callable ``predict`` method or be callable
        itself.
    preprocessor_path:
        Optional path to a pickle file that contains a pre-processing object.
        The object must provide either a callable ``transform`` method or be
        directly callable.
    """

    def __init__(
        self, model_path: PathLike, preprocessor_path: Optional[PathLike] = None
    ) -> None:
        self._model_path = Path(model_path)
        self._preprocessor_path = Path(preprocessor_path) if preprocessor_path else None

        self._model = self._load_pickle(self._model_path)
        self._preprocessor = (
            self._load_pickle(self._preprocessor_path)
            if self._preprocessor_path is not None
            else None
        )

    @staticmethod
    def _load_pickle(path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(f"Nie znaleziono pliku: {path!s}")
        with path.open("rb") as handle:
            return pickle.load(handle)

    def predict(self, raw_data: Any) -> Any:
        """Run inference using the stored model.

        Parameters
        ----------
        raw_data:
            Data in the same format that the original model expected during
            training.  When a preprocessor was supplied the raw input will
            first be passed through it.

        Returns
        -------
        Any
            The prediction result.  If the underlying model returns an object
            providing ``tolist`` it will be converted to a Python list to
            ensure JSON serialisability.
        """

        features = self._apply_preprocessor(raw_data)
        result = self._apply_model(features)
        return self._ensure_serialisable(result)

    def _apply_preprocessor(self, raw_data: Any) -> Any:
        if self._preprocessor is None:
            return raw_data
        return self._call_component(self._preprocessor, raw_data, "transform")

    def _apply_model(self, features: Any) -> Any:
        return self._call_component(self._model, features, "predict")

    @staticmethod
    def _call_component(component: Any, payload: Any, method_name: str) -> Any:
        if hasattr(component, method_name):
            method = getattr(component, method_name)
            if callable(method):
                return method(payload)
            raise TypeError(
                f"Obiekt {component!r} ma atrybut '{method_name}', który nie jest wywoływalny."
            )
        if callable(component):
            return component(payload)
        raise TypeError(
            "Obiekt musi udostępniać metodę "
            f"'{method_name}' lub być wywoływalny (callable)."
        )

    @staticmethod
    def _ensure_serialisable(result: Any) -> Any:
        if hasattr(result, "tolist"):
            try:
                return result.tolist()
            except TypeError:
                pass
        if isinstance(result, (set, tuple)):
            return list(result)
        return result


def _read_json(path: PathLike) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(data: Any, path: Optional[PathLike]) -> None:
    dump = json.dumps(data, ensure_ascii=False, indent=2)
    if path is None:
        sys.stdout.write(dump)
        sys.stdout.write("\n")
        sys.stdout.flush()
    else:
        Path(path).write_text(dump + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ładuje wskazany model (oraz opcjonalnie preprocessing) z plików "
            "pickle i wykonuje predykcję dla danych zapisanych w formacie JSON."
        )
    )
    parser.add_argument(
        "--model-path",
        required=True,
        help="Ścieżka do pliku z zapisanym modelem (pickle).",
    )
    parser.add_argument(
        "--preprocessor-path",
        help="Opcjonalna ścieżka do pliku pickle z pipeline'em przetwarzającym dane.",
    )
    parser.add_argument(
        "--input-data",
        required=True,
        help="Plik JSON zawierający dane wejściowe przekazywane do modelu.",
    )
    parser.add_argument(
        "--output",
        help=(
            "Opcjonalna ścieżka do pliku, w którym zostanie zapisany wynik. "
            "Domyślnie wynik jest wypisywany na standardowe wyjście."
        ),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    connector = ModelConnector(
        model_path=args.model_path, preprocessor_path=args.preprocessor_path
    )
    payload = _read_json(args.input_data)
    predictions = connector.predict(payload)
    _write_json(predictions, args.output)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
