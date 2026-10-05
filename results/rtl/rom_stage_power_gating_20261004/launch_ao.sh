#!/bin/bash
# ROM stage power gating (2026-10-04): route the ALWAYS-ON side alone (ot_v41_rom_pg_ao: scheduler + W18 controller,
# isolation clamps, 676-bit configuration retention shadow + replay, domain clock gate), so its leakage and its
# power-gated-idle activity power are measured on their own cells.  Same clock and corner as launch.sh.
# usage: WT=<pinned worktree> RUN=<name> launch_ao.sh
set -e
: "${WT:?pinned worktree}" "${RUN:?run name}"
J=/srv/opentallas-scratch/claude/rom-stage-pg/jobs/$RUN
mkdir -p $J
cd $WT
test -z "$(git status --porcelain)" || { echo "worktree not clean"; exit 2; }
exec python3 tools/run_abi3_physical_aligned.py --persistent-workdir $J/work --launch-receipt $J/receipt.json \
 --view asap7 --top ot_v41_rom_pg_ao --source rtl/v41rom/ot_v41_rom_pg_ao.sv --source rtl/v41rom/ot_v41_stage_pg_sched.sv \
 --source rtl/chip/ot_chip_v41_pg_ctrl.sv --source rtl/hdc/ot_hdc_cg.sv \
 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --io-delay-fraction 0.2 --stages pnr \
 --die-area 0 0 90 90 --core-area 2.16 2.16 87.84 87.84 --place-density 0.6 \
 --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns 0.0 --nickname-tag rom_stage_pg_${RUN}_20261004 \
 --output $J/out --hold-corners WC,BC --pnr-stop-after finish --orfs-corner WC --clock-uncertainty-hold-ns 0.025 \
 > $J/launch.log 2>&1
