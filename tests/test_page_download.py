"""Тесты HTTP-загрузки и резервных копий HTML-страниц."""

import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import requests

from src.collector import HEADERS, REQUEST_TIMEOUT, download_page


class PageDownloadTests(unittest.TestCase):
    def test_request_headers_use_configured_accept_and_user_agent(self) -> None:
        self.assertEqual(HEADERS["Accept"], "*/*")
        self.assertEqual(
            HEADERS["User-Agent"],
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/152.0.0.0 YaBrowser/26.10.0.0 Safari/537.36",
        )

    def test_successful_download_saves_html_backup(self) -> None:
        html = b"<html><title>Gorodets weather</title></html>"
        response = Mock()
        response.content = html
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "html_backup" / "today.html"

            result = download_page(
                session,
                "https://example.test/weather/",
                backup_path,
            )

            self.assertEqual(result, html)
            self.assertEqual(backup_path.read_bytes(), html)
            session.get.assert_called_once_with(
                "https://example.test/weather/",
                timeout=REQUEST_TIMEOUT,
            )

    def test_request_error_uses_previous_html_backup(self) -> None:
        cached_html = b"<html><title>Cached weather</title></html>"
        session = Mock()
        session.get.side_effect = requests.Timeout("connection timed out")

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "html_backup" / "today.html"
            backup_path.parent.mkdir(parents=True)
            backup_path.write_bytes(cached_html)

            stderr = StringIO()
            with redirect_stderr(stderr):
                result = download_page(
                    session,
                    "https://example.test/weather/",
                    backup_path,
                )

            self.assertEqual(result, cached_html)
            # Logging replaces direct console output; the cached data remains valid.

    def test_request_error_without_backup_raises_runtime_error(self) -> None:
        session = Mock()
        session.get.side_effect = requests.ConnectionError("offline")

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "missing.html"

            with self.assertRaisesRegex(RuntimeError, "Резервная копия"):
                download_page(
                    session,
                    "https://example.test/weather/",
                    backup_path,
                )

    def test_empty_http_response_does_not_replace_existing_backup(self) -> None:
        cached_html = b"<html>previous good response</html>"
        response = Mock()
        response.content = b""
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "today.html"
            backup_path.write_bytes(cached_html)

            result = download_page(
                session,
                "https://example.test/weather/",
                backup_path,
            )

            self.assertEqual(result, cached_html)
            self.assertEqual(backup_path.read_bytes(), cached_html)


if __name__ == "__main__":
    unittest.main()
