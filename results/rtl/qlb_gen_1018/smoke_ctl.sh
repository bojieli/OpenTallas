#!/bin/bash
# QLB-GEN 10-18: c_ctl slice smoke (reset / idle / HOST BEGIN+AUTH programme load / witness / landing probe / XPF probe)
#   smoke_ctl.sh RUN_DIR WORK_NAME [SLICE_SUBDIR=c_ctl]    (Verilator 5.050 via tools/qwen_layerbench/run_smoke.sh)
set -u
S=$(readlink -f "$1"); W=$S/post/smoke/$2; SL=$S/post/${3:-c_ctl}; SRC=$S/src; B=$(dirname $S)
mkdir -p $W
eval "$(python3 - $SL/slice.json <<'PY'
import json, re, sys
r = json.load(open(sys.argv[1])); outs = {p["port"]: p for p in r["ports"] if p["dir"] == "output"}
def one(rx):
    c = [p for p in outs if re.fullmatch(rx, p)]
    if len(c) != 1: raise SystemExit(f"echo smoke_ctl: {rx} matches {c}; exit 4")
    return c[0]
wv = one(r"o_n_sf_prog_tx_observed_v(__r\d+)?"); wr = one(r"o_n_sf_prog_tx_record(__r\d+)?"); hr = one(r"o_n_dvw_hr_wi(__r\d+)?")
t = [v["XPF_TRANSPORT_EDGES"] for v in r.get("die_params_applied", {}).values() if "XPF_TRANSPORT_EDGES" in v]
if len(t) != 1: raise SystemExit("echo smoke_ctl: XPF_TRANSPORT_EDGES not applied in the slice; exit 5")
print(f"WV={wv} WR={wr} HR={hr} XT={t[0]} UNR=\"{hr}|o_n_ng_tt_native_cmd_0\"")
PY
)"
echo "witness $WV / $WR ; hr out $HR ; XPF_TRANSPORT_EDGES $XT" > $W/smoke_params.txt
export SMOKE_UNRESET_OK="$UNR"
BENCH_FILES="$SRC/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv" \
BENCH_DEFS="+define+SMOKE_IMG=\"$B/img_ctl/img\" +define+SMOKE_WIT_V=$WV +define+SMOKE_WIT_REC=$WR +define+SMOKE_HR_OUT=$HR +define+SMOKE_XPF_T=$XT" \
  bash $SRC/tools/qwen_layerbench/run_smoke.sh $SL $W $SRC/tools/qwen_layerbench/drive_qwc_slice_ctl.svh 0 +OT_ROM_DIR=$B/img_ctl/img
