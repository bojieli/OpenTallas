"""CLOCK-RESET/CP1-COLH10 10-25: a coreless CP1 proof-leaf pair gets a clock tap plan from its OWN sinks (pair.py
proof_clock): density taps, bounded sinks per tap and bounded sink->tap distance, no sink-less tap, reset relays
covered, bound insertion unchanged.   python3 -m pytest -q tools/die_plan/test_pair_proof_clock.py"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pair  # noqa: E402
import schema as S  # noqa: E402
import taps as TP  # noqa: E402

RAW = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


@pytest.fixture(scope="module")
def cut():
    P = S.Plan(RAW)
    a, b = list(P.parts)[:2]
    plan, _ = pair.extract(RAW, [a, b])
    return plan, (a, b)


def test_proof_types_get_density_taps_from_own_sinks(cut):
    plan, _ = cut
    rep = plan.pop("proof_clock", None)
    assert rep, "extract must report the proof clock plan"
    assert not S.validate(plan)
    P = S.Plan(plan)
    for tn, t in plan["partition_types"].items():
        ck = t["clock"]
        assert ck["tap_mode"] == "density" and "tap_pitch_um" not in ck
        assert ck["tap_max_sinks"] == pair.PROOF_TAP_MAX_SINKS and ck["tap_radius_um"] == pair.PROOF_TAP_RADIUS_UM
        assert not [tp for tp in ck.get("taps", []) if tp.get("kind") != "core"]
        # the leaf inventory: q per in bit + out reg per out bit at least (plus reach-leaf fold stages)
        nin = sum(b["width"] for b in t["buses"] if b["dir"] == "in")
        nout = sum(b["width"] for b in t["buses"] if b["dir"] == "out")
        assert sum(r[2] for r in ck["sink_sites_um"]) >= nin + nout
        taps = TP.density_taps(P, tn)
        pts = TP.sink_sites(P, tn)
        load, far, _ = TP.assign([(n, x, y) for n, x, y, _, _ in taps], pts, ck["tap_max_sinks"],
                                 ck["tap_radius_um"], max_distance_um=ck["tap_radius_um"])
        assert min(load) > 0, "no sink-less tap"
        assert max(load) <= ck["tap_max_sinks"]
        assert max(far) <= ck["tap_radius_um"] + 1e-6
        # every generated reset relay is a sink within the tap radius (no long arm onto a band tap)
        rel = pair.reset_sink_sites(P, tn)
        for x, y, _ in rel:
            assert min(abs(x - tx) + abs(y - ty) for _, tx, ty, _, _ in taps) <= ck["tap_radius_um"] + 1e-6
        assert rep[tn]["empty"] == 0 and rep[tn]["max_sinks"] <= ck["tap_max_sinks"]


def test_bound_insertion_unchanged(cut):
    plan, _ = cut
    import gen_phys
    P0, P1 = S.Plan(RAW), S.Plan(plan)
    for tn in plan["partition_types"]:
        assert gen_phys.insertion_binding(P1, tn) == gen_phys.insertion_binding(P0, tn)


def test_grid_taps_opt_out_and_clock_only_idempotent(cut):
    plan, (a, b) = cut
    legacy, _ = pair.extract(RAW, [a, b], proof_taps=False)
    assert "proof_clock" not in legacy
    for tn, t in legacy["partition_types"].items():
        assert t.get("clock", {}).get("tap_mode") != "density"
    # --clock-only on a legacy coreless pair plan == extract's default
    pair.proof_clock(legacy)
    for tn in plan["partition_types"]:
        assert legacy["partition_types"][tn]["clock"] == plan["partition_types"][tn]["clock"]


def test_cores_pair_untouched():
    assert not pair.is_proof_type({"module": "m", "contents": [{"module": "m_proof_leaf"}],
                                   "hard_cores": [{"inst": "c"}]})
    assert pair.is_proof_type({"module": "m", "contents": [{"module": "m_proof_leaf"}]})
