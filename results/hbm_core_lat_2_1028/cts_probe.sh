#!/bin/bash
# HBM-CORE-LAT-2 CTS-only insertion probe (diagnostic; LEC/SELRANGE removed from the COPY; no route, no sign-off claim).
K=$(cd "$1" && pwd -P); MEM=${2:-32}; CPUS=${3:-16}
bash $K/run_kit_hbm.sh $K cts $MEM $CPUS; rc=$?
echo "CTS_PROBE run_kit rc $rc"
grep -h "OT_TAP_BALANCE\|OT_TAP_CHECK\|OT_HOLD_GATE" $K/run_cts.log | head -20
C=$(ls $K/run/results/asap7/*/base/4_cts.odb 2>/dev/null | head -1)
if [ -n "$C" ]; then C=/work/${C#$K/}
  docker run --rm --name hcl2pg-$(basename $K | cut -c1-40)-$$ --cpus=4 --memory=${MEM}g --memory-swap=${MEM}g -v $K:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for c in TT FF; do OT_CORNER=\$c ODB=$C openroad -exit /work/postcts_gate.tcl > /work/postcts_gate_\$c.log 2>&1; grep OT_POSTCTS_GATE /work/postcts_gate_\$c.log; done; chown -R $(id -u):$(id -g) /work"
fi
echo CTS_PROBE_DONE
