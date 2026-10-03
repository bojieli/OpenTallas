"""Launcher refusal tests; these do not qualify an RTL token execution."""
import argparse
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.gpu_sys import run_canonical_qwen as launcher


class LauncherTest(unittest.TestCase):
    def args(self, directory, enabled=True):
        return argparse.Namespace(enable_canonical_qwen=enabled, backend="actual_sim:build",
                                  token=1, position=0, expected_token=2, out=Path(directory) / "token.json")

    def test_disabled_does_not_import_or_construct_backend(self):
        with tempfile.TemporaryDirectory() as td, patch.object(launcher.importlib, "import_module") as load:
            with self.assertRaisesRegex(ValueError, "default off"):
                launcher.run(self.args(td, False))
            load.assert_not_called()

    def test_missing_real_backend_components_refused(self):
        with tempfile.TemporaryDirectory() as td, patch.object(launcher.importlib, "import_module") as load:
            load.return_value.build.return_value = {"machine": object()}
            with self.assertRaisesRegex(ValueError, "backend must supply"):
                launcher.run(self.args(td))
            self.assertFalse((Path(td) / "token.json").exists())

    def test_execution_failure_never_publishes_completion(self):
        with tempfile.TemporaryDirectory() as td, patch.object(launcher.importlib, "import_module") as load, \
                patch.object(launcher, "ReleasedProviderDelivery") as delivery:
            load.return_value.build.return_value = dict.fromkeys(
                ("native_module", "byte_module", "machine", "transport"), object())
            delivery.return_value.attach.return_value.run_full_token.side_effect = RuntimeError("RTL fault")
            with self.assertRaisesRegex(RuntimeError, "RTL fault"):
                launcher.run(self.args(td))
            self.assertFalse((Path(td) / "token.json").exists())

    def test_wrong_next_token_never_publishes_completion(self):
        with tempfile.TemporaryDirectory() as td, patch.object(launcher.importlib, "import_module") as load, \
                patch.object(launcher, "ReleasedProviderDelivery") as delivery:
            load.return_value.build.return_value = dict.fromkeys(
                ("native_module", "byte_module", "machine", "transport"), object())
            delivery.return_value.attach.return_value.run_full_token.return_value = {"next_token": 3}
            with self.assertRaisesRegex(ValueError, "differs from"):
                launcher.run(self.args(td))
            self.assertFalse(hasattr(load.return_value.build.call_args.args[0], "expected_token"))
            self.assertFalse((Path(td) / "token.json").exists())


if __name__ == "__main__":
    unittest.main()
