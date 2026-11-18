"""S81-DIE-R3 11-17 (COORD strategy 21:20 lever 2): proto_die.sh runs mk_combo_kv.py with OT_DIE_PLAN_TOOLS set to the tools
tree (an unset value crashed every route step on 'No module named die_sta') and exits non-zero when any step fails."""
import subprocess
from pathlib import Path

SH = Path(__file__).resolve().parent / "proto_die.sh"
SRC = SH.read_text()


def test_syntax():
    assert subprocess.run(["bash", "-n", str(SH)]).returncode == 0


def test_combo_env():
    assert "OT_DIE_PLAN_TOOLS=$S CORNER=$2" in SRC
    assert "local MK=$S/mk_combo_kv.py" in SRC


def test_fail_exit():
    for step in ('echo "GRT_$t" >> $D/FAILS', 'echo "TTA_$C" >> $D/FAILS', "echo CA_CHAIN >> $D/FAILS",
                 "echo STA_DROOP >> $D/FAILS", 'echo "MK_$1_$2" >> $D/FAILS'):
        assert step in SRC, step
    assert 'if [ -s $D/FAILS ]; then log "CHAIN_FAIL' in SRC and "exit 1; fi" in SRC
    assert SRC.rstrip().endswith("log CHAIN_DONE")


def test_proof_clock_tree():
    assert "cp $K/clock/tree.json $K/clock/ctree.v $D/proof/clk/" in SRC
