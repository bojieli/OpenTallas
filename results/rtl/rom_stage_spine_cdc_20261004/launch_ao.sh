#!/bin/bash
# Gated stage clock spine with synchronised crossings (2026-10-04): route the ALWAYS-ON block of a K-element stage alone
# (ot_v41_rom_stage_pg_ao_cdc: shared scheduler + W18 controller + spine gate, K element AO parts) at the signoff
# corners; it is the new logic and must close SS/FF.  Its leakage is the always-on leakage of the power rows.
# usage: WT=<pinned worktree> RUN=<name> K=<1|4> launch_ao.sh
set -e
: "${WT:?pinned worktree}" "${RUN:?run name}" "${K:?elements}"
J=/srv/opentallas-scratch/claude/spine-cdc/jobs/$RUN
mkdir -p $J
cd $WT
test -z "$(git status --porcelain)" || { echo "worktree not clean"; exit 2; }
S=$(python3 -c "print(90 if $K == 1 else 180)"); C=$(python3 -c "print($S-2.16)")
exec python3 tools/run_abi3_physical_aligned.py --persistent-workdir $J/work --launch-receipt $J/receipt.json \
 --view asap7 --top ot_v41_rom_stage_pg_ao_cdc --source rtl/v41rom/ot_v41_rom_stage_pg_cdc.sv --source rtl/v41rom/ot_v41_stage_pg_sched.sv \
 --source rtl/chip/ot_chip_v41_pg_ctrl.sv --source rtl/hdc/ot_hdc_cg.sv --param K=$K \
 --sdc-append results/rtl/rom_stage_spine_cdc_20261004/cdc_clocks.sdc \
 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --io-delay-fraction 0.2 --stages pnr \
 --die-area 0 0 $S $S --core-area 2.16 2.16 $C $C --place-density 0.6 \
 --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns 0.0 --nickname-tag spine_cdc_${RUN}_20261004 \
 --output $J/out --hold-corners WC,BC --pnr-stop-after finish --orfs-corner WC --clock-uncertainty-hold-ns 0.025 \
 > $J/launch.log 2>&1
