#!/bin/bash
# Production-shape bench for a hardened static VM control leaf (rsched / landing / core glue): the leaf's ACTUAL RTL
# inside the full real dsfd_vm_static_core composition (128 SRAM macro models, return lanes, read router, wsched),
# base calendar or one DUT mutant compiled into the leaf.  Prints CORE_LEAF PASS|FAIL <label>.
# Usage: tools/s81_vm/core_leaf_bench.sh OUTDIR LABEL [MUTANT_DEFINE] [READS]
set -u
cd "$(dirname "$0")/../.."
O=${1:?outdir}; L=${2:?label}; M=${3:-}; READS=${4:-2000}; mkdir -p "$O/src"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
cp rtl/dsrom_sys/s81_ph/vm/*.sv rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_static_core.sv "$O/src/"
cp physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v "$O/src/"
FILES=$(sed -n '/^FILES="/,/"$/p' tools/s81_vm/static_core_gate.sh | tr -d '"' | sed 's/^FILES=//')
F=""; for f in $FILES; do F="$F $O/src/$f"; done
D=""; for m in $M; do D="$D +define+$m"; done   # MUTANT_DEFINE may list several defines (e.g. "OT_VM_NATIVE_READ_L16 OT_VM_RSCHED_MUT_SLOT")
"$V" --binary --timing -O1 -Wno-fatal -j 2 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" --top-module tb_dsfd_vm_static_core \
  --Mdir "$O/obj" -o tb $D $F > "$O/build.log" 2>&1 || { tail -20 "$O/build.log"; echo "CORE_LEAF FAIL $L build"; exit 1; }
"$O/obj/tb" +mode=0 +seed=1 +reads=$READS > "$O/run.log" 2>&1
grep -h "RESULT" "$O/run.log"
if grep -q "TB_VMCORE PASS mode 0" "$O/run.log" && ! grep -q "TB_VMCORE FAIL" "$O/run.log"; then echo "CORE_LEAF PASS $L"; else echo "CORE_LEAF FAIL $L"; exit 1; fi
