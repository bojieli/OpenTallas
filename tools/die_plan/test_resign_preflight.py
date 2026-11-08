"""Re-sign source metadata is resolved before any expensive sign-off or LEC."""
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import resign


class ResignPreflightTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kit = self.root / "kit"
        self.kit.mkdir()
        self.argv = ["run", "--auto", "--kit", str(self.kit),
                     "--tag", "flow-20261107-dg-s81", "--repo", str(self.root / "repo"),
                     "--tools", str(self.root / "tools"), "--out", str(self.root / "out")]

    def tearDown(self):
        self.temp.cleanup()

    def test_unknown_source_refuses_before_tools_or_chain(self):
        with patch.object(resign, "tag_commit", return_value="aa" * 20), \
             patch.object(resign, "check_tools") as tools, \
             patch.object(resign, "export_clock_family") as export, \
             patch.object(resign, "run_cmds") as commands, \
             patch.object(resign.subprocess, "call") as run:
            self.assertEqual(resign.main(self.argv), 1)
        tools.assert_not_called()
        export.assert_not_called()
        commands.assert_not_called()
        run.assert_not_called()
        self.assertFalse((self.root / "out" / "PROVENANCE.json").exists())

    def test_kit_source_is_resolved_before_commands(self):
        source = "ab" * 20
        (self.kit / "AUTOPILOT.json").write_text(json.dumps({"src_commit": source}))
        seen = []
        def commands(*args, **kwargs):
            seen.append(resign.kit_build_commit(self.kit))
            return ["signoff"], ["lec"]
        with patch.object(resign, "tag_commit", return_value="aa" * 20), \
             patch.object(resign, "check_tools"), \
             patch.object(resign, "export_clock_family", return_value="clock"), \
             patch.object(resign, "run_cmds", side_effect=commands):
            self.assertEqual(resign.main(self.argv + ["--dry-run"]), 0)
        self.assertEqual(seen, [source])

    def test_explicit_submit_source_allows_metadata_free_copy(self):
        with patch.object(resign, "tag_commit", return_value="aa" * 20), \
             patch.object(resign, "check_tools"), \
             patch.object(resign, "export_clock_family", return_value="clock"), \
             patch.object(resign, "run_cmds", return_value=(["signoff"], ["lec"])) as commands:
            self.assertEqual(resign.main(self.argv + ["--build-commit", "cd" * 20, "--dry-run"]), 0)
        commands.assert_called_once()

    def test_dry_run_without_source_prints_refusal_and_exits_0(self):
        err = io.StringIO()
        with patch.object(resign, "tag_commit", return_value="aa" * 20), \
             patch.object(resign, "check_tools"), \
             patch.object(resign, "export_clock_family", return_value="clock"), \
             patch.object(resign, "run_cmds", return_value=(["signoff"], ["lec"])) as commands, \
             patch.object(resign.subprocess, "call") as run, \
             redirect_stderr(err):
            self.assertEqual(resign.main(self.argv + ["--dry-run"]), 0)
        self.assertIn("RESIGN NOT RECORDED: build_commit unknown: pass --build-commit", err.getvalue())
        commands.assert_called_once()
        run.assert_not_called()
        self.assertFalse((self.root / "out" / "PROVENANCE.json").exists())

    def test_real_run_without_source_still_refuses_same_text(self):
        err = io.StringIO()
        with patch.object(resign, "tag_commit", return_value="aa" * 20), \
             patch.object(resign, "check_tools") as tools, \
             patch.object(resign, "run_cmds") as commands, \
             patch.object(resign.subprocess, "call") as run, \
             redirect_stderr(err):
            self.assertEqual(resign.main(self.argv), 1)
        self.assertIn("RESIGN NOT RECORDED: build_commit unknown: pass --build-commit", err.getvalue())
        tools.assert_not_called()
        commands.assert_not_called()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()

