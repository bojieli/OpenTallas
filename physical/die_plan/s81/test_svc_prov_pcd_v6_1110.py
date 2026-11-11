"""svc_prov_pcd_v6_1110: v6 pin-cycle model on the committed v5 form A event (DO_NOT_COUNT)."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import svc_prov_pcd_v6_1110 as P  # noqa: E402

V5 = HERE / "events/svc_prov_1109_v5_event.json"
V6 = HERE / "events/svc_prov_1110_v6_pcd.json"


def test_box_to_box_two_stages():
    assert P.edge_delta("SML*->SMC", 6)["delta"] == 8
    assert P.edge_delta("SMC->SMR", 0)["delta"] == 2
    assert P.edge_delta("SOFT*->SML*", 2)["delta"] == 3      # soft -> box: one stage, as v5
    assert P.edge_delta("SMD*->SOFT*", 1)["delta"] == 2      # box -> soft: one stage, as v5
    assert P.edge_delta("TRX*->TILE*", 2)["delta"] == 3      # hcore faces are source flops: one stage, as v5
    assert P.edge_delta("IRG*->IRG*", 0)["delta"] == 2


def test_v6_on_v5_event(tmp_path):
    out = tmp_path / "v6.json"
    subprocess.run([sys.executable, str(HERE / "svc_prov_pcd_v6_1110.py"), str(V5), str(out)], check=True)
    v5, v6 = json.loads(V5.read_text()), json.loads(out.read_text())
    assert set(v6["pin_cycle_deltas"]) == set(v5["pin_cycle_deltas"])
    for tn, d5 in v5["pin_cycle_deltas"].items():
        d6 = v6["pin_cycle_deltas"][tn]
        for e, v in d5.items():
            box_box = e in ("SML*->SMC", "SMC->SMR", "SMR->SMD*")
            assert d6[e] == v + (1 if box_box else 0), (tn, e)
        assert ("IRG*->IRG*" in d6) == tn.startswith("svc_lo"), tn
        if tn.startswith("svc_lo"):
            assert d6["IRG*->IRG*"] == 2
    assert v6["irg_engine"]["added_edges"] == 16 and v6["irg_engine"]["el_v6"] == 140
    assert out.read_text() == V6.read_text()                 # the committed record is this tool's output
