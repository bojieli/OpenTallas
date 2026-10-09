#!/bin/bash
# mtp-hbm 2026-10-08: the DSpark control-plane bench (physical/hbm_mtp/bench/tb_hfd_mtp_dspark.sv = rtl/test/tb_dshbm_dspark.sv + HFD_MTP mode, golden-replayed trace from
# tools/dshbm_dspark_trace.py) on the die block hfd_mtp (ot_hfd_mtp_core).
#   run_bench.sh <trace dir> <out dir> [DEFINES ...]     e.g. -DHFD_MTP -DHFD_MTP_FAST -DHFD_MTP_XSEL
# env MUT=0..3 (control mutation; must FAIL).  Prints the bench's DSHBM PASS/FAIL line; exit 0 iff PASS.
set -u
T=$1; O=$2; shift 2; mkdir -p $O
R=$(cd "$(dirname "$0")/../.." && pwd)
P=$(python3 - "$T" "${MUT:-0}" <<'PY'
import json, sys
c = json.load(open(sys.argv[1] + "/cfg.json")); m = c["model"]; W = c.get("window_override") or m["window"]
p = dict(GAMMA=c["gamma"], FORCE=int(c["drafter"] == "forced"), NGEN=c["ngen"], PLEN=c["plen"], NL=m["layers"], B=m["block"],
         MUT=int(sys.argv[2]), W=W, WR=W + 8, SR=max(m["ratios"]) + 8, MAXPOS=m["max_seq_len"], ACCEPT_LEAF=0,
         NEXP=m["n_exp"], NDEXP=m["d_exp"], KV=m["k_exp"], KD=m["d_k"])
print(" ".join(f"-Ptb_dshbm_dspark.{k}={v}" for k, v in p.items()))
PY
)
S="rtl/gpu/dshbm/ot_dshbm_accept_port.sv rtl/gpu/dshbm/ot_dshbm_argmax.sv rtl/gpu/dshbm/ot_dshbm_expert_union.sv
 rtl/gpu/dshbm/ot_dshbm_spec_state.sv rtl/gpu/dshbm/ot_dshbm_spec_state_f.sv rtl/gpu/dshbm/ot_dshbm_dspark_ctl.sv
 rtl/gpu/dshbm/ot_dshbm_dspark_top.sv rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv
 rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv rtl/hdc/ot_hdc_accept.sv
 rtl/gpu/ot_gpu_router_topk.sv rtl/gpu/ot_gpu_router_topk_f.sv rtl/gpu/ot_gpu_expert_fetch.sv rtl/hdc/kv/ot_hdc_hbm_model.sv
 rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_prefix.sv physical/hbm_mtp/rtl/ot_dshbm_dspark_ctl_m.sv physical/hbm_mtp/rtl/ot_dshbm_dspark_top_m.sv
 physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv physical/hbm_mtp/rtl/ot_dshbm_expert_union_m.sv
 physical/hbm_mtp/rtl/ot_hfd_mtp_skid.sv physical/hbm_mtp/rtl/ot_hfd_mtp_core.sv
 physical/hbm_mtp/bench/tb_hfd_mtp_dspark.sv"
cd $R
iverilog -g2012 "$@" -o $O/sim.vvp -s tb_dshbm_dspark $P $S > $O/build.log 2>&1 || { echo "DSHBM FAIL build"; cat $O/build.log | head; exit 2; }
(cd $T && vvp -n $O/sim.vvp) > $O/sim.log 2>&1
L=$(grep -m1 '^DSHBM ' $O/sim.log || echo "DSHBM FAIL no-summary")
echo "$L"
grep -m5 -E "MISMATCH|TIMEOUT|FINAL" $O/sim.log
case "$L" in "DSHBM PASS"*) exit 0;; *) exit 1;; esac
