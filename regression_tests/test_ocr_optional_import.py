"""Regression tests for a pre-existing bug fixed on 2026-10-27 (synthetic data only).

`cv2` and `numpy` were imported in a single try/except block, so an
environment without `cv2` left `numpy` (`np`) unbound as well, causing
`NameError` at class/function-definition time (`np.ndarray` type annotation)
and making `import pdfredact` fail entirely, even for non-OCR usage.

Run from the PDF-Redactor repository root with:
    python -m unittest discover -s regression_tests -v

These tests intentionally use subprocesses because the import-blocking
simulation must not pollute this process's `sys.modules` cache with
fake/blocked `cv2`/`numpy` entries, which could affect other tests or
other libraries (e.g. anything importing numpy indirectly via fitz).
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDFREDACT_DIR = ROOT / 'pdfredact'

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False


def _make_synthetic_pdf(path: Path, name_token: str, id_token: str) -> None:
    """Create a small, wholly fictional PDF for use as test input."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), f"Patient Name: {name_token}")
    page.insert_text((72, 100), f"Patient ID: {id_token}")
    page.insert_text((72, 128), "This document contains no real personal data.")
    doc.set_metadata({"author": "FAKE AUTHOR", "title": "FAKE TITLE"})
    doc.save(str(path))
    doc.close()


class OcrImportRegressionTests(unittest.TestCase):
    """Covers the ocr.py NameError bug caused by a shared cv2/numpy import block."""

    def _run(self, code: str, env_overrides: dict | None = None):
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            [sys.executable, '-c', code],
            # cwd = PDF-Redactor root (parent of the pdfredact/ package dir) so
            # that `import pdfredact` resolves the package via its __init__.py,
            # exercising the same relative-import path as `pdfredact/__init__.py`.
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_1_import_pdfredact_succeeds_in_real_environment(self):
        """`import pdfredact` must succeed even though cv2 is not installed here."""
        result = self._run("import pdfredact; print('IMPORT_OK')")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('IMPORT_OK', result.stdout)
        self.assertNotIn('NameError', result.stderr)

    def test_2_simulated_missing_cv2_and_numpy_no_nameerror(self):
        """Even if numpy were also unavailable, module import must not raise NameError.

        Uses a sys.meta_path import blocker inside an isolated subprocess so the
        blocking has zero effect on this test process or any other test.
        """
        code = (
            "import sys\n"
            "class _Blocker:\n"
            "    def find_spec(self, name, path, target=None):\n"
            "        if name in ('cv2', 'numpy'):\n"
            "            raise ImportError(f'blocked for test: {name}')\n"
            "        return None\n"
            "sys.meta_path.insert(0, _Blocker())\n"
            "import pdfredact\n"
            "caps = pdfredact.get_ocr_capabilities()\n"
            "print('IMPORT_OK', caps['opencv_available'])\n"
        )
        result = self._run(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('NameError', result.stderr)
        self.assertIn('IMPORT_OK False', result.stdout)

    def test_3_ocr_dependency_missing_message_is_accurate(self):
        """_check_dependencies()/detect_text_in_scanned_pdf() report missing libs correctly."""
        sys.path.insert(0, str(PDFREDACT_DIR))
        try:
            import ocr  # noqa: PLC0415 (intentional late import after sys.path setup)
            available, missing = ocr._check_dependencies()
            self.assertFalse(available)
            self.assertIn('opencv-python', missing)
            self.assertNotIn('numpy', missing, 'numpy is installed in this environment')

            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = ocr.detect_text_in_scanned_pdf('nonexistent.pdf', terms=['x'])
            self.assertEqual(result, {})
            self.assertIn('OCR dependencies missing: opencv-python', buf.getvalue())
        finally:
            sys.path.remove(str(PDFREDACT_DIR))

    @unittest.skipUnless(FITZ_AVAILABLE, 'PyMuPDF (fitz) not available')
    def test_4_non_ocr_pdf_processing_unaffected(self):
        """Non-OCR find_boxes()/validate_pdf() still work after the ocr.py fix."""
        sys.path.insert(0, str(PDFREDACT_DIR))
        try:
            from utils import validate_pdf
            from detect import find_boxes

            with tempfile.TemporaryDirectory() as tmp:
                pdf_path = Path(tmp) / 'synthetic.pdf'
                _make_synthetic_pdf(pdf_path, 'FAKE PATIENT ICHIRO', 'FAKE-ID-0001')
                self.assertTrue(validate_pdf(str(pdf_path)))
                boxes = find_boxes(str(pdf_path), terms=['FAKE PATIENT ICHIRO'], regex_patterns=[])
                self.assertTrue(any(boxes.values()))
        finally:
            sys.path.remove(str(PDFREDACT_DIR))


if __name__ == '__main__':
    unittest.main()
