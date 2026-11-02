#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 prepare.py
mkdir -p run
for kind in ucie serdes; do
  iverilog -g2012 -s tb_pair -o "run/$kind.vvp" generated/private_models.sv "generated/tb_$kind.sv" > "run/${kind}_compile.log" 2>&1
  vvp "run/$kind.vvp" > "run/${kind}_positive.log" 2>&1
  set +e
  vvp "run/$kind.vvp" +MUT_PAYLOAD > "run/${kind}_payload_mutant.log" 2>&1
  rc=$?
  set -e
  test "$rc" -ne 0
  grep -q PEER_PAYLOAD_OR_LATENCY "run/${kind}_payload_mutant.log"
done
iverilog -g2012 -DSTALE_UCIE -s tb_pair -o run/ucie_stale.vvp generated/private_models.sv generated/tb_ucie.sv > run/ucie_stale_compile.log 2>&1
set +e
vvp run/ucie_stale.vvp > run/ucie_stale_mutant.log 2>&1
rc=$?
set -e
test "$rc" -ne 0
grep -q UNREGISTERED_TX_BETWEEN_EDGES run/ucie_stale_mutant.log
printf 'PRIVATE_PHY_PAIR_DIAGNOSTIC_PASS two positive three mutant runs; no hierarchy or physical credit\n'
