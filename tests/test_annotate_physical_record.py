import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "annotate_physical_record.py"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_notes_are_appended_and_tool_content_is_hashed(tmp_path):
    record = tmp_path / "pnr.json"
    record.write_text(json.dumps({"status": "pass", "design": {"lanes": 8}}))
    assert run(str(record), "--note", "first", "--note", "second").returncode == 0
    loaded = json.loads(record.read_text())
    assert loaded["notes"] == ["first", "second"]
    assert loaded["status"] == "pass" and loaded["design"] == {"lanes": 8}
    assert run(str(record), "--verify").returncode == 0
    assert run(str(record), "--note", "third").returncode == 0
    assert json.loads(record.read_text())["notes"] == ["first", "second", "third"]


def test_verify_detects_edited_tool_content(tmp_path):
    record = tmp_path / "pnr.json"
    record.write_text(json.dumps({"status": "pass"}))
    assert run(str(record), "--note", "n").returncode == 0
    loaded = json.loads(record.read_text())
    loaded["status"] = "not_met"
    record.write_text(json.dumps(loaded))
    assert run(str(record), "--verify").returncode == 1
    assert run(str(record), "--note", "again").returncode != 0
