#!/usr/bin/env python3
"""HBM-COLLFUSE2 (10-20): --measured inputs for the COLL-fuse / TP-8-rows recomposition on the current measured release row
(combined_1020/measured_rel_i8_su.json = TOKEN-LEAD 10-20 DS 1109.7 / Qwen 372.2 at --bw 98 --bridge 1).

  m_base.json  = measured_rel_i8_su.json unchanged (run with --qwen-tp4-rows: reproduces the committed row)
  m_tp8.json   = + Qwen SU.VOP TP-8 per-q-head shapes (nq 4) measured on the bound static SU (mr10) by HBM-COLLFUSE
                 (results/rtl/toksim_hbm_su_1019/suvop/tp8_collfuse), exp_sum 4 rows by the HBM-SUFIX affine-in-emissions
                 law (slope fitted on the measured max 1/4/8-row points) -- run WITHOUT --qwen-tp4-rows
  m_fuse.json / m_tp8_fuse.json = + lever L1 (fused last hypercube dim): Qwen COLL.ALL_REDUCE_SUM per record minus
                 (rs16 + ag16 - fx32), every term MEASURED on tb_xdie_hbm_step (Verilator 5.050): fx32 = the 'rs' kind at 32
                 frames, which IS an exchange-and-add (TX frame f and the reduce's local operand are the same VM sector).
usage: make_measured_collfuse2.py OUTDIR RS16 AG16 FX32
"""
import copy
import json
import sys
from pathlib import Path

H = Path(__file__).resolve().parent.parent            # results/token_pass/measured_hbm_1019
R = H.parents[2]
TP8 = R / "results/rtl/toksim_hbm_su_1019/suvop/tp8_collfuse"
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rs16, ag16, fx32 = (float(x) for x in sys.argv[2:5])
base = json.loads((H / "combined_1020/measured_rel_i8_su.json").read_text())


def K(d):
    return json.dumps(d, sort_keys=True)


def V(n, m, fmt="FP32"):
    return ["VM", n, m, fmt]


def prog(rec):
    p = json.loads((TP8 / rec / "programme.json").read_text())
    p["golden"] = "PASS" if "SU_TOP PASS" in (TP8 / rec / "sim_mr10.log").read_text() else "FAIL"
    return p


REC = {
    "qw8_softmax_max": dict(A=V(8192, 4), R=V(1, 4)),
    "qw8_bf16_p": dict(A=V(8192, 4), O=V(8192, 4)),
    "qw8_pv_normalize": dict(A=V(128, 4), B=V(128, 4), O=V(128, 4)),
    "qw8_round_q": dict(A=V(512, 1), O=V(512, 1)),
    "qw8_row_scale_qkv": dict(A=V(768, 1), B=V(768, 1), O=V(768, 1)),
}
shapes = {}
for rec, sk in REC.items():
    p = prog(rec)
    assert p["golden"] == "PASS", rec
    shapes[K(sk)] = dict(cycles=p["cycles_stream_833ps"], golden="PASS", rtl_master="ot_hbm_su_static_top",
                         rtl_source="claude/hd4g-gen2e3-1019@9787e078a", bound_in_die=True, verilator="5.050",
                         bench=f"prod_compile.py record {rec}; MUT_DATA witness {rec}/sim_mr10_MUT_DATA.log",
                         job=f"ot-epyc5:/srv/opentallas-scratch/claude/hbm-collfuse/suvop/vec_tp8/{rec}",
                         notes=f"TP-8 shape; serial {p['cycles_serial']} x4/3; {p['issues']} issues / {p['emissions']} emissions")
pts = [(2048, 2290), (16384, 16682)]
m4 = prog("qw8_softmax_max")
pts.append((m4["emissions"], m4["cycles_serial"]))
n = len(pts); mx = sum(x for x, _ in pts) / n; my = sum(y for _, y in pts) / n
slope = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
est = 2345 + slope * 2048 * 3
shapes[K(dict(A=V(8192, 4), B=V(1, 4), O=V(8192, 4), R=V(1, 4)))] = dict(
    cycles=round(est * 4 / 3, 2), golden="PASS", law="affine_emissions", rtl_master="ot_hbm_su_static_top",
    rtl_source="claude/hd4g-gen2e3-1019@9787e078a", bound_in_die=True, verilator="5.050",
    notes=f"measured 1-row record 2345 serial + 3 rows x 2048 emissions x {slope:.4f} (fit on max 1/4/8 rows {pts})")


def tp8(a):
    a = copy.deepcopy(a)
    sv = a["designs"]["qwen"]["SU.VOP"]
    sv["shapes"] = dict(sv["shapes"], **copy.deepcopy(shapes))
    a["sources"]["SU.VOP.qwen_tp8"] = "results/rtl/toksim_hbm_su_1019/suvop/tp8_collfuse (HBM-COLLFUSE / COLLFUSE2)"
    return a


def fuse(a):
    a = copy.deepcopy(a)
    law = a["designs"]["qwen"]["COLL.ALL_REDUCE_SUM"]
    (sk, e), = law["shapes"].items()
    d = rs16 + ag16 - fx32
    e["cycles"] = round(e["cycles"] - d, 1)
    e["bench"] += " + fused fx32 (run_xdie_hbm_step4.sh qw_rs32 on GEN2e4 11bf17f45 COLL source)"
    e["notes"] += f"; HBM-COLLFUSE2 L1: last dim RS16+AG16 ({rs16:g}+{ag16:g}) -> one fused 32-frame exchange-add {fx32:g} (-{d:g})"
    a["sources"]["qwen/COLL.ALL_REDUCE_SUM"] = "collfuse2 L1 fused (results/rtl/hbm_collfuse2_1020)"
    return a


(out / "m_base.json").write_text(json.dumps(base, indent=1) + "\n")
(out / "m_tp8.json").write_text(json.dumps(tp8(base), indent=1) + "\n")
(out / "m_fuse.json").write_text(json.dumps(fuse(base), indent=1) + "\n")
(out / "m_tp8_fuse.json").write_text(json.dumps(fuse(tp8(base)), indent=1) + "\n")
print("wrote", out, "exp_sum4", round(est * 4 / 3, 2), "slope", round(slope, 4), "fuse_delta", rs16 + ag16 - fx32)
