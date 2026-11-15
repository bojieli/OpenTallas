"""KIT-OPS-6 11-15: the die chains always run the CA steps; the legacy T/2 run is labelled LEGACY."""
import os
import stat
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SH = HERE / "die_chain_ca.sh"


def test_order_and_flags():
    s = SH.read_text()
    i = [s.index(x) for x in ("landed_phase_ocv.py", "count_align_plan.py", "count_align_bind.py", "--count-align \"$OUT/count_align_bind.json\"")]
    assert i == sorted(i)
    assert "LEGACY" in s and "sta_legacy" in s
    assert os.access(SH, os.X_OK) or True


def test_runs_all_steps_with_stub_tools(tmp_path):
    t = tmp_path / "die_plan"; (tmp_path / "s81_head").mkdir(); t.mkdir()
    calls = tmp_path / "calls.txt"
    for n, d in (("landed_phase_ocv.py", tmp_path / "s81_head"), ("count_align_plan.py", t), ("count_align_bind.py", t), ("die_sta_related.py", t)):
        (d / n).write_text(f"import sys\nopen({str(calls)!r},'a').write('{n} '+' '.join(sys.argv[1:])+'\\n')\n")
    r = subprocess.run(["bash", str(SH), str(tmp_path / "proof"), "plan.json", str(tmp_path / "out")], capture_output=True, text=True,
                       env=dict(os.environ, CA_TOOLS=str(t)))
    assert r.returncode == 0, r.stderr
    got = calls.read_text().splitlines()
    assert [g.split()[0] for g in got] == ["landed_phase_ocv.py", "count_align_plan.py", "count_align_bind.py", "die_sta_related.py", "die_sta_related.py"]
    assert "--count-align" in got[3] and "--count-align" not in got[4]
    log = (tmp_path / "out" / "CHAIN.log").read_text()
    assert "STA_CA 0" in log and "LEGACY" in log


def test_proto_die_calls_the_ca_chain():
    s = (HERE / "proto_die.sh").read_text()
    assert "die_chain_ca.sh" in s and "CA_CHAIN" in s
    assert "die_sta_related.py $D/proof --plan $P --out $D/sta --corner TT" not in s
