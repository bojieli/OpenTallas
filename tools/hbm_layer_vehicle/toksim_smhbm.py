#!/usr/bin/env python3
"""TOKSIM-HBM-smhbm (10-19): SM.MATVEC with its HBM weight stream on the GEN2e3 d4g die composition, cycle-accurate.

Wraps smb_unit.py (HBM-SMBUDGET compiler + checks, unchanged) and only swaps the bench and the source set:
  tb_toksim_smhbm.sv = tb_hbm_svg_rel_sm re-composed as die.v binds one SM (svg ID_COHORT 1 -> vmks_splitstrap KRL1 ->
  4 x ot_hbm_svc_pc_ctrl_leaf_cfg_h9b -> DRAM timing fixture; SM ot_hbm_accel_smh_attn ENABLE_INT8 1).
Every RTL file comes from THIS tree (branch from claude/hd4g-gen2e3-1019 9787e078a, the die source; file hashes checked
against artifacts/hdie-d4/d4g_gen2e3/synmeta_a by the lane), with simulation SRAM models.

  toksim_smhbm.py run --fix FIX --smw SMW --work W --out J --layers L14:14 --name x   (+ smb_unit env pacing knobs)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import smb_unit as S  # noqa: E402

ROOT = S.ROOT
TB = "rtl/test/hbm_accel/svg_rel/tb_toksim_smhbm.sv"
SM_FILES = """physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_hdc_prefix.sv
rtl/gpu/ot_gpu_bd_col.sv rtl/gpu/ot_gpu_fadd.sv rtl/gpu/ot_gpu_stack.sv rtl/gpu/ot_gpu_tc_col.sv rtl/gpu/ot_gpu_tree.sv
rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv
rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_be.sv
rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_front_static.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_leafh.sv
rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_native_col.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_pstore.sv
rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_tile.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_desc_static.sv
rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_line.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge.sv
rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv rtl/hbm_accel/sm/static/ot_smh_static_int8.sv
rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv rtl/hbm_accel/sm/ot_hbm_accel_smh.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv
rtl/hbm_accel/sm/ot_hbm_accel_smh_gu.sv rtl/hbm_accel/sm/ot_hbm_accel_stack.sv
rtl/hbm_accel/sm/static/ot_smh_static_feed.sv rtl/hbm_accel/sm/static/ot_smh_static_front.sv
rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fpu.sv
rtl/hdc/ot_hdc_sfu.sv rtl/lib/ot_hdly.sv rtl/lib/ot_rst_relay.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_bterm2.sv""".split()
SN = "rtl/hbm_accel/loader/service_native/"
SVC_FILES = [SN + f for f in """ot_hbm_svc_async_fifo.sv ot_hbm_svc_sm8_landing_bank.sv ot_hbm_svc_static_sm_packed136.sv
ot_hbm_svc_prefetch_overlap_owner_rel_id.sv ot_hbm_svc_sm4pc_cdc_rel_id.sv ot_hbm_svc_sm_issuer_rel.sv
ot_hbm_svc_sm_feed_programmed_rel_id.sv ot_hbm_svc_sm_group_rel_id.sv ot_hbm_svc_sm_xcal_rel.sv ot_hbm_svc_sm_xcal_rel_t.sv
ot_hbm_svc_vm_kshare_splitstrap.sv ot_hbm_svc_ring_h9b.sv ot_hbm_svc_ring_h9b_ff.sv ot_hbm_svc_pin_skid2_h9.sv
ot_hbm_svc_pc_ctrl_leaf.sv ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv""".split()] + \
    ["rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv", "rtl/lib/ot_reset_sync.sv",
     "rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv", "rtl/hbm_accel/host_static_20261015/ot_static_run_target.sv",
     "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v",
     "physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v",
     "rtl/test/hbm_accel/svg_rel/tb_svg_rel_dram_sparse.sv"]


def build(work: Path, bundle, defines):
    tag = "_".join(d.replace("=", "") for d in defines) or "base"
    rev = (ROOT / "REV").read_text().strip()[:9] if (ROOT / "REV").exists() else "wt"
    obj = work / f"obj_die_{tag}_{rev}"
    exe = obj / "Vtb_toksim_smhbm"
    if exe.exists():
        return exe
    files = []
    for p in SM_FILES + SVC_FILES + [TB]:
        if p not in files:
            files.append(p)
    files = [ROOT / p for p in files]
    miss = [str(p) for p in files if not p.exists()]
    if miss:
        raise SystemExit(f"missing sources {miss}")
    vl = os.environ.get("VERILATOR") or os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
    incs = sorted({str(p.parent) for p in files})
    cmd = [vl, "--binary", "-j", os.environ.get("VL_JOBS", "16"), "-O1", "-CFLAGS", "-O1", "--x-assign", "fast",
           "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--unroll-count", "256",
           "--timing", "--top-module", "tb_toksim_smhbm", "--Mdir", str(obj)] + \
          [f"-D{d}" for d in S.MV.DIE_DEFINES + list(defines)] + [f"-I{i}" for i in incs] + [str(f) for f in files]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (work / f"build_die_{tag}.log").write_text(" ".join(cmd) + "\n" + r.stdout[-20000:] + r.stderr[-20000:] +
                                               f"\nBUILD_RC {r.returncode} wall {time.time() - t0:.0f} s\n")
    if r.returncode != 0:
        raise SystemExit(f"build failed (see {work}/build_die_{tag}.log)")
    return exe


S.build = build
_lr = S.layer_records


def layer_records(fix, smw):
    """SMB_CENSUS_R=1: rows per SM = ceil(m / 16) (the price model's per-die placement, census bytes_B) instead of the
    fixture's d4g halves ceil(ceil(m / 2) / 16)."""
    out = _lr(fix, smw)
    if os.environ.get("SMB_CENSUS_R") == "1":
        for r in out:
            r["R"] = -(-r["m"] // 16)
    return out


S.layer_records = layer_records
for _k in ("OP_GAP", "X_GAP", "DRAIN", "BUSY"):
    if os.environ.get("SMB_" + _k):
        setattr(S, _k, int(os.environ["SMB_" + _k]))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "run" and "--bundle" not in argv:
        argv += ["--bundle", str(ROOT)]
    rc = S.main(argv)
    # annotate the result with the die composition and the static-schedule knobs actually used
    if argv and argv[0] == "run":
        out = Path(argv[argv.index("--out") + 1])
        if out.exists():
            d = json.loads(out.read_text())
            d["rtl"] = ("cp_svg ot_static_run_target -> ot_hbm_svc_sm_group_rel_id #(ID_COHORT 1) -> "
                        "ot_hbm_svc_vm_kshare_splitstrap #(KRL1 1) -> 4 x ot_hbm_svc_pc_ctrl_leaf_cfg_h9b (die params) -> "
                        "DRAM timing fixture; xc ot_hbm_svc_sm_xcal_rel_t; SM ot_hbm_accel_smh_attn #(ENABLE_INT8 1); "
                        "tb_toksim_smhbm.sv, Verilator 5.050 (GEN2e3 die composition)")
            d["static_schedule"] = dict(first_go=S.FIRST_GO, op_gap=S.OP_GAP, x_gap=S.X_GAP, pace_num=S.PACE_NUM,
                                        pace_den=S.PACE_DEN, pace_add=S.PACE_ADD, fetch=S.FETCH, expert_first=S.EXP_FIRST,
                                        ids_lag=S.IDS_LAG, bscale=S.BSCALE)
            d["source_revision"] = (ROOT / "REV").read_text().strip() if (ROOT / "REV").exists() else None
            out.write_text(json.dumps(d, indent=1, default=str) + "\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
