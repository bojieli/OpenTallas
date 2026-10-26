"""LB2-HBM-CQW: the committed Qwen D4G8 operands re-compile (emit, no fleet) to the replay the fleet snap produced."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMG = ROOT / "results/rtl/hbm_qwen_layer_tput_1018/images"


def _emit(stage, ranks):
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([sys.executable, "-m", "hbm_layer_vehicle.qwen_layer_images", "emit", "--stage", stage,
                            "--ranks", ranks, "--operands", str(IMG / f"operands_{stage}.npz"), "--out", d],
                           cwd=ROOT, env={"PYTHONPATH": str(ROOT / "tools"), "PATH": "/usr/bin:/bin"},
                           capture_output=True, text=True, check=True)
        line = [x for x in r.stdout.splitlines() if x.startswith("QWEN_LAYER_IMAGES ")][-1]
        return json.loads(line.split(" ", 1)[1])["ranks_out"]


def test_emit_matches_fleet_snap():
    for stage in ("L0", "head"):
        snap = json.loads((IMG / f"snap_{stage}.json").read_text())
        assert snap["integrity"]["expected_missing"] == [], stage
        got = _emit(stage, "0,5")
        for r, v in snap["ranks_out"].items():
            assert got[r]["replay_sha256"] == v["replay_sha256"], (stage, r)
            assert got[r]["counts"] == v["counts"], (stage, r)


if __name__ == "__main__":
    test_emit_matches_fleet_snap()
    print("PASS")
