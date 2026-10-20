#!/bin/bash
# L2H-IDXSCORE 2026-10-19: r4 wires-only IDX quarter ot_hbm_idx_score_quarter_wo2 (W tile r4 + 8 leaf_c1 + E tile r4, compared
# at +2) vs the flat ot_hbm_idx_score_quarter_static (old leaves, old relays). Same cases / verdict lines as
# run_quarter_split_lockstep.sh (OWN-IDXSCORE 2026-10-18).
# PASS: pos half0 + pos half1 (every edge equal at +1). Must FAIL: keyline (row 1 reads row 0 key lines), auxearly (row 0 aux
# one edge early), rowswap (E tile swaps the rows' sum buses). Usage: run_quarter_split_lockstep.sh OUT [CASE...]
# CASE: pos (pos0 pos1 + both +poison_payload runs) | keyline | auxearly | rowswap; default = all (the full gate).
# A case list builds only its own vehicles (closure-loop benches: one expect=pass "pos" + one expect=fail per mutant).
set -uo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/idx-quarter-split}"); mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
"$vl" --version > "$out/verilator.version"
Q=rtl/hbm_accel/index/quad_1017
src=(rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv rtl/hbm_accel/index/ot_hbm_idx_score_cluster.sv
 $Q/ot_hbm_idx_score_quarter_static.sv $Q/ot_hbm_idx_score_quarter_wo2.sv rtl/hbm_accel/index/ot_hbm_idx_score_leaf_c1.sv
 rtl/hdc/v41x/ot_hbm_idx_chunk_rt_l.sv rtl/hdc/ot_hdc_delay_auto.sv rtl/lib/ot_rst_relay_l.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/v41x/ot_hbm_idx_chunk_rt.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/lib/ot_rst_relay.sv
 rtl/test/hbm_idx_static/tb_idx_quarter_split.sv rtl/test/hbm_idx_static/quarter_split_r4.vlt)
sha256sum "${src[@]}" rtl/test/hbm_idx_static/run_quarter_split_r4.sh > "$out/sources.sha256"
build(){ # tag half defines...
 local t=$1 h=$2; shift 2
 "$vl" --hierarchical --binary --timing --verilate-jobs "${QS_VJ:-8}" --build-jobs "${QS_BJ:-16}" -O1 -Wno-fatal -Wno-lint -Wno-style \
  -GTP=192 -GHALF=$h -DOT_QS_WO2 "$@" --top-module tb_idx_quarter_split --Mdir "$out/obj_$t" "${src[@]}" > "$out/build_$t.log" 2>&1 || { echo "[$t] BUILD FAILED"; tail -20 "$out/build_$t.log"; }
}
cases=("${@:2}"); [ ${#cases[@]} = 0 ] && cases=(pos keyline auxearly rowswap)
for c in "${cases[@]}"; do case $c in pos|keyline|auxearly|rowswap) ;; *) echo "bad case $c"; exit 2 ;; esac; done
has(){ local c; for c in "${cases[@]}"; do [ "$c" = "$1" ] && return 0; done; return 1; }
has pos && { build pos0 0; build pos1 1; }
has keyline && build keyline 0 -DOT_IDXQS_MUT_KEYLINE; has auxearly && build auxearly 0 -DOT_IDXQS_MUT_AUXEARLY
has rowswap && build rowswap 1 -DOT_IDXQS_MUT_ROWSWAP
echo BUILDS_DONE
rc=0
run(){ # executable-tag expected-verdict log-tag [runtime arguments...]
 local t=$1 want=$2 log=$3 r; shift 3
 "$out/obj_$t/Vtb_idx_quarter_split" "$@" > "$out/run_$log.log" 2>&1; r=$?
 grep -E "IDX_QUARTER_SPLIT|QSPLIT_BAD|Error" "$out/run_$log.log" | head -5 | sed "s/^/[$log] /"
 if [ "$want" = pass ]; then [ $r = 0 ] && grep -q "IDX_QUARTER_SPLIT PASS" "$out/run_$log.log" || { echo "[$log] FAILED (expected PASS)"; rc=1; }
 else [ $r != 0 ] && grep -q "QSPLIT_BAD" "$out/run_$log.log" && echo "[$log] mutant rejected" || { echo "[$log] MUTANT SURVIVED"; rc=1; }; fi
}
if has pos; then
 run pos0 pass pos0; run pos1 pass pos1
 # Reuse compiled positive vehicles with different unreset output histories.
 run pos0 pass pos0_poison +poison_payload; run pos1 pass pos1_poison +poison_payload
fi
# QS_BENCH=1 (closure-loop expect=fail mutant benches): judge a mutant like a positive, so a detected mutant exits non-zero
# with QSPLIT_BAD + IDX_QUARTER_SPLIT_GATE_FAIL (the bench's fail_regex) and a surviving one exits 0 (daemon: NEEDS_RTL).
mw=fail; [ "${QS_BENCH:-0}" = 1 ] && mw=pass
has keyline && run keyline $mw keyline; has auxearly && run auxearly $mw auxearly; has rowswap && run rowswap $mw rowswap
[ $rc = 0 ] && echo IDX_QUARTER_SPLIT_GATE_PASS || echo IDX_QUARTER_SPLIT_GATE_FAIL
exit $rc
