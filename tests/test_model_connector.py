"""Tests for the :mod:`src.model_connector` module."""

from __future__ import annotations

import pickle
import tempfile
import unittest
from pathlib import Path
from typing import Any, Iterable, List

from src.model_connector import ModelConnector


class DummyPreprocessor:
    """Toy preprocessor adding 1 to each numeric feature."""

    def transform(self, data: Iterable[Iterable[int]]) -> list[list[int]]:
        return [[value + 1 for value in row] for row in data]


class DummyModel:
    """Model returning the sum of each row."""

    def predict(self, data: Iterable[Iterable[int]]) -> list[int]:
        return [sum(row) for row in data]


class DummyArray:
    """Mimics a numpy array by exposing :py:meth:`tolist`."""

    def __init__(self, data: Iterable[int]) -> None:
        self._data = list(data)

    def tolist(self) -> List[int]:
        return list(self._data)


class DummyModelReturningArray:
    """Model returning a ``DummyArray`` instance."""

    def predict(self, data: Iterable[int]) -> DummyArray:
        return DummyArray(data)


class InvalidCallable:
    """Object without callable transform/predict methods."""

    some_attribute = "not callable"


class ModelConnectorTestCase(unittest.TestCase):
    def _dump(self, obj: Any, path: Path) -> None:
        with path.open("wb") as handle:
            pickle.dump(obj, handle)

    def test_predict_with_preprocessor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_path = tmp_path / "model.pkl"
            preprocessor_path = tmp_path / "preprocessor.pkl"

            self._dump(DummyModel(), model_path)
            self._dump(DummyPreprocessor(), preprocessor_path)

            connector = ModelConnector(model_path, preprocessor_path)
            result = connector.predict([[0, 1], [2, 3]])

        self.assertEqual(result, [3, 7])

    def test_predict_without_preprocessor_returns_plain_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_path = tmp_path / "model.pkl"

            self._dump(DummyModelReturningArray(), model_path)

            connector = ModelConnector(model_path)
            result = connector.predict([1, 2, 3])

        self.assertEqual(result, [1, 2, 3])

    def test_invalid_preprocessor_raises_type_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_path = tmp_path / "model.pkl"
            preprocessor_path = tmp_path / "preprocessor.pkl"

            self._dump(DummyModel(), model_path)
            self._dump(InvalidCallable(), preprocessor_path)

            connector = ModelConnector(model_path, preprocessor_path)
            with self.assertRaises(TypeError):
                connector.predict([[1, 2]])

    def test_invalid_model_raises_type_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_path = tmp_path / "model.pkl"

            self._dump(InvalidCallable(), model_path)

            connector = ModelConnector(model_path)
            with self.assertRaises(TypeError):
                connector.predict([[1, 2]])


if __name__ == "__main__":  # pragma: no cover - unittest entry point
    unittest.main()
