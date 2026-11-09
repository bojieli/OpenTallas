#!/bin/bash
# DIE-HBM-97/KSHARE 11-09: proof material for recipes_b2.json orfs_vars OT_KEEP_WIRES=reset_pipe on
# ot_hbm_svc_vm_kshare_splitstrap__{v8e478a,v700685}.
#   run.sh KIT_RTL_PARENT_DIR    (a kit dir holding rtl/ with the five recipe files; heavy: run through ot-run)
# count_merge.tcl: synth -flatten -noabc of the core with KEEP=0 / KEEP=1 and the flops on reset_pipe wires.
#   KEEP=0 (vK as built): 4 flops are left of the 16 ot_reset_sync instances (32 flops): opt_merge folded every
#   hbm-side sync into one 2-flop pipe and every stream-side sync into another (count_keep0.txt).
#   KEEP=1 (keep_hook.tcl = the OT_KEEP_WIRES part of physical/common_flow/ot_keep_regs.tcl): all 32 remain (count_keep1.txt).
# eq_proof.tcl: RTL (gold: proc/flatten/memory, no opt_merge) vs the KEEP=1 synthesis (gate), async2sync, equiv_make by
#   name, equiv_induct, equiv_status -assert (eq_status.txt).  The kit flow also runs lec.py on the real ORFS netlist.
set -euo pipefail
K=$(cd "$1" && pwd -P); E=$(cd "$(dirname "$0")" && pwd -P)
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
for k in 0 1; do
  docker run --rm --memory 32g -e KEEP=$k -v "$K":/work:ro -v "$E":/eq openroad/orfs:asap7lock $Y -q -c /eq/count_merge.tcl
done
docker run --rm --memory 64g -v "$K":/work:ro -v "$E":/eq openroad/orfs:asap7lock $Y -c /eq/eq_proof.tcl > "$E/eq_proof.log" 2>&1
tail -n 3 "$E/eq_status.txt"
