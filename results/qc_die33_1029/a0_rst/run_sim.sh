#!/bin/bash
set -uo pipefail
cd /srv/opentallas-scratch2/claude/wt/die-qc33-a0rst
D=tools/qwen_romleaf/a0core/icg; V=$HOME/.local/opentallas-tools/bin/verilator; O=/srv/opentallas-scratch2/claude/die-qc33-a0/rrst_sim; mkdir -p $O
python3 -I /srv/opentallas-scratch2/claude/die-qc33-a0/rr/mkstub.py
cp /srv/opentallas-scratch2/claude/die-qc33-a0/rr/tb_a0_rrst.sv $D/
timeout 900 $V --binary --timing -j 4 -O1 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_a0_rrst -Mdir $O/obj $D/tb_a0_rrst.sv rtl/physical/a0_core/qfd_tile_nk_a0c.sv $D/rrst_body_stub_nk.sv rtl/physical/a0_core/ot_a0_icg_hop.sv rtl/lib/ot_rst_relay.sv > $O/build.log 2>&1; echo build rc=$?; grep -i "%Error" $O/build.log | head
for m in 0 10 11; do $O/obj/Vtb_a0_rrst +ICG_MUT=$m | grep A0RRST; done | tee $O/results.txt
