#!/bin/bash
set -u
T=/srv/opentallas-scratch/claude/codex-qw-dieclk3-recover-1020
SRC=/srv/opentallas-scratch/claude/qw-dieclk3-1019/src
R=$T/chain_rN
export OT_FROM=grt OT_RELAY_SCHEDULE=/srv/opentallas-scratch/claude/qw-dieclk3-1019/sched/compute_compiled.json
export DC_GRID_CENTER=1 DC_SAFE_TREE=1 DC_REACH_DIAG=1 DC_NEIGHBOUR_TRIM=1
export OT_BIND_FWD_RLYH0=1 OT_DIE_CLOCK_PHYS=1 OT_DIE_CLOCK_MODE=regional OT_DIE_CLOCK_VARIANT=rN
export OT_RST_REP_VIEW=closed OT_DIE_REPAIR=1 OT_PDN_RELAY_GRIDS=1 OT_HOLD_BUDGET=die
export OT_SPLIT_PHY_NFACE=1 OT_SPLIT_PHY_TALL=1 OT_ASSUMED_PHY_PG_ACCESS=1 OT_STA_SUMMARY=1 OT_PG_OPEN_DIAG=1
export OT_ADMIT=pass OT_ITERS=12 OT_ROUTE_RESET=1 OT_CORNERS="tt ff ss" OT_STA_CLOCKS=$R/libs/clocks.tcl
export OT_GRT_CLOCK_LAYERS=M6-M9 OT_GRT_CLOCK_NDR=1
bash "$T/die_chain_reuse.sh" r22k "$R" "$SRC" > "$T/recovery.log" 2>&1
rc=$?; echo "$rc" > "$T/recovery.rc"; exit "$rc"
