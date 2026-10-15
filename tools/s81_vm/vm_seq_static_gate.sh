#!/usr/bin/env bash
# Exact gate of the static VM sequencer engine 12 (dsfd_vm_seq_static): 3 base seeds at production density,
# 6 fault witnesses (each must raise exactly its fault), 4 mutants (each must FAIL the base calendar).
# Usage: tools/s81_vm/vm_seq_static_gate.sh OUTDIR [JOBS]
set -u
cd "$(dirname "$0")/../.."
OUT=${1:?outdir}; JOBS=${2:-1500}; mkdir -p "$OUT"
R=rtl/dsrom_sys/s81_ph; SRC="$R/vm/dsfd_vm_seq_static.sv $R/test/tb_dsfd_vm_seq_static.sv"
bad=0
iverilog -g2012 -o "$OUT/sim" -s tb_dsfd_vm_seq_static $SRC || exit 2
for s in 1 2 3; do vvp -n "$OUT/sim" +mode=0 +jobs=$JOBS +seed=$s > "$OUT/base_s$s.log"; grep -q "TB_VMSS PASS mode 0" "$OUT/base_s$s.log" || { echo "GATE FAIL base seed $s"; bad=1; }; done
for m in 1 2 3 4 5 6; do vvp -n "$OUT/sim" +mode=$m +jobs=$JOBS +seed=7 > "$OUT/fault_m$m.log"; grep -q "TB_VMSS PASS mode $m" "$OUT/fault_m$m.log" || { echo "GATE FAIL fault witness $m"; bad=1; }; done
for M in SLICE RANGE DLAT HASH; do
  iverilog -g2012 -DOT_VMSS_MUT_$M -o "$OUT/mut_$M" -s tb_dsfd_vm_seq_static $SRC || exit 2
  vvp -n "$OUT/mut_$M" +mode=0 +jobs=$JOBS +seed=1 > "$OUT/mut_$M.log"
  grep -q "TB_VMSS FAIL mode 0" "$OUT/mut_$M.log" || { echo "GATE FAIL mutant $M escaped"; bad=1; }
done
grep -h "RESULT" "$OUT"/*.log
[ $bad = 0 ] && echo "VMSS_GATE PASS" || { echo "VMSS_GATE FAIL"; exit 1; }
