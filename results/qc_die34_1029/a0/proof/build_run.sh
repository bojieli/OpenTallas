#!/bin/bash
# DIE-QC-34: rebuild the Codex native A0 ICG2 vehicle (same pinned sources, files.txt) with the contract-monitor bench,
# then run the mutant controls.  Functional (qualified miter) and contract (lead/drain) verdicts are reported separately.
set -euo pipefail
tile=$1; M=/srv/opentallas-scratch2/claude/die-qc34-a0/proof; P=/srv/opentallas-scratch2/claude/codex-qc-proof-0831
d=$M/native_$tile; mkdir -p $d; cp $P/native_$tile/files.txt $d/
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
mapfile -t src < $d/files.txt
defs=(+define+TB_ICG=2 +define+TB_REGROOT=3 +define+OT_ROM_CONST0_KV +define+TB_CONTRACT)
[[ $tile == nl ]] && defs+=(+define+TB_NL)
verilator --version > $d/verilator.version
sha256sum $M/tb_a0_icg.sv "${src[@]}" > $d/sources.sha256
verilator --binary --timing -j 16 -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  "${defs[@]}" --top-module tb_a0_icg -Mdir $d/obj $M/tb_a0_icg.sv "${src[@]}" > $d/build.log 2>&1
printf "mutant\tfunctional\tcontract\tline\n" > $d/controls.tsv
for m in 0 9 7 8 3 1 2 5; do
  $d/obj/Vtb_a0_icg +OT_ROM_DIR=$P/native_$tile/rom +ICG_MUT=$m > $d/run_mut$m.log 2>&1 || true
  c=$(grep "^A0ICG_CONTRACT " $d/run_mut$m.log || echo none)
  q=$(grep -o "qualified_errors=[0-9]*" $d/run_mut$m.log | head -1)
  fun=$([[ $q == qualified_errors=0 ]] && echo PASS || echo "CAUGHT($q)")
  con=$(echo "$c" | grep -q "lead_fail=0 drain_fail=0" && echo PASS || echo CAUGHT)
  printf "%s\t%s\t%s\t%s\n" $m "$fun" "$con" "$c" >> $d/controls.tsv
done
cat $d/controls.tsv
