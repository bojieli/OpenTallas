#!/bin/bash
# Gated stage clock spine (2026-10-04): route the ALWAYS-ON side with the spine gate alone (ot_v41_rom_pg_ao_sp, SPINE = 1:
# scheduler + W18 controller, isolation clamps, retention shadow + replay, the spine enable flop and the spine ICG) at
# the signoff corners, as route A2 did for ot_v41_rom_pg_ao.  This block is the new logic and must close SS/FF.
# usage: WT=<pinned worktree> RUN=<name> launch_ao.sh
set -e
: "${WT:?pinned worktree}" "${RUN:?run name}"
J=/srv/opentallas-scratch/claude/spine-gate/jobs/$RUN
mkdir -p $J
cd $WT
test -z "$(git status --porcelain)" || { echo "worktree not clean"; exit 2; }
exec python3 tools/run_abi3_physical_aligned.py --persistent-workdir $J/work --launch-receipt $J/receipt.json \
 --view asap7 --top ot_v41_rom_pg_ao_sp --source rtl/v41rom/ot_v41_rom_pg_ao_sp.sv --source rtl/v41rom/ot_v41_stage_pg_sched.sv \
 --source rtl/chip/ot_chip_v41_pg_ctrl.sv --source rtl/hdc/ot_hdc_cg.sv --param SPINE=1 \
 --sdc-append results/rtl/rom_stage_spine_gate_20261004/spine_clocks.sdc \
 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --io-delay-fraction 0.2 --stages pnr \
 --die-area 0 0 90 90 --core-area 2.16 2.16 87.84 87.84 --place-density 0.6 \
 --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns 0.0 --nickname-tag spine_gate_${RUN}_20261004 \
 --output $J/out --hold-corners WC,BC --pnr-stop-after finish --orfs-corner WC --clock-uncertainty-hold-ns 0.025 \
 > $J/launch.log 2>&1
