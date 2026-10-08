"""s81-fieldphase: the committed 1,792 field-phase composition reproduces from its committed regions and geometry."""
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/s81"))
import field_phases_1792 as F  # noqa: E402


def test_nodes_reproduce():
    rec = json.loads((F.OUT / "composition.json").read_text())
    wires = {fl: F.wire_table(F.OUT / "geometry", g)[0] for fl, g in (("bf", "m221bf"), ("q", "m221q"))}
    adder = sum(F.PHASE_ADDERS.values())
    for v, x in rec["variants"].items():
        assert x["failed"] == 0 and x["all_exact"]
        reg = json.load(gzip.open(F.OUT / "regions" / f"{v}.json.gz", "rt"))
        fl = json.loads((F.MAP / v / "stage_map.json").read_text())["stage_flavour"]
        half = F.node_cycles(reg, dict(enumerate(fl)), wires, True, adder)
        full = F.node_cycles(reg, dict(enumerate(fl)), wires, False, adder)
        for n, y in x["nodes"].items():
            assert y["half_rate"] == half[n]["max"] and y["full_rate"] == full[n]["max"], (v, n)
            assert y["half_rate"] >= y["full_rate"]


def test_half_rate_rule():
    # one busy BF region: go->idle 100 -> 2 x 100 + 2; a q region untouched; last phase uses go->last_w
    ph = [{"0": [4, 90, 100, 1, 1], "1": [4, 80, 95, 1, 0]}, {"0": [4, 50, 60, 1, 1]}]
    w = {0: 10, 1: 20}
    full, _ = F.phase_cycles(ph, w, False, 0)
    half, _ = F.phase_cycles(ph, w, True, 0)
    assert full == max(100 + 10, 95 + 20) + 1 + (50 + 10)
    assert half == max(202 + 10, 95 + 20) + 1 + (102 + 10)
    assert F.phase_cycles(ph, w, False, 18)[0] == full + 36
