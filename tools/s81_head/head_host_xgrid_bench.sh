#!/usr/bin/env bash
# DH81-HOST lockstep: production plus mutants 1-6, MODE 0 and 1; plus default-off token identity. Fleet host only.
set -uo pipefail
S=/srv/opentallas-scratch2/claude/dh81-host/bench/src; B=/srv/opentallas-scratch2/claude/dh81-host/bench
O=${1:?out}; [ -e "$O" ] && { echo exists; exit 2; }; mkdir -p "$O"; cd "$S"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; CORE=rtl/dsrom_sys/s81_head/ot_s81hd_host_ep_core.sv
python3 -I tools/s81_dv/hostctx_1021/gen_vectors.py "$O/vec" >"$O/gen.log" || exit 3
python3 -I "$B/tb.py" rtl/dsrom_sys/s81_head/test/tb_s81hd_host_split_lockstep.sv "$O/tb.sv" || exit 3
# default off: preprocessed token stream equal to the pinned file
"$V" -E -P "$B/core_base.sv" 2>/dev/null | grep -v '^\s*$' | sha256sum > "$O/pp_base.sha"
"$V" -E -P "$CORE" 2>/dev/null | grep -v '^\s*$' | sha256sum > "$O/pp_new.sha"
cmp "$O/pp_base.sha" "$O/pp_new.sha" && echo "DEFAULT_OFF_TOKEN_IDENTICAL $(cut -c1-16 "$O/pp_new.sha")" | tee "$O/default.txt"
grep -v 'ot_s81hd_host_w_core\|ot_s81hd_host_e_core' "$B/sources.f" > "$O/src.f"
for m in ${MUTS:-0 1 2 3 4 5 6}; do
 { echo '`define OT_S81HD_HOST_XGRID'; echo "\`define OT_S81HD_HOST_XGRID_MUT $m"
   sed -e 's/\bot_s81hd_host_ep_core\b/ot_s81hd_host_ep_core_xg/g' -e 's/\bot_s81hd_host_frame_mux\b/ot_s81hd_host_frame_mux_xg/g' "$CORE"
   echo '`undef OT_S81HD_HOST_XGRID'; echo '`undef OT_S81HD_HOST_XGRID_MUT'; } > "$O/core_xg_$m.sv"
 for mode in 0 1; do
  "$V" --binary --timing -O1 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_s81hd_host_xgrid_lockstep -GSPLIT_MUT="$m" -GMODE="$mode" \
   +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF -Mdir "$O/obj_${m}_$mode" -f "$O/src.f" "$O/core_xg_$m.sv" "$O/tb.sv" --build-jobs 4 >"$O/build_${m}_$mode.log" 2>&1 || { echo "mut$m mode$mode BUILD_FAIL" | tee -a "$O/rc.txt"; continue; }
  "$O/obj_${m}_$mode/Vtb_s81hd_host_xgrid_lockstep" +VEC="$O/vec" +SEED=${SEED:-11} >"$O/run_${m}_$mode.log" 2>&1
  echo "mut$m mode$mode rc$? $(grep -m1 -E 'MISMATCH|PASS' "$O/run_${m}_$mode.log" | cut -c1-170)" | tee -a "$O/rc.txt"
  rm -rf "$O/obj_${m}_$mode"
 done
done
echo BENCH_DONE
