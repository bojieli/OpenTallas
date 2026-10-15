#!/bin/bash
# Exact production-shape bench for one native write-edge leaf (claude S81 VM F1, 2026-10-15).
# Positive: the full 53-source / 150-root wsched component (tb_dsfd_vm_static_wsched_roots, >10000 compiler-scoreboarded
# scatter writes, no reference DUT) built from the actual leaf sources incl. the native profile wrappers.
# Mutant: a defect injected into the named leaf's actual source; the same bench must FAIL.
#   leaf_bench.sh OUT LEAF CASE     LEAF = header|payload|control|dispatch|stage   CASE = base|mutant
set -eu
O=${1:?out}; LEAF=${2:?leaf}; CASE=${3:-base}
S=rtl/dsrom_sys/s81_ph/vm; T=rtl/dsrom_sys/s81_ph/test
V=${VERILATOR:-verilator}
mkdir -p "$O"
W0="$S/dsfd_vm_static_w0.sv"; define=
if [ "$CASE" = mutant ]; then
 case "$LEAF" in
  payload) define=+define+OT_VM_W0_MUT_SLICE;;
  control) define=+define+OT_VM_WSCHED_MUT_LANE;;
  dispatch) define=+define+OT_VM_WDISPATCH_MUT_SLOT;;
  stage) define=+define+OT_VM_WSTAGE_MUT_TAG;;
  header) python3 - "$W0" "$O/w0_header_mut.sv" <<'PY'
import sys
from pathlib import Path
s=Path(sys.argv[1]).read_text();n='o_row<=s_row;';assert s.count(n)==1
Path(sys.argv[2]).write_text(s.replace(n,"o_row<=s_row^{{(14*NSRC-1){1'b0}},1'b1};"))
PY
   W0="$O/w0_header_mut.sv";;
  *) echo "unknown leaf $LEAF"; exit 2;;
 esac
elif [ "$CASE" != base ]; then echo "unknown case $CASE"; exit 2; fi
"$V" --binary --timing -O1 -Wno-fatal -j 4 --top-module tb_dsfd_vm_static_wsched_roots --Mdir "$O/obj" -o tb $define \
  "$W0" "$S/dsfd_vm_static_wcontrol.sv" "$S/dsfd_vm_static_wsched.sv" "$S/dsfd_vm_static_wdispatch128.sv" \
  "$S/dsfd_vm_static_wstage128.sv" "$S/dsfd_vm_static_wdispatch128_profiles.sv" "$S/dsfd_vm_static_wstage128_profiles.sv" "$T/tb_dsfd_vm_static_wsched_roots.sv" > "$O/build.log" 2>&1
"$O/obj/tb" > "$O/run.log" 2>&1 || true
tail -3 "$O/run.log"
R=$(grep -o 'WRITE_ROOTS_RESULT sent=[0-9]* got=[0-9]* bad=[0-9]*' "$O/run.log" | head -1 || true)
if [ -z "$R" ]; then echo "WRITE_LEAF_BENCH ERROR $LEAF $CASE (no result line; see build.log/run.log)"; exit 3; fi
if grep -qx PASS "$O/run.log"; then echo "WRITE_LEAF_BENCH PASS $LEAF $CASE $R"; exit 0; fi
echo "WRITE_LEAF_BENCH FAIL $LEAF $CASE $R"; exit 1
