#!/usr/bin/env python3
"""HBM-QINT8B (10-20): units_variants/smhbm_int8w.json -- Qwen SM.MATVEC measured on the WIDE INT8 front (ot_hbm_sm_i8w_front,
ot_hbm_accel_smh_attn INT8W 1, command mode 3: one 136-B packed line of 128 INT8 codes an edge = rows A/B of one chunk)
through the die-composed SM bench tb_toksim_smhbm.sv (-DTOKSIM_I8W) and the MC3 successor PC controller (TOKSIM_PC=mc3,
rotated layout via hbm_bank_layout.static_run, SMB_BSCALE 1).  Block = 64 packed lines (one wave of 8 A-items).

  toksim_smhbm_int8_units.py RUNS_DIR CENSUS BRANCH OUT PACE [BASE_UNITS]

Per TP-8 shape (R = m_TP4 / 32 rows per SM, 1 KV head a die): cycles = measured span (first command -> last result) +
OP_GAP 256 (the compiled op gap, as units/smhbm.json).  The LM head (R 1,187 > 256-row descriptor table) uses the affine
law fitted on the INT8 runs (fixed + per-block x blocks, fit points qkv48 / gu192, checked on o128 / down128).
DS entries are copied unchanged from BASE_UNITS (units/smhbm.json) so the file is a drop-in smhbm unit.
"""
import json
import sys
from pathlib import Path

OP_GAP = 256
PFX = __import__("os").environ.get("I8_PREFIX", "w8")   # run-name prefix (final-RTL runs)
SHAPES = [("qkv48", 4096, 1536), ("o128", 1024, 4096), ("gu192", 4096, 6144), ("down128", 3072, 4096)]


def key(K, m, o="VM"):
    return json.dumps({"A": ["VM", K, 1, "FP32"], "B": ["HBM", K, m, "INT8"], "O": [o, m, 1, "FP32"]})


def main():
    runs, census, branch, out, P = sys.argv[1:6]
    base = json.loads(Path(sys.argv[6]).read_text()) if len(sys.argv) > 6 else None
    R = Path(runs)
    t = {}
    for n, _, _ in SHAPES:
        d = json.loads((R / f"{PFX}_{n}_p{P}.json").read_text())
        o = d["ops"][0]
        assert d["verdict"] == "PASS" and o["verdict"] == "PASS" and o["fmt"] == "INT8", (n, d["verdict"])
        t[n] = o
    slope = (t["gu192"]["span_first_cmd_to_last_result"] - t["qkv48"]["span_first_cmd_to_last_result"]) / \
        (t["gu192"]["blocks"] - t["qkv48"]["blocks"])
    fixed = t["qkv48"]["span_first_cmd_to_last_result"] - t["qkv48"]["blocks"] * slope
    cen = json.loads(Path(census).read_text())["qwen"]["classes"]["SM.MATVEC"]["shapes"]
    master = ("ot_hbm_accel_smh_attn #(ENABLE_INT8 1, INT8W 1) (ot_hbm_sm_i8w_front, HBM-QINT8B) <- ot_hbm_svc_sm_group_rel_id <- "
              "ot_hbm_svc_vm_kshare_splitstrap <- 4 x ot_hbm_svc_pc_ctrl_leaf_cfg_safe MC3 (successor)")
    q = {}
    for n, K, m in SHAPES:
        o = t[n]
        k = key(K, m)
        c = o["span_first_cmd_to_last_result"] + OP_GAP
        q[k] = dict(cycles=float(c), golden="PASS", rtl_master=master, bound_in_die=False, rtl_source=branch,
                    bench="rtl/test/hbm_accel/svg_rel/tb_toksim_smhbm.sv + tools/hbm_layer_vehicle/toksim_smhbm.py "
                          "(TOKSIM_PC=mc3 TOKSIM_QWEN_MODE=int8w -DTOKSIM_I8W)",
                    job=f"ot-epyc5:/srv/opentallas-scratch2/claude/hbm-qint8b-1020/tok/out/{PFX}_{n}_p{P}.json", verilator="5.050",
                    measured_int8_span=o["span_first_cmd_to_last_result"], blocks_int8=o["blocks"], lines_int8=o["lines"],
                    bytes_hbm=o["bytes_hbm"], R_tp8=o["R"], model_cost=cen[k]["model_cost"],
                    ratio=round(c / cen[k]["model_cost"], 4),
                    notes=f"WIDE INT8 front measured directly (mode 3, 64 packed lines / 64-word block, one line an edge), bit-exact PASS, pace {P}/64+8 (HBM-bound: p72/p64 fault at the svg cdc)")
    kh = key(4096, 37984, "STREAM")
    Rh = -(-(37984 // 2) // 16)
    blocks = -(-Rh // 2)               # wide: A rows = ceil(Rh / 2) x Gn 8 groups = 8 A-items = one 64-line block a row
    ch = fixed + blocks * slope + OP_GAP
    q[kh] = dict(cycles=round(ch, 1), golden=None, rtl_master=master, bound_in_die=False, law_point="affine",
                 model_cost=cen[kh]["model_cost"], ratio=round(ch / cen[kh]["model_cost"], 4),
                 notes=f"LM head TP-8 R {Rh} > 256-row table: affine fixed {fixed:.1f} + {blocks} wide INT8 blocks x {slope:.2f} + {OP_GAP} "
                       "(fit qkv48/gu192 wide runs)")
    check = {n: round(t[n]["span_first_cmd_to_last_result"] - (fixed + t[n]["blocks"] * slope), 1) for n in t}
    rs = [(v["ratio"], cen[k]["n"] * cen[k]["model_cost"]) for k, v in q.items()]
    qm = dict(law="shape_table", shapes=q, ratio=round(sum(a * w for a, w in rs) / sum(w for _, w in rs), 4),
              grade="measured-newest-bench-passing-not-bound",
              affine=dict(fixed=round(fixed, 1), per_block=round(slope, 2), residuals=check),
              int8_path_finding="wide INT8 front: one packed line an edge (128 codes/edge), HBM-bound at pace 80/64+8 "
                                "(88 edges / 64-line block vs 136 on the narrow front)",
              pending=["INT8W bound in the die SM master (HBM-DIE6)", "x-load p=5 parts on the die x-loader (columns 0 and 4)",
                       "VM writer descriptor P=2, rows B = A + 8*stride (compiler)"])
    doc = dict(group="smhbm", variant="int8w", branch=branch, controller="successor MC3 (not bound), rotated layout",
               pace=int(P), designs=dict(qwen={"SM.MATVEC": qm}))
    if base:
        doc["designs"]["ds_ar"] = base["designs"]["ds_ar"]
        doc["ds_from"] = "units/smhbm.json (unchanged)"
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(dict(fixed=fixed, slope=slope, check=check, cycles={n: q[key(K, m)]["cycles"] for n, K, m in SHAPES},
                          head=ch)))


if __name__ == "__main__":
    main()
