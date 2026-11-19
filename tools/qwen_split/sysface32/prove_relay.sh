#!/bin/bash
# prove_relay.sh OLD_CORE.sv LIB_DIR [OUT]   (FABLE-FIX-S81-GLUE 2026-11-19)
# qfd_sys_face_lctx3_core with the define OT_QC_SF_PROG_RELAY: off must equal OLD_CORE exactly; on must equal OLD_CORE plus a
# one-cycle relay on tt_pw and seq_dh[186:44] only (unbounded one-step induction, submodules as blackboxes).
# OLD_CORE = the core before the define: git show 92b29f6c5791:rtl/qwen_split/qfd_sys_face_lctx3_core.sv
# LIB_DIR  = a directory holding the sources of every submodule (a QC glue kit's rtl/ directory).
set -eu
OLD=$(readlink -f "$1"); LIB=$(readlink -f "$2"); O=$(mkdir -p "${3:-bench/prove_relay}" && readlink -f "${3:-bench/prove_relay}")
cd "$(dirname "$0")/../../.."
Y=${YOSYS:-/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys}
NEW=rtl/qwen_split/qfd_sys_face_lctx3_core.sv; T=qfd_sys_face_lctx3_core
LIBS=$(ls "$LIB"/*.sv "$LIB"/*.v | grep -v "/$T.sv" | tr '\n' ' ')
syn() { "$Y" -Q -q -l "$O/$1.log" -p "read_verilog -sv -lib $LIBS; read_verilog -sv $3 $2; hierarchy -top $T; synth -top $T -noabc -nofsm; write_json $O/$1.json" >/dev/null 2>&1 || { tail -3 "$O/$1.log"; exit 1; }; }
syn old "$OLD" ''; syn off $NEW ''; syn on $NEW -DOT_QC_SF_PROG_RELAY
for m in off on; do
  F=; [ $m = off ] && F=--no-relay
  python3 -I tools/qwen_split/sysface32/prove_relay.py "$O/old.json" "$O/$m.json" $T "$O/miter_$m.sv" $F | tee "$O/miter_$m.txt"
  "$Y" -Q -q -l "$O/sat_$m.log" -p "read_verilog $O/miter_$m.sv; prep -top relay_miter; sat -verify -prove bad 0" >/dev/null 2>&1 || { echo "PROVE_RELAY_FAIL $m"; exit 1; }
  grep -q 'SAT proof finished - no model found: SUCCESS!' "$O/sat_$m.log" && echo "PROVE_RELAY_PASS $m"
done
