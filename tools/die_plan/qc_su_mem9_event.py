#!/usr/bin/env python3
"""QC-MEM9 11-08 plan event: bind the eight QC SU lanes to the memory-transport head (rtl/physical/qfd_dv_lane_h_su_mem9.sv).

MEMORY_READ_EXTRA = su_l->su_c request cycles + su_c->su_l answer cycles, DERIVED from this plan's latency.lanes (all SU
slices, both lane groups, both buses): the core must match the transport of the plan it is built for, and a plan event
that changes those buses (e.g. TYPE-SAFE-3 relays, answer 4 -> 7) changes the number.  Non-uniform depths are refused.
Adds memory_read_extra to the bound_group of every hard core of qfd_qc_su_lane_w_l0..7 (bound_groups.materialize ->
qc_su_lane_cut.cut -> rtl/physical/qfd_qc_su_lane_w_l*.sv).  No pin, outline, macro, lane or latency field changes.
    qc_su_mem9_event.py PLAN.json OUT.json [--expect-extra N]   -> prints {n_groups, modules, request, answer, extra, sha256}
"""
import argparse, hashlib, json, re
from pathlib import Path

MODS = {f"qfd_qc_su_lane_w_l{l}" for l in range(8)}
REQ = re.compile(r"sl_[EW]\d+_su_l[01]__x_su_l[01]_su_c(_p1)?$")
ANS = re.compile(r"sl_[EW]\d+_su_c__x_su_c_su_l[01](_p1)?$")
# qfd_dv_s1_flop_ring: S1 delay of age 14+EXTRA is limited to D <= 33 (the 133-bit S2 ring stays D16 + EXTRA reply stages)
MAX_EXTRA = 19


def transport(d):
    lanes = d["latency"]["lanes"]
    req = {k: v["cycles"] for k, v in lanes.items() if REQ.match(k)}
    ans = {k: v["cycles"] for k, v in lanes.items() if ANS.match(k)}
    if not req or not ans:
        raise SystemExit("no su_l<->su_c lanes in latency.lanes")
    if len(set(req.values())) != 1 or len(set(ans.values())) != 1:
        raise SystemExit(f"non-uniform su_l<->su_c depths: request {sorted(set(req.values()))} answer {sorted(set(ans.values()))}")
    return next(iter(req.values())), next(iter(ans.values())), len(req), len(ans)


def apply(d, extra):
    n, mods = 0, set()
    for tn, t in d["partition_types"].items():
        for h in t.get("hard_cores") or []:
            if h.get("module") in MODS:
                bg = h.get("bound_group")
                if not bg or bg.get("kind") != "exact_post_bind_group":
                    raise SystemExit(f"{tn}/{h['inst']}: expected an exact post-bind group")
                if bg.get("memory_alignment") != 3 or bg.get("kv_wr_pipe") != 1:
                    raise SystemExit(f"{tn}/{h['inst']}: unexpected head contract")
                bg["memory_read_extra"] = extra
                n += 1
                mods.add(h["module"])
    if mods != MODS:
        raise SystemExit(f"modules touched {sorted(mods)} != the eight lanes")
    return n, mods


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--expect-extra", type=int, help="refuse unless the derived extra equals this")
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"refusing to overwrite {a.out}")
    d = json.loads(a.plan.read_text())
    req, ans, n_req, n_ans = transport(d)
    extra = req + ans
    if a.expect_extra is not None and extra != a.expect_extra:
        raise SystemExit(f"derived extra {extra} (request {req} + answer {ans}) != expected {a.expect_extra}")
    if not 0 < extra <= MAX_EXTRA:
        raise SystemExit(f"extra {extra} outside the head ring range 1..{MAX_EXTRA}")
    n, mods = apply(d, extra)
    out = json.dumps(d, indent=1) + "\n"
    a.out.write_text(out)
    print(json.dumps(dict(n_groups=n, modules=sorted(mods), request=req, answer=ans, n_request_lanes=n_req, n_answer_lanes=n_ans,
                          extra=extra, sha256=hashlib.sha256(out.encode()).hexdigest())))


if __name__ == "__main__":
    main()
