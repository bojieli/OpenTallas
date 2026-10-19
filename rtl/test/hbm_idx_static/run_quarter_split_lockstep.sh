#!/bin/bash
# OWN-IDXSCORE 2026-10-18: wires-only IDX quarter (W tile + 8 leaves + E tile) vs flat ot_hbm_idx_score_quarter_static.
# PASS: pos half0 + pos half1 (every edge equal at +1). Must FAIL: keyline (row 1 reads row 0 key lines), auxearly (row 0 aux
# one edge early), rowswap (E tile swaps the rows' sum buses). Usage: run_quarter_split_lockstep.sh OUT
set -uo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/idx-quarter-split}"); mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
"$vl" --version > "$out/verilator.version"
Q=rtl/hbm_accel/index/quad_1017
src=(rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv rtl/hbm_accel/index/ot_hbm_idx_score_cluster.sv
 $Q/ot_hbm_idx_score_quarter_static.sv $Q/ot_hbm_idx_score_quarter_split.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/v41x/ot_hbm_idx_chunk_rt.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/lib/ot_rst_relay.sv
 rtl/test/hbm_idx_static/tb_idx_quarter_split.sv rtl/test/hbm_idx_static/quarter_split.vlt)
sha256sum "${src[@]}" rtl/test/hbm_idx_static/run_quarter_split_lockstep.sh > "$out/sources.sha256"
build(){ # tag half defines...
 local t=$1 h=$2; shift 2
 "$vl" --hierarchical --binary --timing --verilate-jobs "${QS_VJ:-8}" --build-jobs "${QS_BJ:-16}" -O1 -Wno-fatal -Wno-lint -Wno-style \
  -GTP=192 -GHALF=$h "$@" --top-module tb_idx_quarter_split --Mdir "$out/obj_$t" "${src[@]}" > "$out/build_$t.log" 2>&1 || { echo "[$t] BUILD FAILED"; tail -20 "$out/build_$t.log"; }
}
build pos0 0; build pos1 1; build keyline 0 -DOT_IDXQS_MUT_KEYLINE; build auxearly 0 -DOT_IDXQS_MUT_AUXEARLY; build rowswap 1 -DOT_IDXQS_MUT_ROWSWAP
echo BUILDS_DONE
rc=0
run(){ # tag want
 local r; "$out/obj_$1/Vtb_idx_quarter_split" > "$out/run_$1.log" 2>&1; r=$?
 grep -E "IDX_QUARTER_SPLIT|QSPLIT_BAD|Error" "$out/run_$1.log" | head -5 | sed "s/^/[$1] /"
 if [ "$2" = pass ]; then [ $r = 0 ] && grep -q "IDX_QUARTER_SPLIT PASS" "$out/run_$1.log" || { echo "[$1] FAILED (expected PASS)"; rc=1; }
 else [ $r != 0 ] && grep -q "QSPLIT_BAD" "$out/run_$1.log" && echo "[$1] mutant rejected" || { echo "[$1] MUTANT SURVIVED"; rc=1; }; fi
}
run pos0 pass; run pos1 pass; run keyline fail; run auxearly fail; run rowswap fail
[ $rc = 0 ] && echo IDX_QUARTER_SPLIT_GATE_PASS || echo IDX_QUARTER_SPLIT_GATE_FAIL
exit $rc
