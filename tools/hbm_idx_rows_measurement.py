#!/usr/bin/env python3
"""H-MTP2/idx: collect the IDX P-row record family evidence into results/arch/hbm_mtp_1015/idx_rows/measurement.json.

Inputs (all under results/arch/hbm_mtp_1015/idx_rows/): <engine>_s<seed>/ gate outputs of rtl/test/hbm_idx_rows/
run_topk_rows.sh (vectors.log, run_*.log, vec/rows.json, sources.sha256), index_spec.json
(tools/hbm_idx_index_rows_spec.py), sens.json (tools/hbm_idx_rows_sens.py), synth_area.json.
    python3 tools/hbm_idx_rows_measurement.py
"""
import datetime
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "results/arch/hbm_mtp_1015/idx_rows"
P = 6
MODEL_TOPK_II = 47.0
ENGINES = dict(static="rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv (die-bound today, hb_idx/implementation/topk)",
               rows="rtl/hbm_accel/index/ot_hbm_idx_topk_rows_static.sv (NEW additive P-row pipelined successor)")
MUTANTS = dict(static={"M1": "rank by score", "M2": "ties to higher index", "M3": "select skips lanes 3/7",
                       "M4": "capture one edge early", "M5": "split second sector not written",
                       "H1": "heap NOT reset between rows (bench force: lanes cleared only at record start)"},
               rows={"M1": "heap NOT reset between rows", "M2": "row stride dropped (every row re-reads row 0)",
                     "M3": "lane insert rate violated (all sectors into one lane half)"})


def gate(engine, seed):
    g = D / f"{engine}_s{seed}"
    rows = json.loads((g / "vec/rows.json").read_text())
    prod = rows[:6]                      # production route.top6 shapes, in tools/hbm_idx_topk_rows_vectors.py order
    runs = {}
    for f in sorted(g.glob("run_*.log")):
        m = re.search(r"IDX_TOPK_ROWS ENGINE\d MUT(\d) MUTH(\d) records(\d+) dones(\d+) faults(\d+) sectors_checked(\d+) "
                      r"errors(\d+)", f.read_text())
        v = f.stem[4:]
        runs[v] = dict(records=int(m[3]), dones=int(m[4]), faults=int(m[5]), sectors_checked=int(m[6]),
                       errors=int(m[7]), verdict=("PASS" if int(m[7]) == 0 else "FAIL"))
    ends = [int(x) for x in re.findall(r"END_EDGE (\d+)", (g / "run_M0.log").read_text())]
    assert [r["end"] for r in rows] == ends, (engine, seed, "measured done/fault edges != compiler schedule")
    recs = [dict(m=r["m"], has_r=r["has_r"], a_str=r["a_str"], edges=r["end"] - r["G"] + 1) for r in prod]
    return dict(records=recs, runs=runs, measured_end_edges_equal_schedule=True,
                sources_sha256=dict(l.split()[::-1] for l in (g / "sources.sha256").read_text().splitlines()))


def main():
    out = dict(schema="opentallas.hbm_mtp_1015.idx_rows.v1", stream="H-MTP2/idx",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), P=P,
               vehicle="IDX.TOPK route.top6 production shape (n 384, k 6, ascending ids, REPL mirror scores, O + R) as "
                       "P1 and P-row (m = 6) records on the ACTUAL hfd_hgi_vms_static_SW slice (v15/v16 ABI: idx = "
                       "record client 2, IDX read group 4), compiler calendar replayed, every done/fault edge and every "
                       "output sector (incl. untouched neighbour words) checked against hgi_sim.machine.topk_ids; + 12 "
                       "random records (n 1..384, k 1..8, m 1..3, specials/ties/NaN) + 2 illegal descriptors; Icarus 12 "
                       "(ot-epyc4)",
               topk={})
    for e in ("static", "rows"):
        seeds = sorted(int(p.name.split("_s")[1]) for p in D.glob(f"{e}_s*") if p.is_dir())
        gs = {s: gate(e, s) for s in seeds}
        r = gs[seeds[0]]["records"]
        c1, p6 = r[0]["edges"], r[1]["edges"]
        ii = (p6 - c1) / (P - 1)
        out["topk"][e] = dict(
            engine=ENGINES[e], c1_edges=c1, p6_edges=p6, ii_edges=round(ii, 2),
            ii_over_model=round(ii / MODEL_TOPK_II, 3), model_ii=MODEL_TOPK_II,
            p6_other_shapes={f"m{x['m']}_r{x['has_r']}_astr{x['a_str']}": x["edges"] for x in r[2:]},
            serial_6xP1=6 * c1, exact_all_seeds=all(g["runs"]["M0"]["verdict"] == "PASS" for g in gs.values()),
            mutants={k: dict(what=w, killed_all_seeds=all(g["runs"][k]["verdict"] == "FAIL" for g in gs.values()),
                             errors={s: g["runs"][k]["errors"] for s, g in gs.items()}) for k, w in MUTANTS[e].items()},
            seeds=gs)
    out["topk"]["rows"]["timeline"] = ("per row: ROW 1 + ns reads (one sector an edge) -> II = ns + 1 = 49 at n 384 "
                                       "(aligned); select 5 k + rank/pack 4 + writes overlap the next row's reads")
    out["union_spec"] = dict(
        status="SPEC ONLY (not built)",
        form="UNION mode of the P-row TOPK record (descriptor bit; no new opcode): every row's k ids (already on o_w at PK1) "
             "OR into a 384-b expert bitmap (bit = id; cleared at CHK); after the last row the engine writes the "
             "ascending union ids, 8 an edge (one sector a write slot, byte masks), plus the count U in one word",
        cost_edges="+ceil(U / 8) + 1 write slots + ~3 encode edges after the last row's writes (U = 23.9 mean at P 6, "
                   "<= 36): ~8 edges vs a separate union record (~150 edges static TOPK / 283 price) a layer",
        area="384 flops + 8 cascaded 64-b leading-one encoders: ~0.001-0.002 mm2 (estimate)",
        exactness="ids only (no arithmetic); golden = sorted(set(ids of all P rows))",
    )
    for f in ("index_spec.json", "sens.json", "synth_area.json"):
        p = D / f
        if p.exists():
            out[f.split(".")[0]] = json.loads(p.read_text())
    srcs = ["rtl/hbm_accel/index/ot_hbm_idx_topk_rows_static.sv", "rtl/test/hbm_idx_rows/tb_idx_topk_rows.sv",
            "rtl/test/hbm_idx_rows/run_topk_rows.sh", "tools/hbm_idx_topk_rows_vectors.py",
            "tools/hbm_idx_index_rows_spec.py", "tools/hbm_idx_rows_sens.py", "tools/hbm_idx_rows_measurement.py",
            "tools/hbm_idx_static_calendar.py", "rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv"]
    out["source_sha256"] = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in srcs}
    (D / "measurement.json").write_text(json.dumps(out, indent=1) + "\n")
    for e in ("static", "rows"):
        t = out["topk"][e]
        print(e, "c1", t["c1_edges"], "P6", t["p6_edges"], "II", t["ii_edges"], "x model", t["ii_over_model"],
              "exact", t["exact_all_seeds"], {k: v["killed_all_seeds"] for k, v in t["mutants"].items()})


if __name__ == "__main__":
    main()
