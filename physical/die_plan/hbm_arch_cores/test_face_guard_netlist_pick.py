"""HBM-SM-KIDS-2 11-09: run_kit_hbm.sh gives face_guard / port_bind 1_synth.v when it exists, else 1_2_yosys.v.
The old `ls 1_synth.v 1_2_yosys.v | head -1` always took 1_2_yosys.v (ls sorts its arguments)."""
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
SRC = (HERE / "run_kit_hbm.sh").read_text()


def _pick_snippet():
    line = next(x for x in SRC.splitlines() if re.match(r"\s*N=.*1_synth\.v.*1_2_yosys\.v", x))
    return line.strip().rstrip("\\").strip().replace("\\$", "$")


def _run(tmp, files):
    base = tmp / "run/results/asap7/hbc_x/base"
    base.mkdir(parents=True)
    for f in files:
        (base / f).write_text("module x; endmodule\n")
    sh = _pick_snippet().replace("/work/", str(tmp) + "/") + ' printf "%s" "$N"'
    return subprocess.run(["bash", "-c", sh], capture_output=True, text=True, check=True).stdout


def test_prefers_1_synth(tmp_path):
    assert _run(tmp_path, ["1_2_yosys.v", "1_synth.v"]).endswith("/base/1_synth.v")


def test_falls_back_to_1_2_yosys(tmp_path):
    assert _run(tmp_path, ["1_2_yosys.v"]).endswith("/base/1_2_yosys.v")


def test_none_gives_empty(tmp_path):
    assert _run(tmp_path, []) == ""


def test_no_sorted_ls_pick():
    assert "1_2_yosys.v 2>/dev/null | head -1" not in SRC
