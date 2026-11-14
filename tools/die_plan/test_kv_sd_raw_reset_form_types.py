"""KV-101/SPLIT: kv_sd_raw_reset_form.py --types re-forms only the named SD types (default both, unknown refused)."""
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "kv_sd_raw_reset_form.py"


def test_types_option_present_and_default_both():
    src = TOOL.read_text()
    assert "'--types',default='kv3_sys_SD,kv3_sys_SD_v1'" in src
    assert "for tn in TYPES:" in src


def test_unknown_type_refused(tmp_path):
    for n in ("p.json", "r.json"):
        (tmp_path / n).write_text("{}")
    r = subprocess.run([sys.executable, "-I", str(TOOL), str(tmp_path / "p.json"), "--out-plan", str(tmp_path / "o.json"),
                        "--report", str(tmp_path / "rep.json"), "--reference-plan", str(tmp_path / "r.json"),
                        "--bind-rtl", str(tmp_path), "--types", "kv3_sys_X"], capture_output=True, text=True)
    assert r.returncode != 0 and "kv3_sys_X" in r.stderr
