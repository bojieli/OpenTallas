#!/usr/bin/env python3
"""TOKSIM-HBM-smhbm: fold toksim_smhbm.py run JSONs into units/smhbm.json (parent TOKSIM-HBM schema).

  toksim_smhbm_units.py --census census_shapes.json --fix FIXROOT --ds R1.json[,R2..] --qwen Q1.json[,..]
                        --branch B@sha --out units/smhbm.json [--pending JSON]
Per op: cycles = OCCUPANCY on the static stream = next op's first command - this op's first command (same run; for the
last op of a run: first command -> last result).  This is the record's incremental token time (it includes the HBM-paced
block gos, the x-store load of the next op and the compiled op gap).  span (first command -> last result) is recorded too.
Ops are matched to census SHAPE_KEYs by their exact descriptors (fixture records.json desc; Qwen: QWEN table).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

QWEN = {"qkv": (4096, 1536), "o": (1024, 4096), "gu": (4096, 6144), "down": (3072, 4096), "head": (4096, 37984)}


def key_of(desc):
    d = {}
    for nm in sorted(desc):
        v = desc[nm]
        d[nm] = [v[5], v[1], v[2], v[6]]
    return json.dumps(d)


def qkey(tag):
    K, m = QWEN[tag]
    o = ["STREAM", m, 1, "FP32"] if tag == "head" else ["VM", m, 1, "FP32"]
    return json.dumps({"A": ["VM", K, 1, "FP32"], "B": ["HBM", K, m, "INT8"], "O": o})


def occupancy(ops, runs_done):
    out = []
    for i, op in enumerate(ops):
        nxt = ops[i + 1]["first_cmd_abs"] if i + 1 < len(ops) and ops[i + 1]["layer"] == op["layer"] else None
        span = op.get("span_first_cmd_to_last_result")
        out.append((nxt - op["first_cmd_abs"]) if nxt is not None else span)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True)
    ap.add_argument("--fix", required=True)
    ap.add_argument("--ds", default="")
    ap.add_argument("--qwen", default="")
    ap.add_argument("--branch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", default="", help="JSON file merged into designs (pending, notes)")
    a = ap.parse_args()
    cen = json.loads(Path(a.census).read_text())
    meta = {}
    for L in ("L00", "L02", "L14", "head"):
        for q in json.loads((Path(a.fix) / L / "records.json").read_text())["records"]["0"]:
            meta[(L, q.get("k_layer", q["k"]))] = q
    designs = {}
    for des, files in (("ds_ar", a.ds), ("qwen", a.qwen)):
        cls = cen[des]["classes"]["SM.MATVEC"]
        meas = {}
        for f in [x for x in files.split(",") if x]:
            d = json.loads(Path(f).read_text())
            occ = occupancy(d["ops"], d.get("runs_done", []))
            for op, c in zip(d["ops"], occ):
                fused = 1
                if des == "qwen":
                    k = qkey(op["tag"])
                else:
                    desc = json.loads(json.dumps(meta[(op["layer"], op["k"])]["desc"]))
                    if "w1+w3" in op["tag"]:
                        # fixture fuses w1+w3 (m 48); the census prices w1 and w3 as two m-24 records: half each
                        fused = 2
                        for nm in ("B", "O"):
                            desc[nm][2 if nm == "B" else 1] //= 2
                    if op["tag"] == "LM head":
                        desc["O"][5] = "STREAM"
                    k = key_of(desc)
                c = c / fused if c is not None else None
                meas.setdefault(k, []).append(dict(cycles=c, span=op.get("span_first_cmd_to_last_result"),
                                                   verdict=op["verdict"], run=d["name"], tag=op["tag"], layer=op["layer"],
                                                   R=op["R"], blocks=op["blocks"], lines=op["lines"], fused=fused,
                                                   run_verdict=d["verdict"], sched=d.get("static_schedule"),
                                                   src=d.get("source_revision"), file=f))
        shapes, ratios = {}, []
        msum = 0.0
        for k, s in cls["shapes"].items():
            ms = meas.get(k)
            if not ms:
                shapes[k] = dict(cycles=None, golden=None, rtl_master="ot_hbm_accel_smh_attn + ot_hbm_svc_pc_ctrl_leaf_cfg_h9b",
                                 notes="no production record of this shape in the measured fixtures")
                continue
            c = sum(m["cycles"] for m in ms) / len(ms)
            ok = all(m["verdict"] == "PASS" for m in ms) and all(m["run_verdict"] == "PASS" for m in ms)
            shapes[k] = dict(cycles=round(c, 1), golden="PASS" if ok else "FAIL",
                             rtl_master="ot_hbm_accel_smh_attn #(ENABLE_INT8 1) <- ot_hbm_svc_sm_group_rel_id <- "
                                        "ot_hbm_svc_vm_kshare_splitstrap <- 4 x ot_hbm_svc_pc_ctrl_leaf_cfg_h9b",
                             rtl_source=f"{a.branch} (RTL = claude/hd4g-gen2e3-1019 9787e078a, die synth sources)",
                             bound_in_die=True, bench="rtl/test/hbm_accel/svg_rel/tb_toksim_smhbm.sv + "
                                                      "tools/hbm_layer_vehicle/toksim_smhbm.py",
                             job="ot-epyc5:/srv/opentallas-scratch/claude/toksim-smhbm-1019/out/" +
                                 ",".join(sorted({Path(m['file']).name for m in ms})),
                             verilator="5.050", n_records_measured=len(ms),
                             span_first_cmd_to_last_result=round(sum(m["span"] or 0 for m in ms) / len(ms), 1),
                             model_cost=s["model_cost"], ratio=round(c / s["model_cost"], 4), bytes_B=s["bytes_B"],
                             B_per_edge=round(s["bytes_B"] / c, 2),
                             notes=f"rows/SM {ms[0]['R']} blocks {ms[0]['blocks']} lines {ms[0]['lines']}; "
                                   f"schedule {ms[0]['sched']}")
            ratios.append((c / s["model_cost"], s["n"] * s["model_cost"]))
            msum += s["n"] * s["model_cost"]
        ratio = sum(r * w for r, w in ratios) / sum(w for _, w in ratios) if ratios else None
        designs[des] = {"SM.MATVEC": dict(law="shape_table", shapes=shapes, ratio=round(ratio, 4) if ratio else None,
                                          ratio_weighting="model_sum-weighted over measured shapes",
                                          covered_model_sum=round(msum, 1), class_model_sum=cls["model_sum"],
                                          covered_frac=round(msum / cls["model_sum"], 4))}
    if a.extra:
        ex = json.loads(Path(a.extra).read_text())
        for des, v in ex.items():
            designs.setdefault(des, {}).setdefault("SM.MATVEC", {}).update(v)
    doc = dict(group="smhbm", branch=a.branch, updated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               designs=designs)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    for des, v in designs.items():
        c = v["SM.MATVEC"]
        print(des, "ratio", c.get("ratio"), "covered", c.get("covered_frac"), "grade", c.get("grade"))


if __name__ == "__main__":
    main()
