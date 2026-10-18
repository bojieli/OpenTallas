#!/bin/bash
# RBH-SFUS 10-18: kit bench of the subr_<q> leaf (ot_hbm_su_bridge_release, RTL unchanged) -- tb_hbm_su_bridge_release
# against the ideal phase-zero release on two real ot_hbm_su_multirate_bridge instances.
# usage: run_bridge_release.sh OUT MODE   MODE = pos (4 aligned runs, PASS) | misalign (restart off-epoch: fault REQUIRED)
#                                               | mut1 (release one stream edge early) | mut2 (one edge late)
set -uo pipefail
cd "$(dirname "$0")/../../../../../.."
OUT=$(realpath -m "${1:?out}"); MODE=${2:?mode}; mkdir -p "$OUT"
S=rtl/hbm_accel/generic/adapters/static_su
br=($S/top/tb_hbm_su_bridge_release.sv $S/top/ot_hbm_su_bridge_release.sv $S/programme/multirate_bridge.sv)
sha256sum "${br[@]}" > "$OUT/sources_$MODE.sha256"
case $MODE in pos|misalign) m=0;; mut1) m=1;; mut2) m=2;; *) echo "bad mode"; exit 2;; esac
iverilog -g2012 -Ptb_hbm_su_bridge_release.MUT=$m -o "$OUT/br_$MODE.vvp" "${br[@]}" || { echo "BRIDGE_RELEASE BUILD FAIL"; exit 2; }
case $MODE in pos) args="+RUNS=4";; misalign) args="+RUNS=3 +MISALIGN";; *) args="";; esac
vvp -n "$OUT/br_$MODE.vvp" $args 2>&1 | tee "$OUT/bridge_$MODE.log"; r=${PIPESTATUS[0]}
rm -f "$OUT/br_$MODE.vvp"
if [ $MODE = misalign ]; then
  grep -q "leaf_fault=1" "$OUT/bridge_$MODE.log" && grep -q "BRIDGE_RELEASE PASS" "$OUT/bridge_$MODE.log" && [ $r = 0 ] \
    && { echo "BRIDGE_RELEASE_GATE PASS misalign faulted"; exit 0; }
  echo "BRIDGE_RELEASE_GATE FAIL misalign"; exit 1
fi
grep -q "BRIDGE_RELEASE PASS" "$OUT/bridge_$MODE.log" && [ $r = 0 ] && { echo "BRIDGE_RELEASE_GATE PASS $MODE"; exit 0; }
echo "BRIDGE_RELEASE_GATE FAIL $MODE rc=$r"; exit 1
