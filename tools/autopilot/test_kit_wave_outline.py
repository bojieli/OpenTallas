"""GEOM-91: kit outline for AUTO-GEOM comes from budget.json, else freeze.json (core kits)."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave  # noqa: E402


def _outline(tmp_path, files):
    for name, body in files.items():
        (tmp_path / name).write_text(json.dumps(body))
    r = subprocess.run(["bash", "-c", kit_wave.outline_cmd(str(tmp_path))], capture_output=True, text=True)
    return r.stdout.strip()


def test_budget_outline_first(tmp_path):
    assert _outline(tmp_path, {"budget.json": {"outline_um": [10.5, 20]},
                               "freeze.json": {"outline_um": [1, 2]}}) == "10.5x20"


def test_freeze_fallback_for_core_kits(tmp_path):
    assert _outline(tmp_path, {"budget.json": {}, "freeze.json": {"outline_um": [170.64, 164.16]}}) == "170.64x164.16"


def test_no_outline_prints_nothing(tmp_path):
    assert _outline(tmp_path, {"budget.json": {}}) == ""
