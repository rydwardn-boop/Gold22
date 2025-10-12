"""Tests for :mod:`scripts.generate_full_code`."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from scripts import generate_full_code


class GenerateFullCodeTestCase(unittest.TestCase):
    def test_default_export_contains_headers(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = generate_full_code.main([])
        output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("===== README.md =====", output)
        self.assertIn("===== src/model_connector.py =====", output)
        self.assertIn("===== tests/test_model_connector.py =====", output)

    def test_custom_file_list(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            generate_full_code.main(["README.md"])
        output = buffer.getvalue()

        self.assertTrue(output.startswith("===== README.md ====="))
        self.assertNotIn("model_connector.py", output.splitlines()[0])


if __name__ == "__main__":  # pragma: no cover - unittest entry point
    unittest.main()
