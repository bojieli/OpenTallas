#!/bin/bash
# KV-KITS-9 10-28: head bench for the KV head strap leaves (COORD 07:12 condition 2).  usage: head_strap_window_bench.sh OUTDIR [MUT]
#   MUT 0: PASS (old vs new head outputs identical every edge incl. reset + window; new == reference)
#   MUT 1: hid2 sampled KK9_MUT_DLY (default 24) edges after rp: beats then carry hid 0 -> must FAIL
set -u
R=${KK9_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}; OUT=$1; MUT=${2:-0}
TB=${KK9_TB:-$R/rtl/test/kv_core_harden/tb_head_strap_window.sv}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"
D=${KK9_MUT_DLY:-24}
R3=$R/rtl/qwen_sys/split_20261014/ot_qkh_head_native_r3.sv
R4=$R/rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4.sv
if [ "$MUT" = 1 ]; then
  grep -q 'always @(posedge clk) hid2 <= (STRAP_SAMPLE != 0 && !rp) ? 2'"'"'b00 : hid;' "$R4" || { echo "FAIL mutant anchor"; exit 1; }
  # mutant: hid2 released KK9_MUT_DLY edges after rp (python, no sed quoting)
  python3 -c "import sys; s=open(sys.argv[1]).read(); a='always @(posedge clk) hid2 <= (STRAP_SAMPLE != 0 && !rp) ? 2\'b00 : hid;'; d=int(sys.argv[3]); assert s.count(a)==1; b=f'reg [{d}-1:0] kk9_rpd = 0; always @(posedge clk) kk9_rpd <= {{kk9_rpd, rp}}; always @(posedge clk) hid2 <= (STRAP_SAMPLE != 0 && !(rp && kk9_rpd[{d}-1])) ? 2\'b00 : hid;'; open(sys.argv[2],'w').write(s.replace(a,b))" "$R4" "$OUT/r4_mut.sv" "$D" || { echo "FAIL mutant anchor"; exit 1; }
  R4=$OUT/r4_mut.sv
fi
SRC="$TB $R/rtl/qwen_sys/split_20261014/ot_qkh_head_native.sv $R3 $R4 $R/rtl/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv
 $R/rtl/hdc/nearhbm/ot_qkh_subtiles.sv $R/rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/hdc/ot_hdc_delay.sv
 $R/rtl/hdc/ot_hdc_fp32_add_lat_nr.sv $R/rtl/hdc/ot_hdc_fp32_mul_lat.sv $R/rtl/hdc/ot_hdc_fp32_mul_pipe.sv $R/rtl/hdc/ot_hdc_fastfp.sv
 $R/rtl/hdc/ot_hdc_prefix.sv $R/rtl/hdc/ot_hdc_fp32_add_lat.sv"
"$V" --binary --timing -j 16 -O1 --x-assign 0 --x-initial 0 --output-split 20000 --output-split-cfuncs 5000 \
  -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD +define+KVD_Q_FP32=1 --top-module tb_head_strap_window \
  --Mdir "$OUT/obj" -o tb $SRC > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; echo "FAIL build"; exit 2; }
"$OUT/obj/tb" > "$OUT/run.log" 2>&1; rc=$?
grep -E '^(PASS|FAIL|HEAD_|OLD_NEW|REF_NEW)' "$OUT/run.log" | head -12
rm -rf "$OUT/obj"
exit $rc
