#!/usr/bin/env python3
"""TOKSIM-HBM-coll (10-19): measured start->retire cycles of every COLL.* record class of the d4g DS AR / Qwen3-8B AR
census (LH-REPRICE3, 45.03 B/edge/SM, banklat projected), from the cross-die COLL step co-sims re-run on current RTL.

PER RECORD (both designs):   cycles = c_model - P_off + M_off / n_train
  c_model  the census model cost of the record (dump of the census schedule, job info_banklat_all)
  P_off    the off-die collective part the price carries for that record: DS = the compiled record base_cost (the
           perf.coll_cycles TU endpoint + delivery + 1 / 2 switch crossings + striping tail of the train, dealt over its
           n records); Qwen = COLL.ALL_REDUCE_SUM calibration 1350 + the plan-b TP4 -> TP8 delivery delta (+8)
  M_off    the MEASURED cross-die step(s) of the train: launch -> last publication (max over the two dies) of the
           two-die co-sim tb_xdie_hbm_step (per die: hb_coll_NE ot_hfd_coll_q2_hard_v8g + gq_issue + cp_ep/epcal
           calendar + 10 lane relays/way + hfd_ep_static + ot_pdie_serdes KP4; far die = the peer injecting its
           contributions at the schedule slots; flight modelled: DS switch+cable 333 words, Qwen package 4 words),
           bit-exact vs golden.  Train -> form as composed by TOKEN-XDIE-HBM / XDIE-HBM3..5 / HBM-COLL256-RS144:
             DS gathers (x_proj train, attn_out y, ffn_out yf, router gsc, indexer iq)      AG(48)
             DS expert_intermediate s0..s6 (7-record train)                                  AG(144)
             DS o-group GROUP_REDUCE_MCAST (2 crossings)                                     RS(144) + AG(144)
             DS TOPK_MERGE 96 x 512 (index merge)                                            link E(P = 1528)
             Qwen ALL_REDUCE_SUM, TP8 hypercube (3 links, 6 dependent steps)                 RS64+RS32+RS16+AG16+AG32+AG64
  c_model - P_off = the on-die adders of the price (collq gather span, COLL VM_RT 74 + g4, relay legs, ring-A +2, +64
           TKM ...) -- kept as priced (their own measured benches: HBM-COLLQ, HBM-BANKLAT-COLL), not re-measured here.
Records without an off-die part in the price (engram gathers, the candidate TOPK_MERGE: base 0), ROW_GATHER (no
payload co-sim) and ARGMAX_MERGE (only the on-die v8x merge is benched) are left unmeasured (null).

    python3 tools/toksim_hbm_coll_compose_1019.py --logs DIR --dump DIR --census census_shapes.json --out coll.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
from collections import defaultdict
from pathlib import Path

QW_P_OFF = 1350.0 + 2 * (7 * 16 / 4 - 3 * 32 / 4)        # calibration + plan-b delivery delta (k = 2) = 1358


def step(logdir: Path, run: str, cfg: str):
    """(launch -> last publication max over dies, E max, per-die detail, verdict) of one co-sim stage log"""
    f = logdir / run / f"{cfg}.log"
    t = f.read_text(errors="replace")
    m = re.search(r"XDIE3_STEP d0 (.*?) \| d1 (.*)", t)
    dies = []
    for part in m.groups():
        dies.append({k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", part)})
    e = re.search(r"XDIE3_E d0 (\d+) d1 (\d+)", t)
    ok = re.search(r"^XDIE2 .* (PASS|FAIL)$", t, re.M)
    return dict(launch_to_last_pub=max(d["last_pub"] for d in dies), E=[int(e.group(1)), int(e.group(2))],
                dies=dies, verdict=ok.group(1) if ok else "NONE", log=f"{run}/{cfg}.log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", type=Path, required=True)
    ap.add_argument("--dump", type=Path, required=True)
    ap.add_argument("--census", type=Path, required=True)
    ap.add_argument("--meta", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    meta = json.loads(a.meta.read_text())
    cen = json.loads(a.census.read_text())
    L = a.logs
    S = dict(ag48=step(L, "out_s3e3", "ds_ag48_pass"), ag48_r256=step(L, "out_s6main", "reg_ds_ag48_pass"),
             ag144=step(L, "out_s6main", "reg_ds_ag144_pass"), rs144=step(L, "out_s6main", "ds_rs144_pass"),
             qrs64=step(L, "out_s4e3", "qw_rs64_pass"), qrs32=step(L, "out_s4e3", "qw_rs32_pass"),
             qrs16=step(L, "out_s4e3", "qw_rs16_pass"), qag16=step(L, "out_s3e3", "qw_ag16_pass"),
             qag32=step(L, "out_s3e3", "qw_ag32_pass"), qag64=step(L, "out_s3e3", "qw_ag64_pass"))
    tk = (L / "out_colle3/topk1528_ds.log").read_text(errors="replace")
    mt = re.search(r"^XDIE_HBM .*$", tk, re.M)
    mi = re.search(r"^XDIE_INST .*$", tk, re.M)
    tk_e = [float(x) for x in re.findall(r"E=([\d.]+)", mi.group(0))] if mi else []
    S["topk1528"] = dict(line=mi.group(0) if mi else None, E_link=tk_e,
                         verdict="PASS" if mt and mt.group(0).rstrip().endswith("PASS") else "FAIL", log="out_colle3/topk1528_ds.log")
    lp = lambda k: S[k]["launch_to_last_pub"]
    FORMS = {
        "AG48": (lp("ag48"), ["ag48"], "AG(48), ROWS 64 (bound default) build"),
        "AG144": (lp("ag144"), ["ag144"], "AG(144) 3 x 48 RX blocks, ROWS 256 build (newest bench-passing, not bound)"),
        "RS144+AG144": (lp("rs144") + lp("ag144"), ["rs144", "ag144"], "RS(144) + AG(144), ROWS 256 build (not bound)"),
        "TOPK1528": (max(S["topk1528"]["E_link"]) if S["topk1528"]["E_link"] else None, ["topk1528"],
                     "tb_xdie_hbm_link E_link P = 1528 (transport vehicle: ot_hgi_coll_link_e extract + relays + ep + serdes)"),
        "QAR_TP8": (sum(lp(k) for k in ("qrs64", "qrs32", "qrs16", "qag16", "qag32", "qag64")),
                    ["qrs64", "qrs32", "qrs16", "qag16", "qag32", "qag64"],
                    "hypercube RS64+RS32+RS16 (ROWS 128 AR_ITER 1 build, not bound) + AG16+AG32+AG64 (ROWS 64 bound default)"),
    }

    def form_of(r):
        t, op = r["tag"] or "", r["op"]
        if op == "GROUP_REDUCE_MCAST":
            return "RS144+AG144"
        if op == "ALL_REDUCE_SUM":
            return "QAR_TP8"
        if op == "TOPK_MERGE" and t.startswith("96"):
            return "TOPK1528"
        if op == "ALL_GATHER" and t.startswith("expert_intermediate_gather"):
            return "AG144"
        if op == "ALL_GATHER" and t.startswith(("x_projections_gather", "attn_out_gather", "ffn_out_gather",
                                                 "router_gather", "indexer.q_gather")):
            return "AG48"
        return None

    out = dict(group="coll", branch=meta["branch"], updated_utc=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
               method=__doc__.split("\n\n")[1].strip() if "\n\n" in __doc__ else __doc__, steps=S,
               forms={k: dict(cycles=v[0], steps=v[1], what=v[2]) for k, v in FORMS.items()}, designs={})
    for d, job in (("ds_ar", "AR"), ("qwen", "qwen")):
        recs = json.loads((a.dump / f"dump.info_banklat_all__{job}.json").read_text())
        # trains: records of one segment with the same form and tag family (x_proj / expert_intermediate)
        fam = lambda r: (r["seg"], form_of(r), (r["tag"] or "").split(".")[0] if form_of(r) in ("AG48", "AG144") and
                         (r["tag"] or "").startswith(("x_projections", "expert_intermediate")) else r["i"])
        n_train = defaultdict(int)
        for r in recs:
            n_train[fam(r)] += 1
        per = defaultdict(lambda: dict(n=0, model=0.0, meas=0.0, off_model=0.0, off_meas=0.0, forms=set(), unmeasured=0))
        xdie = dict(records=0, model_off=0.0, measured_off=0.0)
        for r in recs:
            sk = r["shape"]
            k = (r["op"], sk)
            e = per[k]
            e["n"] += 1
            e["model"] += r["cost"]
            f = form_of(r)
            if f is None or FORMS[f][0] is None:
                e["unmeasured"] += 1
                continue
            p_off = QW_P_OFF if d == "qwen" else float(r["base_cost"] or 0.0)
            m_off = FORMS[f][0] / n_train[fam(r)]
            e["meas"] += r["cost"] - p_off + m_off
            e["off_model"] += p_off
            e["off_meas"] += m_off
            e["forms"].add(f)
            xdie["records"] += 1
            xdie["model_off"] += p_off
            xdie["measured_off"] += m_off
        cls = {}
        ccen = cen[d]["classes"]
        for cname, c in ccen.items():
            if not cname.startswith("COLL."):
                continue
            op = cname.split(".", 1)[1]
            shapes, rat_m, rat_s = {}, 0.0, 0.0
            for sk, sv in c["shapes"].items():
                e = per.get((op, sk))
                rec = dict(cycles=None, golden="PASS", rtl_master="ot_hfd_coll_q2_hard_v8g (hb_coll_NE) + ot_hgi_coll_gq_issue + hfd_ep_static + ot_pdie_serdes",
                           rtl_source=meta["rtl_source"], bound_in_die=None, bench=None, job=None, verilator="5.050",
                           notes="", model_cost=sv["model_cost"], n=sv["n"])
                if e is None or e["unmeasured"] == e["n"]:
                    rec.update(golden="n/a", notes="no off-die co-sim for this record kind (see where_model_wrong); model kept")
                elif e["unmeasured"]:
                    rec.update(notes=f"{e['unmeasured']} of {e['n']} records unmeasured")
                else:
                    fs = sorted(e["forms"])
                    cyc = e["meas"] / e["n"]
                    rec.update(cycles=round(cyc, 1),
                               bound_in_die=all(f in ("AG48",) for f in fs),
                               bench=", ".join(meta["bench"][f] for f in fs), job=", ".join(meta["job"][f] for f in fs),
                               rtl_source=", ".join(meta["src"][f] for f in fs),
                               golden="PASS" if all(S[s]["verdict"] == "PASS" for f in fs for s in FORMS[f][1]) else "FAIL",
                               notes=(f"form {'+'.join(fs)}; per record = model {e['model'] / e['n']:.1f} - priced off-die "
                                      f"{e['off_model'] / e['n']:.1f} + measured off-die {e['off_meas'] / e['n']:.1f} "
                                      f"(train step / records in train); on-die adders kept as priced"))
                    rat_m += cyc * sv["n"]
                    rat_s += sv["model_cost"] * sv["n"]
                shapes[sk] = rec
            meas_n = sum(1 for v in shapes.values() if v["cycles"] is not None)
            grade = "unmeasured"
            if meas_n:
                fails = any(v["golden"] == "FAIL" for v in shapes.values() if v["cycles"] is not None)
                bound = all(v["bound_in_die"] for v in shapes.values() if v["cycles"] is not None)
                grade = "measured-golden-FAIL" if fails else ("measured-current-d4g" if bound else "measured-newest-bench-passing-not-bound")
            cls[cname] = dict(law="shape_table", shapes=shapes, ratio=round(rat_m / rat_s, 4) if rat_s else None,
                              grade=grade, pending=[], where_model_wrong=meta["where"].get(f"{d}.{cname}", ""))
        cls["XDIE.LINK"] = dict(law="const", cycles=0.0, grade="measured-newest-bench-passing-not-bound",
                                note=("inter-die part is INSIDE the COLL records' start->retire (already in the per-record "
                                      "cycles above): const 0 so it is not double counted; per token the off-die part is "
                                      f"measured {xdie['measured_off']:.1f} vs priced {xdie['model_off']:.1f} cycles over "
                                      f"{xdie['records']} records (sum of record cycles, not critical-path)"),
                                per_token_measured_off=round(xdie["measured_off"], 1), per_token_priced_off=round(xdie["model_off"], 1),
                                records=xdie["records"])
        out["designs"][d] = cls
    a.out.write_text(json.dumps(out, indent=1, default=sorted) + "\n")
    print(json.dumps({d: {c: (v.get("ratio"), v.get("grade")) for c, v in x.items()} for d, x in out["designs"].items()}, indent=1))


if __name__ == "__main__":
    main()
