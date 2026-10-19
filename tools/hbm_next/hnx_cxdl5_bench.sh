#!/bin/bash
# HBM-NEXT-UNITS-COLL 2026-10-19: L = 5 delivery landing bench (rtl/hbm_next/coll/ot_hnx_su_cxdl5.sv, tb_hnx_su_cxdl5),
# fleet, Verilator 5.050. Run from a bundle root:  tools/hbm_next/hnx_cxdl5_bench.sh OUT [MUTS]
#  MUT 0 must print CXDL5 PASS; MUT 11 / 12 / 13 must print CXDL5 FAIL (fail witnesses).
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); MUTS=${2:-0 11 12 13}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null)"
SRC=(rtl/hbm_next/coll/tb/tb_hnx_su_cxdl5.sv rtl/hbm_next/coll/ot_hnx_su_cxdl5.sv
     rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv)
sha256sum "${SRC[@]}" tools/hbm_next/hnx_cxdl5_bench.sh > "$O/sources.sha256"
FL=(--binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-BLKSEQ --top-module tb_hnx_su_cxdl5)
one(){ local m=$1 d=$O/obj_m$1
 verilator "${FL[@]}" -j 4 -GMUT=$m --Mdir $d -o Vm$m "${SRC[@]}" > $O/build_m$m.log 2>&1 || { sleep 5;
 verilator "${FL[@]}" -j 1 -GMUT=$m --Mdir $d -o Vm$m "${SRC[@]}" > $O/build_m$m.log 2>&1; }
 [ -x $d/Vm$m ] || { V "m$m BUILD_FAILED $(grep -m1 -i error $O/build_m$m.log)"; return; }
 $d/Vm$m > $O/m$m.log 2>&1; echo "RUN_RC=$?" >> $O/m$m.log
 V "m$m: $(grep -h '^CXDL5 PASS\|^CXDL5 FAIL' $O/m$m.log | head -1)"
 rm -rf $d
}
for m in $MUTS; do one $m & done
wait
V "done"
