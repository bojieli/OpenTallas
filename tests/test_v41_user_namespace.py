"""The package controller must retain user IDs past the old 8-bit boundary."""

import hashlib
import json
from pathlib import Path

from tools.rtl_v41_user_namespace import ROOT, SOURCES, run


def test_866_user_controller_namespace(tmp_path: Path) -> None:
    output = tmp_path / "verdict.json"
    result = run(output)
    assert result == json.loads(output.read_text())
    assert set(result["tests"]) == {"16", "21"}
    assert all(case["pass"] for case in result["tests"].values())
    for path in SOURCES:
        assert result["source_sha256"][str(path)] == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
