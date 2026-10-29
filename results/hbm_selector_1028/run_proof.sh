#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-selector-1028
mkdir -p proof
docker run --rm --name codex-selector-compaction-proof --cpus=2 --memory=16g --memory-swap=16g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
for pair in 0:0 1:1 1:0; do
 m=${pair%:*}; r=${pair#*:}
 set +e
 yosys -Q -T -p "read_verilog -sv proofsrc/ot_hbm_idx_compact_tree.sv proofsrc/ot_hbm_idx_selector_compact.sv proofsrc/proof.sv; chparam -set MUTANT $m -set REF_MUT $r proof; hierarchy -check -top proof; proc; flatten; opt; sat -verify -prove bad 0 -show-inputs" > proof/m${m}r${r}.log 2>&1
 rc=$?
 set -e
 if [ "$m" = "$r" ]; then test "$rc" = 0; else test "$rc" != 0; grep -q "proof did fail" proof/m${m}r${r}.log; fi
done
yosys -Q -T -p "read_verilog -sv proofsrc/hist_proof.sv; hierarchy -check -top hist_proof; proc; flatten; opt; sat -verify -prove bad 0 -show-inputs" > proof/hist.log 2>&1
echo SELECTOR_COMPACTION_PROOF_PASS
'
