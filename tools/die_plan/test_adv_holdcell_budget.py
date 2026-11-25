"""pytest: ADV-HOLDCELL-BUDGET on fixtures modeled on the A5t5 kits: pc r85c02c25c (36,837 pad cells on 430,276 insts, 8.6 %), hg_v1p2
(23,821 on 452,817 = 5.3 %), pv_v12 (open port endpoints 2,335 at -119.2 after repair), hgi_v4 (clean)."""
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "precheck"))
import adv_holdcell_budget as A  # noqa: E402
import adv_harvest_hold as H  # noqa: E402


def plan():
    t = {"hard": False}
    names = ["kv3_pc__cl5a95b461__r85c02c25c", "kv3_hg_v1p2", "kv3_pv_v12", "kv3_hgi_v4", "kv3_new"]
    return {"die": {"name": "qwen_kvsys"}, "partition_types": {n: dict(t) for n in names},
            "partitions": [{"name": f"p{i}", "type": n} for i, n in enumerate(names)]}


def cache():
    def rec(pad, insts, on=0, ow=0.0):
        return {"last": {"pad_cells": pad, "insts": insts, "pad_ends": pad, "margin": 40.0, "hold_cells": pad + 3000,
                         "open_n": on, "open_wns": ow, "exact": "k"}}
    return {"hold": {"qwen_kvsys": {"kv3_pc": rec(36837, 430276), "kv3_hg_v1p2": rec(23821, 452817),
                                    "kv3_pv_v12": rec(0, 483158, 2335, -119.2), "kv3_hgi_v4": rec(6859, 369324)}}}


def test_flags_and_summary():
    out = A.findings(plan(), "p", hold_cache=cache())
    assert out[0].startswith("WARN ADV-HOLDCELL-BUDGET kv3_pc__cl5a95b461__r85c02c25c: 36,837 planned-pad cells = 8.6%")
    assert any(ln.startswith("WARN ADV-HOLDCELL-BUDGET kv3_hg_v1p2: 23,821") for ln in out)
    assert not any("kv3_hgi_v4:" in ln for ln in out)
    po = [ln for ln in out if "PORT-OPEN" in ln]
    assert len(po) == 1 and "kv3_pv_v12" in po[0] and "2,335" in po[0] and "-119.2" in po[0]
    assert out[-1].endswith("2 types over 5% pad share, 1 with open port endpoints, 4 measured, 1 no retained kit")


def test_no_cache():
    assert A.findings(plan(), "p", hold_cache={"x": 1})[0].startswith("WARN ADV-HOLDCELL-BUDGET not checked")


def test_harvest_parse(tmp_path):
    log = textwrap.dedent("""\
        OT_HOLD_PAD rr1 margin 40.0 ends 36940 padded 19636 cells 19636 (HB4xp67_ASAP7_75t_R 37 ps FF / 60 ps TT, floor 0.0) setup_blocked 104
        OT_HOLD_PAD rr2 margin 40.0 ends 17305 padded 17201 cells 17201 (HB4xp67_ASAP7_75t_R 37 ps FF / 60 ps TT, floor 0.0) setup_blocked 104
        OT_PREGRT_FF_HOLD after wns 5.04 endpoints 0 cross_tap_wns 45.0 tap_ports 74 hold_cells 40128 insts 430276 setup_wns -757.1 (before -757.1) guard 45
        """)
    d = tmp_path / "kit" / "gen" / "kv3_pc__cl5a95b461__r85c02c25c"
    d.mkdir(parents=True)
    (d / "pregrt_ff_hold.log").write_text(log)
    r = H.parse(str(d / "pregrt_ff_hold.log"))
    assert (r["pad_cells"], r["pad_ends"], r["margin"], r["hold_cells"], r["insts"], r["open_n"]) == (36837, 36940, 40.0, 40128, 430276, 0)
    assert H.type_of(str(d / "pregrt_ff_hold.log")) == "kv3_pc"
    out = tmp_path / "c.json"
    assert H.main([str(out), "qwen_kvsys", str(tmp_path)]) == 0
    c = A.load_cache(str(out))
    assert c["hold"]["qwen_kvsys"]["kv3_pc"]["last"]["pad_cells"] == 36837
