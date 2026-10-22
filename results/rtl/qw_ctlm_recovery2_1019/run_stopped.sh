#!/bin/bash
set -u
cd /srv/opentallas-scratch/claude/qw-ctlm-recovery2-1019
verilator --binary --top-module tb_ring_phase -Wno-fatal -j 2 tb_stopped_reset.sv src/rtl/common/landed_parent/ot_pl_land.sv -Mdir stopped_obj > stopped_build.log 2>&1 || exit 1
./stopped_obj/Vtb_ring_phase > stopped_reset.log 2>&1
