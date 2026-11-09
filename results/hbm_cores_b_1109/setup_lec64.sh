#!/bin/bash
set -euo pipefail
cd /
S=/srv/opentallas-scratch2/claude/codex-qc-su1-fill-reuse-1113
R=/srv/opentallas-scratch2/claude/qc-mem9-rtl/lec64
mkdir -p $R/out
cp -al $S/kit $R/kit
cp -p $S/driver.py $R/driver.py
for f in gold.aig gate.aig gold.map gate.map gold.keep gold.aliases.json; do cp -p $S/out/$f $R/out/$f; done
# hard links are read-only shared files: replace nothing, only add new files
cp $R/../rc_tmp/reset_contract.json $R/kit/reset_contract.json
mkdir -p $R/kit/reset_contract
cp $R/../rc_tmp/reset_contract/receipt.txt $R/kit/reset_contract/receipt.txt
