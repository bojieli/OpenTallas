"""PATH-KV-WIKIT 10-25: unit tests for the channel-aware per-bit FT station sites (ft_bit_sites_chan.py) and the
kv3_hub_Wi host-core re-place (geom_hubwi_chan.py), on the committed die_plan.json.

- the plan's kv3_hub_Wi bit sites keep every per-bit register hop <= 405 um (PROTO convention) and no station in a core
- the max-hop / last-hop-slack case: the worst bit has only ~0.003 um of reach slack; moving its last station 1 um
  away from the out pin must FAIL the audit
- mutant: a host core moved into the E FT channel must FAIL (audit: stations inside it; geom check: x > XMAX)
- the generator itself (reduced type: two tight slots) re-derives sites within reach and outside cores
"""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ft_bit_sites_chan as C  # noqa: E402
import geom_hubwi_chan as G  # noqa: E402

PLAN = HERE.parent / "die_plan.json"
TN = "kv3_hub_Wi"


@pytest.fixture(scope="module")
def plan():
    raw = json.loads(PLAN.read_text())
    P = C.S.Plan(C.S.load(str(PLAN)), PLAN.resolve())
    return raw, P


def test_plan_sites_within_reach_and_outside_cores(plan):
    raw, P = plan
    a = C.audit(raw, P, TN)
    assert a["bits"] > 3000
    assert a["over"] == [] and a["max_bit_hop_um"] <= 405.0
    assert a["in_core"] == []
    G.check(raw["partition_types"][TN])


def test_last_hop_slack_mutant_fails(plan):
    raw, P = plan
    a = C.audit(raw, P, TN)
    w = a["worst"]
    assert 405.0 - w["hop_um"] < 0.01          # the tight case the test is about
    m = copy.deepcopy(raw)
    s = next(s for s in m["partition_types"][TN]["ft_slots"] if s["name"] == w["slot"])
    j = w["hops"].index(max(w["hops"]))        # hop j: pts[j] -> pts[j+1]; pts[0] in pin, pts[1..k-1] stations
    k = s["stations"]
    pins = {}
    for bus, bit, ln, x, y, f in C.gen_phys.type_pins(P, TN):
        pins.setdefault(bus, {})[bit] = (x, y)
    pts = C.chain_points(pins, s, w["bit"], s["bit_sites_um"])
    if j + 1 <= k - 1:      # move the far station (site j) 1 um away from pts[j]
        site, other = j, pts[j]
    else:                   # last hop: move the last station (site j-1) 1 um away from the out pin
        site, other = j - 1, pts[j + 1]
    xy = s["bit_sites_um"][site][w["bit"]]
    xy[0] += -1.0 if other[0] > xy[0] + C.F.CELL[0] / 2 else 1.0
    b = C.audit(m, P, TN)
    assert b["over"], "1 um of extra hop on the worst bit must exceed 405 um"


def test_core_moved_into_channel_fails(plan):
    raw, P = plan
    m = copy.deepcopy(raw)
    t = m["partition_types"][TN]
    # stations of the E channel: put host_qm on top of the densest one
    xs = [st[b] for s in t["ft_slots"] for st in s.get("bit_sites_um") or [] for b in range(len(st))
          if st[b][0] > G.XMAX + 6]
    assert xs, "the E channel x > XMAX holds stations"
    x, y = xs[len(xs) // 2]
    core = next(c for c in t["hard_cores"] if c["inst"] == "host__qkd_hr_host_qm")
    core["origin_um"] = [round(x - 10.0, 2), round(y - 10.0, 2)]
    a = C.audit(m, P, TN)
    assert any(r[3] == "host__qkd_hr_host_qm" for r in a["in_core"])
    with pytest.raises(ValueError, match="inside the E FT channel"):
        G.check(t)


def test_generator_reduced_type(plan):
    """the generator's own reach figure agrees with the independent audit (same PROTO convention), so main() can
    fail closed on it; sites stay outside cores and the stage shapes match the slot"""
    raw, P = plan
    m = copy.deepcopy(raw)
    t = m["partition_types"][TN]
    keep = {"ft15"}                            # 1 b / 7 st, 5.9 um slack
    t["ft_slots"] = [s for s in t["ft_slots"] if s["name"] in keep]
    for s in t["ft_slots"]:
        s.pop("bit_sites_um", None)
    rep = C.run(m, P, TN)
    a = C.audit(m, P, TN)
    assert set(rep["slots"]) == keep
    assert abs(rep["max_bit_hop_um"] - a["max_bit_hop_um"]) <= 0.06   # rep rounds to 0.1
    assert a["in_core"] == []
    assert bool(a["over"]) == (a["max_bit_hop_um"] > 405.0)
    for s in t["ft_slots"]:
        assert len(s["bit_sites_um"]) == s["stations"] - 1
        assert all(len(st) == s["width"] + 1 for st in s["bit_sites_um"])
