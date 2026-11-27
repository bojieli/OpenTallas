"""P-ECO-WAITER-RACE: the ECO-HANDOFF waiter must wait for the routed 6_final.spef (written after 5_2_route.odb) before prd_mk.sh."""
import subprocess
from pathlib import Path

W = Path(__file__).with_name("eco_handoff_waiter.sh")


def test_syntax():
    assert subprocess.run(["bash", "-n", str(W)]).returncode == 0


def test_waits_for_spef_between_route_wait_and_prd_mk():
    s = W.read_text()
    i_route = s.index("until [ -s $RS/5_2_route.odb ]")
    i_spef = s.index("until [ -s $RS/6_final.spef ]")
    i_mk = s.index("prd_mk.sh $KIT")
    assert i_route < i_spef < i_mk
    assert "stat -c %Y $RS/6_final.spef" in s
