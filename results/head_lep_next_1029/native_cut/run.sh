#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-head-lep-next/native_cut
S=/srv/opentallas-scratch2/claude/codex-head-lep-next/lockstep
cd "$R"
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
verilator --binary -j 8 --timing -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINCONNECTEMPTY -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF --top-module tb_native_cut *.sv "$S/ot_s81ph_link_ep_safe4.sv" "$S/ot_link_crc32.sv" "$S/ot_sram_oldread_b64.sv" "$S/ot_sram_showahead_b64.sv" "$S/ot_link_credit_rx_b64.sv" "$S/ot_link_credit_tx_rc.sv" "$S/ot_sram_1r1w2c_256x64_m1.v" "$S/ot_sram_1r1w2c_32x64_m1.v" --Mdir obj > build.log 2>&1
./obj/Vtb_native_cut > sim.log 2>&1
grep "NATIVE_CUT PASS" sim.log
if ./obj/Vtb_native_cut +mutant > mutant.log 2>&1; then exit 1; fi
grep "MUTANT CAUGHT" mutant.log
