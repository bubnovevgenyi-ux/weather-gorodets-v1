"""Тесты условного подключения к удалённому отладчику PyCharm."""

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.debugger import configure_pydevd


class PyCharmDebuggerTests(unittest.TestCase):
    def test_debugger_is_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.debugger.load_dotenv") as load_dotenv:
                with patch("src.debugger.importlib.import_module") as import_module:
                    self.assertFalse(configure_pydevd(Path(".env")))

        load_dotenv.assert_called_once()
        import_module.assert_not_called()

    def test_debugger_uses_environment_configuration(self) -> None:
        debugger = MagicMock()
        variables = {
            "PYCHARM_DEBUG": "1",
            "PYCHARM_DEBUG_HOST": "10.0.0.12",
            "PYCHARM_DEBUG_PORT": "5679",
            "PYCHARM_DEBUG_SUSPEND": "true",
        }
        with patch.dict(os.environ, variables, clear=True):
            with patch("src.debugger.load_dotenv"):
                with patch(
                    "src.debugger.importlib.import_module",
                    return_value=debugger,
                ) as import_module:
                    self.assertTrue(configure_pydevd(Path(".env")))

        import_module.assert_called_once_with("pydevd_pycharm")
        debugger.settrace.assert_called_once_with(
            "10.0.0.12",
            port=5679,
            stdout_to_server=True,
            stderr_to_server=True,
            suspend=True,
        )

    def test_invalid_port_fails_with_clear_message(self) -> None:
        variables = {"PYCHARM_DEBUG": "1", "PYCHARM_DEBUG_PORT": "not-a-port"}
        with patch.dict(os.environ, variables, clear=True):
            with patch("src.debugger.load_dotenv"):
                with self.assertRaisesRegex(RuntimeError, "PYCHARM_DEBUG_PORT"):
                    configure_pydevd(Path(".env"))

    def test_missing_optional_dependency_fails_with_install_hint(self) -> None:
        variables = {"PYCHARM_DEBUG": "1"}
        with patch.dict(os.environ, variables, clear=True):
            with patch("src.debugger.load_dotenv"):
                with patch(
                    "src.debugger.importlib.import_module",
                    side_effect=ImportError("not installed"),
                ):
                    with self.assertRaisesRegex(RuntimeError, "requirements-debug.txt"):
                        configure_pydevd(Path(".env"))


if __name__ == "__main__":
    unittest.main()
