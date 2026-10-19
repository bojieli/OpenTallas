#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
bench=results/kv_ahub_transport_component_1019
: "${VERILATOR:=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}"
if ! "$VERILATOR" --version | tee "$bench/tool_version.log" | grep -q 'Verilator 5.050'; then
  echo 'Required Verilator 5.050 is unavailable' >&2; exit 2
fi
logdir="$bench/logs_attempt2"
mkdir -p "$logdir"
for width in 268 68; do
  for mutant in 0 1 2 3 4 5; do
    if [[ $mutant == 4 && $width != 68 ]]; then continue; fi
    name=w${width}_m${mutant}
    "$VERILATOR" --binary --timing --top-module tb_transport --Mdir "$bench/obj_$name" \
      -j 2 -Wno-fatal --x-initial unique --x-assign unique \
      -GW="$width" -GMUT="$mutant" \
      rtl/lib/ot_rst_pipe.sv rtl/hdc/nearhbm/qkd_ahub_transport_private.sv \
      "$bench/tb_transport.sv" >"$logdir/${name}_build.log" 2>&1
    for seed in 1 7 31; do
      log="$logdir/${name}_seed${seed}.log"
      set +e
      "$bench/obj_$name/Vtb_transport" +verilator+rand+reset+2 +verilator+seed+"$seed" >"$log" 2>&1
      rc=$?
      set -e
      echo "$rc" >"$log.rc"
      if [[ $mutant == 0 ]]; then
        [[ $rc == 0 ]] && grep -q "TRANSPORT_PASS W=$width MUT=0" "$log"
        ! grep -q TRANSPORT_FAIL "$log"
      else
        [[ $rc != 0 ]] && grep -Eq "TRANSPORT_FAIL (payload|valid_frontier|accept_frontier)" "$log"
        ! grep -q TRANSPORT_PASS "$log"
      fi
    done
  done
done
echo 'TRANSPORT_SUITE_PASS: two actual widths, all applicable causal mutants, three arbitrary-init seeds'
