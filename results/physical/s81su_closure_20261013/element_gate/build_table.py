#!/usr/bin/env python3
"""[s81su-price] functional + throughput half of the element gate for the S81 SU tiles (2026-10-13).
Reads only committed records: the immutable token-path prices, the combined full hier gate JSONs and source_match.json.
    python3 source_match.py   (writes /tmp/s81su_price/srcmatch.json; copy to source_match.json)
    python3 build_table.py    (writes table.json)
No price is derived here: a job price is the listed token-path node(s) the job spans, summed, each node quoted."""
import json, subprocess
from pathlib import Path
H = Path(__file__).resolve().parent
ROOT = H.parents[3]
def show(ref, p):
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{p}"], capture_output=True, check=True).stdout
PRICE_FILE, PRICE_COMMIT = "results/arch/token_path_20261009/ds_rom.json", "00888ffb6"
tp = json.loads(show(PRICE_COMMIT, PRICE_FILE))
node = {n["id"]: n for n in tp["nodes"]}
def price(ids):
    return [dict(key=f"nodes[id={i}].cycles", cycles=node[i]["cycles"], critical=node[i]["critical"],
                 basis=node[i]["src"].get("note", "")[:260]) for i in ids]
GATE = "results/physical/s81su_closure_20261013/smt_qualification/full_gate/run_full_dpi_m%d_a0_h.json"
g0 = json.loads((ROOT / (GATE % 0)).read_text())
KN = "QN KV QB SW SE SO GQ GK".split()
runs = {r["run"]: [(KN[j["kind"]], j["done"] - j["start"]) for j in r["job_cycles"]] for r in g0["runs"]}
assert len({json.dumps(v) for v in runs.values()}) == 1 and all(r["ok"] and r["err_rows"] == 0 for r in g0["runs"])
jc = runs["golden_L0"]
meas = dict(QN=jc[2][1], KV=jc[3][1], QB=jc[4][1], SW=jc[6][1], SE_T128=jc[7][1], SO_T128=jc[8][1], SE_T640=jc[9][1], SO_T640=jc[10][1],
            GQ=jc[0][1], GK=jc[1][1])
FLAT = dict(QN=229, KV=225, QB=65, SW=201, SE_T128=196, SO_T128=112, SE_T640=275, SO_T640=112, GQ=38, GK=35)
JOBS = {  # job -> (priced nodes, priced benchmark shape, bench shape)
 "QN": (["L5.attn.q_quant"], "ot_dsrom_su_norm q N 256 D 1280, RMSNorm -> FP8 act-quant, VM read -> last quantised block at its consumer (hub in 33 / out 23 + wire 9 + 9 included)", "QN_N 256, 1,280-element q row"),
 "KV": (["L5.attn.kv_rope_qdq"], "ot_dsrom_su_norm kv N 512 D 512, RMSNorm -> RoPE -> FP8 QDQ, VM read -> last QDQ block at its consumer (hub in 33 / out 23 + wire 9 + 9 included)", "KV_N 512"),
 "QB": (["L5.attn.z_quant"], "ot_dsrom_su_qbank NB 32 QLAT 5, 2 beats (2,048 values): 76 cyc + 1 + 3", "QB_NB 32, 2 x 32 blocks (2,048 values), FP8 and FP4"),
 "SW": (["L5.ffn.quant2"], "ot_dsrom_su_swiglu W 1024 LM5/LA4/QLAT5, 4 vectors, first input -> last code (33 in + lane 116 + quant 18 + 23 out); ffn.swiglu 3.0 and ffn.route_w 5.9 are separate nodes 'covered by ffn.quant2'", "SW_W 1024, 4 vectors, route weight incl. the shared expert"),
 "SE_T640": (["L5.attn.max", "L5.attn.exp", "L5.attn.den", "L5.attn.sink"], "softmax H 16, T 640 (L3 chain): scores in -> den at the lanes", "SM_H 16, SM_LPH 16, T 640"),
 "SE_T128": (["L0.attn.max", "L0.attn.exp", "L0.attn.den", "L0.attn.sink"], "softmax H 16, T 128 (L0 sliding window)", "SM_H 16, SM_LPH 16, T 128"),
 "SO_T640": (["L5.attn.normalize"], "softmax normalize H 16: first P.V vector in -> last o out (divide + BF16 + inverse RoPE)", "SM_H 16, 16 x 512 P.V"),
 "SO_T128": (["L0.attn.normalize"], "as SO_T640 (same price at L0)", "SM_H 16, 16 x 512 P.V"),
}
jobs = {}
for k, (ids, pshape, bshape) in JOBS.items():
    pr = price(ids); tot = round(sum(p["cycles"] for p in pr), 1)
    jobs[k] = dict(measured_cycles=meas[k], flat_master_cycles=FLAT[k], price_cycles=tot, ratio=round(meas[k] / tot, 3),
                   passes_1p10=meas[k] / tot <= 1.10, price_nodes=pr, priced_shape=pshape, bench_shape=bshape,
                   critical_in_token_path=any(p["critical"] for p in pr))
for k in ("GQ", "GK"):
    jobs[k] = dict(measured_cycles=meas[k], flat_master_cycles=FLAT[k], price_cycles=None, ratio=None,
                   note="gain load: no token-path node, no immutable price exists (not a per-token op)")
TILE_JOBS = dict(ctl=list(JOBS), qnt=["QN"], qne=["QN"], qnh=["QN"], qnr=["QN"], kve=["KV"], kvp=["KV"], kvr=["KV"],
                 smt=["SE_T640", "SE_T128", "SO_T640"], sml=["SE_T640", "SE_T128"], smc=["SE_T640", "SE_T128"],
                 smr=["SE_T640", "SE_T128"], smd=["SO_T640"], swe=["SW"])
sm = json.loads((H / "source_match.json").read_text())
extra = json.loads((H / "rtl_fp_gate.json").read_text()) if (H / "rtl_fp_gate.json").exists() else None
FP = ("ot_hdc_fastfp.sv", "ot_hdc_fp32_f12.sv", "ot_hdc_fp32_mul_lat.sv", "ot_hdc_fp32_add_lat.sv", "ot_hdc_prefix.sv", "ot_dsrom_fp32_add_l6.sv")
rows = []
for r in sm:
    t = r["tile"].split("_")[-1]
    f = r["files"]; neq = [x["path"] for x in f if not x["equal_gate_commit"]]
    wrap = [x["path"] for x in f if not x["in_gate_build"] and not x["path"].endswith(FP)]
    fp = [x["path"] for x in f if x["path"].endswith(FP)]
    tj = TILE_JOBS[t]; worst = max(tj, key=lambda j: jobs[j]["ratio"])
    cb = t == "qnt"
    row = dict(tile=r["tile"], routed=f"{r['kit']} @ {r['routed_commit']}", params=r["params"],
               rtl_bytes_equal_gate_commit_b132ae0da=not neq, files_changed_vs_gate=neq,
               routed_top_wrapper_compiled_by_gate=False, wrapper_files=wrap,
               fp_primitives_in_full_gate="DPI behavioural models (su_gate --fp dpi), not the routed bytes" if fp else "none in this tile",
               exact_mutant_evidence=("results/rtl/s81su_qnt_cb_c904b01fb_20261013/final @ 70ac518d7: lockstep CB32/CB16 vs the 69c124e5d qnt (bytes = b132ae0da), all 4,305 output bits every cycle, 18,670 checks, added_cycles 0, MUT 6 FAIL; candidate sha256 e33c4f5e = routed ot_s81_su_qn.sv. Composition: " if cb else "")
               + (GATE % 0) + " (+ m1, m5) @ 47c89defd: su_gate --hier --shape full --fp dpi @ b132ae0da, m0 PASS 0/1,722 x3 cycles 3,146; m1 FAIL (1,296/1,267/1,294 rows), m5 FAIL (222/193/220)",
               jobs={j: dict(measured=jobs[j]["measured_cycles"], price=jobs[j]["price_cycles"], ratio=jobs[j]["ratio"]) for j in tj},
               limiting_job=worst, ratio=jobs[worst]["ratio"])
    miss = []
    if cb: miss.append("no composed slab gate with CB 32 (the slab default is the 69c124e5d tap; equivalence is by lockstep only)")
    miss.append("gate never compiles the routed top (" + ", ".join(Path(w).name for w in wrap) + "); its parameters equal the slab's full-shape values by inspection only")
    if fp: miss.append("production-shape gate on the routed FP primitive bytes (--fp rtl)")
    thr = [j for j in tj if not jobs[j]["passes_1p10"]]
    if thr: miss.append("throughput: " + ", ".join(f"{j} {jobs[j]['measured_cycles']} vs {jobs[j]['price_cycles']} = {jobs[j]['ratio']}x" for j in thr))
    row["verdict"] = ("NOT QUALIFIED" if thr else "throughput within 1.10 at the slab pins; functional NOT YET source-exact")
    row["missing"] = miss
    rows.append(row)
out = dict(schema="opentallas.s81su.element_gate.functional_throughput.v1", generated="2026-10-13",
           price_source=dict(file=PRICE_FILE, commit=PRICE_COMMIT, budget="results/arch/throughput_budget_20261010/budget.json @ 70bd064b2 /rom/ds_rom/classes[cls=su] (116,151.3 cyc, source = that file); name rule ^(dsfd_su_t_|ot_s81_hc_) gives the tiles status QUALIFIED with ratio null: a name rule, not a measurement"),
           measurement=dict(record=GATE % 0, record_commit="47c89defd", gate_source_commit="b132ae0da", shape=g0["shape"], params=g0["params"], fp=g0["fp"],
                            basis="slab cycles from the core accepting the job (e_cmd) to c_done_v after the job's last result row is written; behavioural VM read latency LVM 10; no die transport between VM and the slab pins. The price nodes include the old hub transport, so this is a lower bound of the die-level node.",
                            total_cycles=g0["runs"][0]["cycles"]),
           jobs=jobs, tiles=rows, rtl_fp_gate=extra)
(H / "table.json").write_text(json.dumps(out, indent=1) + "\n")
for k, v in jobs.items(): print(k, v["measured_cycles"], v["price_cycles"], v["ratio"])
for r in rows: print(r["tile"], r["routed"], r["rtl_bytes_equal_gate_commit_b132ae0da"], r["limiting_job"], r["ratio"], r["verdict"])
