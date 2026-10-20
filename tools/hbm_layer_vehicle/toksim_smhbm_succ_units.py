#!/usr/bin/env python3
"""TOKSIM-HBM (10-19): units/smhbm.json for the SUCCESSOR PC controller (HBM-MC2 SAFE ot_hbm_svc_pc_ctrl_leaf_cfg_safe,
claude/l2h-bw-safe-1019) with the ROTATED layout (SMB_BSCALE 1: consecutive blocks rotate the bank set), measured in the
die-composed SM bench tb_toksim_smhbm.sv (TOKSIM_PC=safe) at the static 96-edge GO cadence (SMB_PACE 96/64 + 8).

  toksim_smhbm_succ_units.py RUNS_DIR CENSUS FIXROOT BRANCH OUT

DS: per-op occupancy of the census-row runs c_dsA_p96 / c_dsB_p96 (SMB_CENSUS_R 1 = the price's per-die rows), matched to
census shape keys by toksim_smhbm_units.py.  Qwen: the INT8 packed calendar is rejected by the bound svg S1 feed (q_* runs),
so the stream is measured BF16-widened (2x the INT8 lines) at the TP-8 rows a die holds (R = m_TP4 / 32; 1 KV head a die),
runs t_*; the INT8 record = measured BF16w span - (blocks / 2) x measured per-block cadence (slope of t_qkv48 vs t_gu192,
same K) + OP_GAP 256 (the compiled op gap the DS occupancy also carries).  The LM head (R 1,187 > 256-row descriptor
table) uses the same affine law (fit points qkv48 / gu192 / down128 / o128).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OP_GAP = 256


def main():
    runs, census, fix, branch, out = sys.argv[1:6]
    P = sys.argv[6] if len(sys.argv) > 6 else "96"                    # static GO pace (edges per 64-line block - 8)
    dsA, dsB = (sys.argv[7].split(",") if len(sys.argv) > 7 else ["c_dsA_p96", "c_dsB_p96"])
    R = Path(runs)
    tmp = Path(out).with_suffix(".ds_tmp.json")
    subprocess.run([sys.executable, str(HERE / "toksim_smhbm_units.py"), "--census", census, "--fix", fix,
                    "--ds", f"{R}/{dsA}.json,{R}/{dsB}.json", "--branch", branch, "--out", str(tmp)], check=True)
    ds = json.loads(tmp.read_text())["designs"]["ds_ar"]["SM.MATVEC"]
    tmp.unlink()
    master = ("ot_hbm_accel_smh_attn #(ENABLE_INT8 1) <- ot_hbm_svc_sm_group_rel_id <- ot_hbm_svc_vm_kshare_splitstrap <- "
              "4 x ot_hbm_svc_pc_ctrl_leaf_cfg_safe (HBM-MC2 successor; MC3 structure gives identical cycles)")
    for s in ds["shapes"].values():
        s["rtl_master"] = master
        if s.get("cycles") is not None:
            s["bound_in_die"] = False
            s["rtl_source"] = f"{branch} (GEN2e3 die sources 9787e078a + successor PC files from claude/l2h-bw-safe-1019 89200325b)"
            s["notes"] = (s.get("notes", "") + "; SUCCESSOR controller, rotated layout (SMB_BSCALE 1), static GO cadence " + P + "/64+8 (" + dsA + "," + dsB + "); "
                          "H9b (bound) reference p180/p220 in runs/dsA_p180.json dsB_p220.json")
    ds.update(grade="measured-newest-bench-passing-not-bound",
              where_model_wrong="successor+rotated sustains the 96-edge cadence (p80 also PASS); asbuilt layout FAILs at p96 (a_qkv_p96)",
              pending=[])
    # ---- Qwen
    t = {n: json.loads((R / f"t_{n}_p{P}.json").read_text())["ops"][0] for n in ("qkv48", "o128", "gu192", "down128")}
    for o in t.values():
        assert o["verdict"] == "PASS"
    slope = (t["gu192"]["span_first_cmd_to_last_result"] - t["qkv48"]["span_first_cmd_to_last_result"]) / \
        (t["gu192"]["blocks"] - t["qkv48"]["blocks"])
    fixed = t["qkv48"]["span_first_cmd_to_last_result"] - t["qkv48"]["blocks"] * slope
    cen = json.loads(Path(census).read_text())["qwen"]["classes"]["SM.MATVEC"]["shapes"]

    def key(K, m, o="VM"):
        return json.dumps({"A": ["VM", K, 1, "FP32"], "B": ["HBM", K, m, "INT8"], "O": [o, m, 1, "FP32"]})
    q = {}
    rows = [("qkv48", key(4096, 1536)), ("o128", key(1024, 4096)), ("gu192", key(4096, 6144)), ("down128", key(3072, 4096))]
    for n, k in rows:
        o = t[n]
        c = o["span_first_cmd_to_last_result"] - (o["blocks"] / 2) * slope + OP_GAP
        q[k] = dict(cycles=round(c, 1), golden="PASS", rtl_master=master, bound_in_die=False,
                    rtl_source=f"{branch} (+ successor PC files claude/l2h-bw-safe-1019 89200325b)",
                    bench="rtl/test/hbm_accel/svg_rel/tb_toksim_smhbm.sv + tools/hbm_layer_vehicle/toksim_smhbm.py (TOKSIM_PC=safe)",
                    job=f"ot-epyc5:/srv/opentallas-scratch/claude/toksim-smhbm-1019/out/t_{n}_p{P}.json", verilator="5.050",
                    measured_bf16w_span=o["span_first_cmd_to_last_result"], blocks_bf16w=o["blocks"], R_tp8=o["R"],
                    model_cost=cen[k]["model_cost"], ratio=round(c / cen[k]["model_cost"], 4),
                    notes=f"TP-8 rows R {o['R']} (census TP-4 rows / 2), BF16-widened bit-exact PASS; INT8 = span - blocks/2 x {slope:.1f} + {OP_GAP}")
    kh = key(4096, 37984, "STREAM")
    Rh = -(-(37984 // 2) // 16)
    blocks_int8 = -(-Rh // 2)
    ch = fixed + blocks_int8 * slope + OP_GAP
    q[kh] = dict(cycles=round(ch, 1), golden=None, rtl_master=master, bound_in_die=False, law_point="affine",
                 model_cost=cen[kh]["model_cost"], ratio=round(ch / cen[kh]["model_cost"], 4),
                 notes=f"LM head TP-8 R {Rh} > 256-row table: affine fixed {fixed:.1f} + {blocks_int8} INT8 blocks x {slope:.1f} + {OP_GAP} "
                       "(fit points t_qkv48/t_gu192, checked on t_down128/t_o128)")
    check = {n: round(t[n]["span_first_cmd_to_last_result"] - (fixed + t[n]["blocks"] * slope), 1) for n in t}
    rs = [(v["ratio"], cen[k]["n"] * cen[k]["model_cost"]) for k, v in q.items()]
    qm = dict(law="shape_table", shapes=q, ratio=round(sum(a * w for a, w in rs) / sum(w for _, w in rs), 4),
              grade="measured-newest-bench-passing-not-bound", affine=dict(fixed=round(fixed, 1), per_block=round(slope, 2),
                                                                           residuals=check),
              where_model_wrong="census prices TP-4 rows on a 16-SM TP-8 die (2x bytes) at 45.03 B/edge; successor+rotated = 104 edges/64-line block",
              int8_path_finding="packed INT8 calendar (ENABLE_INT8, command[116]) FAILS on the bound svg S1 feed for every pace (runs q_*): "
                                "die-integrity defect; BF16-widened stream used",
              pending=[])
    doc = dict(group="smhbm", branch=branch, updated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               controller="successor SAFE (not bound in GEN2e3), rotated layout",
               designs={"ds_ar": {"SM.MATVEC": ds}, "qwen": {"SM.MATVEC": qm}})
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")
    print("ds ratio", ds.get("ratio"), "cov", ds.get("covered_frac"), "| qwen ratio", qm["ratio"], "affine", qm["affine"])
    for k, v in q.items():
        print(" ", v["cycles"], v["model_cost"], v["ratio"])


if __name__ == "__main__":
    main()
