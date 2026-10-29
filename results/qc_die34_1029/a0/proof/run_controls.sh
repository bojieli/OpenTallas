#!/bin/bash
# run mutant controls on an already built native_<tile>/obj (no set -e: a run without PASS/FAIL line is reported as such)
tile=$1; M=/srv/opentallas-scratch2/claude/die-qc34-a0/proof; P=/srv/opentallas-scratch2/claude/codex-qc-proof-0831; d=${2:-$M/native_$tile}
printf "mutant\tfunctional\tcontract\tline\n" > $d/controls.tsv
for m in 0 9 7 8 3 1 2 5 6; do
  $d/obj/Vtb_a0_icg +OT_ROM_DIR=$P/native_$tile/rom +ICG_MUT=$m > $d/run_mut$m.log 2>&1
  c=$(grep "^A0ICG_CONTRACT " $d/run_mut$m.log); q=$(grep -o "qualified_errors=[0-9]*" $d/run_mut$m.log | head -1)
  if [ -z "$q" ]; then fun="NOVERDICT"; elif [ "$q" = qualified_errors=0 ]; then fun=PASS; else fun="CAUGHT($q)"; fi
  echo "$c" | grep -q "lead_fail=0 drain_fail=0" && con=PASS || con=CAUGHT
  printf "%s\t%s\t%s\t%s\n" $m "$fun" "$con" "$c" >> $d/controls.tsv
done
cat $d/controls.tsv
