"""GEOM-ADVISORY-RC-1122: geom_check.sh exits 0 on a rule FAIL that has a verdict line (advisory AUTO-GEOM; a false DIED was posted on rc 1),
non-zero when the check did not judge or with OT_GEOM_STRICT=1."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def setup(tmp_path, verdict, line, rc):
    tools = tmp_path / "tools"
    tools.mkdir()
    shutil.copy(HERE / "geom_check.sh", tools / "geom_check.sh")
    for f in ("geom_dump.tcl", "geom_grt.tcl"):
        (tools / f).write_text("")
    (tools / "geom_png.py").write_text("")
    (tools / "geom_rules.py").write_text(
        "import json, sys\n"
        "j = sys.argv[sys.argv.index('--json') + 1]\n"
        f"json.dump({{'verdict': {verdict!r}, 'line': {line!r}}}, open(j, 'w'))\n"
        f"print('AP_AUTO_GEOM ' + {line!r})\nsys.exit({rc})\n")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "docker").write_text("#!/bin/sh\nexit 0\n")
    (bin_ / "docker").chmod(0o755)
    odb = tmp_path / "k" / "a" / "b" / "c" / "d" / "e" / "3_place.odb"
    odb.parent.mkdir(parents=True)
    odb.write_text("x")
    out = tmp_path / "out"
    out.mkdir()
    (out / "check.json").write_text(json.dumps({"odb": str(odb), "grt": False, "rules_args": []}))
    env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}", OT_PLACED_SCAN="0")
    return tools / "geom_check.sh", out, env


@pytest.mark.parametrize("verdict,line,rc,strict,want", [
    ("FAIL", "AUTO-GEOM FAIL fill=FAIL(0.1) r2r=FAIL(3)", 1, False, 0),   # advisory rule FAIL: finished check
    ("FAIL", "AUTO-GEOM FAIL fill=FAIL(0.1)", 1, True, 1),               # OT_GEOM_STRICT=1: old exit 1
    ("PASS", "AUTO-GEOM PASS", 0, False, 0),
    ("", "", 1, False, 1),                                               # no verdict: the check did not judge
])
def test_rc(tmp_path, verdict, line, rc, strict, want):
    sh, out, env = setup(tmp_path, verdict, line, rc)
    if strict:
        env["OT_GEOM_STRICT"] = "1"
    r = subprocess.run(["bash", str(sh), str(out)], capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == want, r.stdout + r.stderr
    if verdict == "FAIL":
        assert line in r.stdout and json.loads((out / "auto_geom.json").read_text())["line"] == line
