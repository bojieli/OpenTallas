#!/usr/bin/env python3
"""DS HBM rate effect of the hierarchical SM element ot_hbm_accel_smh (rtl/hbm_accel/sm/ot_hbm_accel_smh.sv) against the
pipelined-issue element ot_hbm_accel_sm_pq, composed with the existing tools (dshbm_hbm_opt_compose / the matched
reference walk).  Every term is measured: the same 12 op sequences (tools/dshbm_sm_pq_seq.py, identical seeds and
shapes) on both elements.

  * per-op cost of a DEPENDENT op (the walk's single-op groups): the matched reference's sm_v start->done per shape
    plus the measured per-op delta smh - sm_pq in the serial-protocol runs (every op dependent: ar_l20 / wg serial,
    other; P1 and P6), worst occurrence per shape;
  * independent runs (PQ groups): replaced by the smh records' measured groups, exactly as item (1) does for sm_pq.
AR (P1) and MTP step (P6) are reported for both elements; the difference is the structural redesign's rate effect.

    python3 tools/hbm_accel_smh_compose.py --smh-rec results/rtl/hbm_sm_structure_20261005 --out R.json
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import dshbm_hbm_opt_compose as C

ROOT = C.ROOT


def ser_delta(smh_dir: Path, pq_dir: Path):
    """Per-shape (P, fmt, K, rows) worst start->done delta smh - sm_pq over the serial-protocol records."""
    pairs = [("ar_l20_f1s", 1), ("wg_f1s", 1), ("other_f1", 1), ("p6_l20_f6s", 6), ("p6_wg_f6s", 6),
             ("p6_other_f6", 6)]
    d, rows = {}, []
    for name, P in pairs:
        a = json.loads((smh_dir / f"{name}.json").read_text())
        b = json.loads((pq_dir / f"{name}.json").read_text())
        for r in (a, b):
            assert r["status"] == "pass" and r["mismatching_ops"] == 0, name
        if name.startswith(("other", "p6_other")):
            assert all(o["dep"] for o in a["ops"]), name
        for oa, ob in zip(a["ops"], b["ops"]):
            assert (oa["tag"], oa["fmt"], oa["K"], oa["rows"]) == (ob["tag"], ob["fmt"], ob["K"], ob["rows"])
            da = oa["rtl"]["t_done"] - oa["rtl"]["t_post"]
            db = ob["rtl"]["t_done"] - ob["rtl"]["t_post"]
            k = (P, oa["fmt"], oa["K"], oa["rows"])
            d[k] = max(d.get(k, -10**9), da - db)
            rows.append(dict(record=name, op=oa["op"], tag=oa["tag"], smh_post_to_done=da, pq_post_to_done=db,
                             delta=da - db))
    return d, rows


def adjusted(S, delta):
    S2 = dict(S)
    sm = copy.deepcopy(S["smseq"])
    miss = []
    dmax = max(delta.values())
    for k, v in sm.op.items():
        dk = delta.get(k)
        if dk is None:
            miss.append(k)
            dk = dmax                       # a shape no serial record holds: the worst measured delta
        v["s2d"] += dk
        v["s2last"] += dk
        v["drain"] += dk
    S2["smseq"] = sm
    return S2, miss


def compose(S, rows1, rows6, recs, ar, mm):
    rp, r6p = recs
    s1, per1 = C.item1(S, rows1, rp, 1)
    s6, per6 = C.item1(S, rows6, dict(l20=r6p["l20_6"], wg=r6p["wg_6"]), 6)
    step = mm["step_us"] - s6
    return dict(walk_AR_us=ar, AR_us=round(ar - s1, 3), pq_groups_saved_AR_us=s1, groups_AR=per1,
                walk_MTP_step_us=mm["step_us"], MTP_step_us=round(step, 3), pq_groups_saved_MTP_us=s6,
                groups_MTP=per6, MTP_tok_s=round(mm["tau"] * 1e6 / step, 1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--smh-rec", type=Path, required=True, help="dir holding the smh records (<seq>_f1.json ...)")
    ap.add_argument("--pq-rec", type=Path, default=C.REC / "pq")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    S = C.setup()
    ar0, mm0, rows1, rows6 = C.gate_rows(S)
    pq = compose(S, rows1, rows6, (C.load_recs(a.pq_rec, "f1"), C.load_recs(a.pq_rec, "f6")), ar0, mm0)
    delta, drows = ser_delta(a.smh_rec, a.pq_rec)
    S2, miss = adjusted(S, delta)
    ar2, mm2, rows1b, rows6b = C.gate_rows(S2)
    smh = compose(S2, rows1b, rows6b, (C.load_recs(a.smh_rec, "f1"), C.load_recs(a.smh_rec, "f6")), ar2, mm2)
    out = dict(schema="opentallas.hbm_accel_smh.compose.v1",
               basis=dict(gate_AR_us=ar0, gate_MTP_step_us=mm0["step_us"], tau=mm0["tau"]),
               sm_pq=pq, smh=smh,
               effect=dict(AR_us=round(smh["AR_us"] - pq["AR_us"], 3),
                           AR_pct=round(100 * (smh["AR_us"] - pq["AR_us"]) / pq["AR_us"], 3),
                           MTP_step_us=round(smh["MTP_step_us"] - pq["MTP_step_us"], 3),
                           MTP_pct=round(100 * (smh["MTP_step_us"] - pq["MTP_step_us"]) / pq["MTP_step_us"], 3),
                           MTP_tok_s=round(smh["MTP_tok_s"] - pq["MTP_tok_s"], 1)),
               per_op_serial_delta_cycles={f"P{k[0]} {k[1]} K{k[2]} R{k[3]}": v for k, v in sorted(delta.items())},
               shapes_without_serial_record=[f"P{k[0]} {k[1]} K{k[2]} R{k[3]}" for k in miss],
               serial_rows=drows,
               inputs={C.rel(p): C.sha(p) for p in sorted(list(a.smh_rec.glob("*.json")) + list(a.pq_rec.glob("*.json")))
                       if p.name != a.out.name},
               tool_sha256={C.rel(Path(__file__)): C.sha(Path(__file__))})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(sm_pq={k: pq[k] for k in ("AR_us", "MTP_step_us", "MTP_tok_s")},
                          smh={k: smh[k] for k in ("AR_us", "MTP_step_us", "MTP_tok_s")}, effect=out["effect"],
                          missing=out["shapes_without_serial_record"]), indent=1))


if __name__ == "__main__":
    main()
