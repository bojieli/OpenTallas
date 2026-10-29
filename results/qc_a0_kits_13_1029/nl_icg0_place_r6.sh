#!/bin/bash
# QC-A0-KITS-13: ONE rerun of NL ICG0 typed placement with the reset6 settings (COORD 10-29 ruling b).
# reset6 = intel1 codex-qc-a0-2340/run_parent_reset_place.sh: --cpus=8, NUM_CORES=8, identical config.mk GPL args
# (density 0.45, -routability_driven -timing_driven, divergence revert ON = default, no -disable_revert_if_diverge).
# fail1 (Codex unit oth-ubuntu-582810-1793274530, stopped 06:40 by COORD ruling) used --cpus=16 NUM_CORES=16;
# its log: ../nl_icg0_3_3_fail1_diverge_16t.log. Kit = copy of codex-qc-a0-0251/candidate_kits/qfd_tile_nl_a0c_a0nl12icg0typed, restarting at 3_3.
set -euo pipefail
K=/srv/opentallas-scratch2/claude/qc-a0-kits-13-1029/nl_icg0_r6
docker run --rm --name qca0k13-nl-icg0-place-r6 --cpus=8 --memory=12g --memory-swap=12g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place; rc=\$?; chown -R 1000:1000 /work; exit \$rc" > "$K/place_r6.log" 2>&1
