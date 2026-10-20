#!/usr/bin/env python3
"""TOKSIM-HBM (10-19): compose the MEASURED HBM d4g single-user token from per-unit RTL measurements.

  merge   units/*.json -> measured.json   (the --measured input of hgi_sim.toksim_hbm_census_1019)
  report  census_jobs (model, from the census run) + measured_jobs (the same static schedule with measured record
          cycles) -> cycles.json + the tables of README.md

Token cycles (measured) = the S2 static schedule of the compiled d4g programme with every record of a measured shape
at its measured start->retire cycles (count x measured, overlapped exactly as the static schedule issues them) + the
measured inter-die cycles (XDIE.LINK, if reported outside the COLL records) + the post-hoc model terms that no record
carries (sm_svc partial-block granularity, pg_reset, land factor -- reported as UNMEASURED).
% measured = record cycles at exact measured shapes / all record cycles of the measured schedule (serial work share).

    python3 tools/hgi_sim/toksim_hbm_compose_1019.py merge  --units DIR --out measured.json
    python3 tools/hgi_sim/toksim_hbm_compose_1019.py report --model DIR --measured-jobs DIR --units DIR --out cycles.json
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

CLK_PS = 1e12 / 1.2e9                     # 833.3 ps edge (the price model CLK = 1.2 GHz)
DESIGNS = {"ds_ar": "info_banklat_all__AR", "qwen": "info_banklat_all__qwen"}
PRICE = {"ds_ar": dict(tok_s=1233.4, banklat_tok_s=1206.3, record=1905.4),       # LH-REPRICE3 compose / banklat / old
         "qwen": dict(tok_s=403.2, banklat_tok_s=407.0, record=946.2)}
# post-hoc model terms outside the record schedule (d4g_reprice3/_1019 post_hoc): cycles a token, UNMEASURED
POST_HOC = {"ds_ar": dict(sm_svc=43 * 388 + 4, pg_reset=4, land_pct=-1.13), "qwen": dict(pg_reset=4, land_pct=-0.07)}


def merge(units: Path, out: Path):
    doc = dict(designs={}, sources={})
    for f in sorted(units.glob("*.json")):
        u = json.loads(f.read_text())
        doc["sources"][f.stem] = dict(branch=u.get("branch"), updated_utc=u.get("updated_utc"))
        for d, classes in (u.get("designs") or {}).items():
            for c, law in classes.items():
                if c == "XDIE.LINK":
                    doc.setdefault("xdie", {})[d] = law
                    continue
                if law.get("law") not in ("shape_table", "const", "affine_bytes", "ratio"):
                    continue
                if law.get("grade") in ("pending", "unmeasured"):
                    continue
                if law["law"] == "shape_table":
                    sh = {k: v for k, v in (law.get("shapes") or {}).items() if v.get("cycles") is not None}
                    if not sh and law.get("ratio") is None:
                        continue
                    law = dict(law, shapes=sh)
                doc["designs"].setdefault(d, {})[c] = dict(law, group=f.stem)
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"merged {sum(len(v) for v in doc['designs'].values())} class laws from {len(doc['sources'])} unit files")


def _tok(cyc):
    return 1e12 / (cyc * CLK_PS)


def report(model: Path, meas: Path, units: Path, out: Path):
    merged = json.loads((units.parent / "measured.json").read_text()) if (units.parent / "measured.json").exists() else {}
    res = dict(schema="opentallas.toksim_hbm_measured.v1", lane="TOKSIM-HBM",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               clock_ps=CLK_PS, die="HBM d4g GEN2e3 (pb0/die.v) masters; per-unit labels say bound / newest-bench-passing",
               method=__doc__.split("\n\n")[1], designs={})
    for d, job in DESIGNS.items():
        mj = json.loads((model / f"{job}.json").read_text())
        sj = json.loads((meas / f"{job}.json").read_text())
        rows, tot_used, tot_meas, tot_ratio = [], 0.0, 0.0, 0.0
        for c, v in sorted(sj["classes"].items(), key=lambda kv: -kv[1]["model_sum"]):
            m0 = mj["classes"].get(c, {})
            law = (merged.get("designs", {}).get(d, {}) or {}).get(c, {})
            used = v["used_sum"]
            tot_used += used
            tot_meas += v.get("measured_used", 0.0)
            tot_ratio += v.get("ratio_used", 0.0)
            rows.append(dict(cls=c, n=v["n"], model_cycles=m0.get("model_sum", v["model_sum"]),
                             measured_cycles=round(v.get("measured_used", 0.0), 1),
                             measured_model_cycles=round(v.get("measured_model", 0.0), 1),
                             measured_n=v.get("measured_n", 0), ratio_n=v.get("ratio_n", 0),
                             composed_cycles=round(used, 1),
                             meas_over_model=(round(v["measured_used"] / v["measured_model"], 3)
                                              if v.get("measured_model") else None),
                             grade=law.get("grade", "unmeasured"), group=law.get("group"),
                             where_model_wrong=law.get("where_model_wrong")))
        ph = POST_HOC[d]
        x = (merged.get("xdie") or {}).get(d)
        xd = float(x["cycles"]) if x and x.get("cycles") is not None else 0.0
        sched_m = sj["schedule_total"]
        # d4g_reprice3 post_hoc order: (schedule + pg_reset) / (1 + land %) + sm_svc
        meas_cyc = (sched_m + ph["pg_reset"] + xd) / (1 + ph["land_pct"] / 100) + ph.get("sm_svc", 0)
        model_cyc = (mj["schedule_total"] + ph["pg_reset"]) / (1 + ph["land_pct"] / 100) + ph.get("sm_svc", 0)
        pct = 100 * tot_meas / (tot_used + xd + ph.get("sm_svc", 0) + ph["pg_reset"]) if tot_used else 0.0
        pct_r = 100 * tot_ratio / (tot_used + xd + ph.get("sm_svc", 0) + ph["pg_reset"]) if tot_used else 0.0
        res["designs"][d] = dict(
            measured_schedule_cycles=round(sched_m, 1), model_schedule_cycles=round(mj["schedule_total"], 1),
            xdie_cycles=xd, xdie=x, post_hoc_unmeasured=ph,
            token_cycles_measured=round(meas_cyc, 1), tok_s_measured=round(_tok(meas_cyc), 1),
            token_cycles_model=round(model_cyc, 1), tok_s_model=round(_tok(model_cyc), 1),
            price_of_record=PRICE[d], pct_measured_exact=round(pct, 1), pct_ratio_extrapolated=round(pct_r, 1),
            pct_model_only=round(100 - pct - pct_r, 1), extrapolated_records=sj.get("extrapolated_records"),
            classes=rows)
    out.write_text(json.dumps(res, indent=1) + "\n")
    for d, r in res["designs"].items():
        print(d, "measured", r["tok_s_measured"], "tok/s", r["token_cycles_measured"], "cyc; model", r["tok_s_model"],
              "; % measured", r["pct_measured_exact"], "+ ratio", r["pct_ratio_extrapolated"])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["merge", "report"])
    ap.add_argument("--units", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", type=Path)
    ap.add_argument("--measured-jobs", type=Path)
    a = ap.parse_args()
    if a.cmd == "merge":
        merge(a.units, a.out)
    else:
        report(a.model, a.measured_jobs, a.units, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
