#!/usr/bin/env python3
"""DIE-S81-47 11-01 (COORD 09:0x class fix): the 17 S81 landing bands planned FAIL ("landing band absent" at kit gen,
11 types: svc_hi_dsdv_svc_rs__t1..t6, svc_hi_dsdv_svc_pvso_entry__t1/t2, svc_lo_dsdv_svc_rs__t7, ot_s81sl_leaf__t8/t72)
get bands from clock_landing_plan.fill_failed_bands: rects_um = 2..N disjoint rects nearest the bus pin, each legal
under the single-band rules (17.28-um margin, macro/other-band/FT-site free, every corner within 405-2.16 um of the
pin), summed area >= the padded reserve the type's other bands use; ring_place follows the type's other ring bands.
svc_lo_dsdv_svc_rs__t7 hbm_i0 gets one legal rect (the finer search grid finds it).  CHECKED before (event branch
ad39bb2f321): no single legal rect for the svc_hi bands (exhaustive search, probe_b4).

Only the FAIL bands change (asserted): every other band, key and type stays byte-identical; landing_place.tcl()
succeeds for all 11 types.  Report: per band rects, area / reserve, hop, and an UNCHECKED first-fit flop-capacity
estimate (DFFHQNx1 108 x 270 dbu, ring_place=ff spread from the summed area as landing_placement.tcl computes it).
usage (repo root): delta_bands_1101.py PLAN_IN PLAN_OUT SIDECAR REPORT.json"""
import copy
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402
import landing_place as LP  # noqa: E402
import compact_plan as CP  # noqa: E402
import clock_landing_plan as CLP  # noqa: E402

TYPES = ["svc_hi_dsdv_svc_rs__t1", "svc_hi_dsdv_svc_rs__t2", "svc_hi_dsdv_svc_rs__t3", "svc_hi_dsdv_svc_rs__t4",
         "svc_hi_dsdv_svc_rs__t5", "svc_hi_dsdv_svc_rs__t6", "svc_hi_dsdv_svc_pvso_entry__t1",
         "svc_hi_dsdv_svc_pvso_entry__t2", "svc_lo_dsdv_svc_rs__t7", "ot_s81sl_leaf__t8", "ot_s81sl_leaf__t72"]
N_FAIL = 17


def fails(raw, tn):
    lc = (raw["partition_types"][tn].get("clock") or {}).get("landing_contract") or {}
    return sorted(k for k, b in (lc.get("bands") or {}).items() if b.get("placement") == "FAIL" or not b.get("rect_um"))


def capacity(b, fill=0.90, w=1.08, h=0.27, sw=0.054):
    """first-fit ring-flop estimate: flops = 5*(width+1)+160, each reserving ceil(w/0.4*sp/site) sites."""
    rs = b.get("rects_um") or [b["rect_um"]]
    area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs)
    flops = 5 * (b["width"] + 1) + 160
    need = flops * math.ceil(w / 0.4 / sw - 1e-9) * sw * h
    sp = max(1.0, fill * area / need)
    rw = math.ceil(w / 0.4 * sp / sw - 1e-9) * sw
    cap = sum(int((r[3] - r[1]) / h + 1e-9) * (int((r[2] - r[0] - w) / rw + 1e-9) + 1)
              for r in rs if r[2] - r[0] >= w)
    return dict(flops_est=flops, spread=round(sp, 4), capacity_flops=cap, ratio=round(cap / flops, 3))


def main():
    src, dst, side, rp = sys.argv[1:5]
    text = Path(src).read_text()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    assert sum(len(fails(raw, tn)) for tn in TYPES) == N_FAIL
    assert not [tn for tn in raw["partition_types"] if tn not in TYPES and fails(raw, tn)]
    for tn in TYPES:
        try:
            LP.tcl(S.Plan(raw), tn)
            raise AssertionError(f"{tn}: expected landing band absent before")
        except ValueError as e:
            assert "landing band absent" in str(e), e
    new, rep = CLP.fill_failed_bands(raw, json.loads(Path(side).read_text()), TYPES)
    assert len(rep) == N_FAIL
    for k in new:
        if k != "partition_types":
            assert new[k] == orig[k], k
    for tn in new["partition_types"]:
        a, b = new["partition_types"][tn], orig["partition_types"][tn]
        if tn not in TYPES:
            assert a == b, tn
            continue
        fb = fails(orig, tn)
        assert {k: v for k, v in a.items() if k != "clock"} == {k: v for k, v in b.items() if k != "clock"}, tn
        assert {k: v for k, v in a["clock"].items() if k != "landing_contract"} == \
            {k: v for k, v in b["clock"].items() if k != "landing_contract"}, tn
        la, lb = a["clock"]["landing_contract"], b["clock"]["landing_contract"]
        assert {k: v for k, v in la.items() if k != "bands"} == {k: v for k, v in lb.items() if k != "bands"}, tn
        assert {k: v for k, v in la["bands"].items() if k not in fb} == \
            {k: v for k, v in lb["bands"].items() if k not in fb}, tn
        assert not fails(new, tn), tn
    P = S.Plan(new)
    for tn in TYPES:
        LP.tcl(P, tn)                                   # raises on a band still absent / an invalid rects_um
    for r in rep:
        b = new["partition_types"][r["type"]]["clock"]["landing_contract"]["bands"][r["bus"]]
        r.update(width=b["width"], ring_place=b.get("ring_place"), n_rects=len(r["rects_um"]), **capacity(b))
    for tn in TYPES:
        mm = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, mm.end())
        text = text[:mm.end()] + CP._d(new["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == new
    Path(dst).write_text(text)
    Path(rp).write_text(json.dumps(dict(bands=rep), indent=1) + "\n")
    for r in rep:
        print(r["type"], r["bus"], "W", r["width"], "rects", r["n_rects"], "area", r["area_um2"], "reserve",
              r["reserve_um2"], "hop", r["hop_um"], "grid", r["grid_um"], "cap/flops", r["capacity_flops"],
              r["flops_est"], r["ratio"])


if __name__ == "__main__":
    main()
