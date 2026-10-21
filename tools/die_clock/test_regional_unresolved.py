import json
import subprocess
import sys
from pathlib import Path


def test_unresolved_clock_classes_refuse_an_otherwise_passing_die(tmp_path):
    check = dict(neighbour_check=dict(ff_measured=True, classes={"intra:r0": dict(judged=True, over=0, pairs=1)}))
    manifest = dict(spine=dict(balance=False, pads=0))
    (tmp_path / "check.json").write_text(json.dumps(check))
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    for cls in (None, "NO_ROOT", "BUMP", "RESET_XDOM", "NEIGHBOUR", "GAP", "STATIC"):
        pairs = dict(summary=dict(pairs={cls: 1} if cls else {}), lanes=[dict(bid="lane", drift=0, dck_tt=1, dck_ff=1)])
        (tmp_path / "pairs.json").write_text(json.dumps(pairs))
        subprocess.run([sys.executable, str(Path(__file__).with_name("regional_verdict.py")),
                        str(tmp_path / "check.json"), str(tmp_path / "pairs.json"), str(tmp_path / "manifest.json"),
                        "--out", str(tmp_path / "verdict.json")], check=True, capture_output=True)
        result = json.loads((tmp_path / "verdict.json").read_text())
        assert result["verdict"] == ("PASS" if cls in (None, "STATIC") else "FAIL"), (cls, result)
