#!/usr/bin/env bash
# One DUT mutant of dsfd_vm_seq_static on the production-density base calendar (mode 0); must FAIL.
# Usage: tools/s81_vm/vm_seq_mutant_bench.sh OUTDIR MUT [JOBS]   prints VMSS_MUTANT FAIL <MUT> when the bench catches it
set -u
cd "$(dirname "$0")/../.."
OUT=${1:?outdir}; M=${2:?mutant}; JOBS=${3:-1500}; mkdir -p "$OUT"
R=rtl/dsrom_sys/s81_ph
iverilog -g2012 -DOT_VMSS_MUT_$M -o "$OUT/mut" -s tb_dsfd_vm_seq_static $R/vm/dsfd_vm_seq_static.sv $R/test/tb_dsfd_vm_seq_static.sv || exit 2
vvp -n "$OUT/mut" +mode=0 +jobs=$JOBS +seed=1 > "$OUT/mut.log"
grep -h RESULT "$OUT/mut.log"
if grep -q "TB_VMSS FAIL mode 0" "$OUT/mut.log"; then echo "VMSS_MUTANT FAIL $M"; exit 1; else echo "VMSS_MUTANT PASS $M (escaped)"; exit 0; fi
