#!/bin/bash
# TOK-ALL-17 control: same probe bench with the ctl slice-select mutant (OT_S81HD_CTL_MUT_SLICE) -> must FAIL
O=/srv/opentallas-scratch2/claude/tok17-head/ctl/o; cd $O; V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --binary --timing --build-jobs 4 -O1 -Wno-fatal -DOT_S81HD_CTL_MUT_SLICE --top-module tb_tok17_ctl_lat -Mdir obj_mut *.sv *.v > build_mut.log 2>&1
obj_mut/Vtb_tok17_ctl_lat +B2B > run_mut_slice.log 2>&1
grep -h "PASS\|FAIL" run_mut_slice.log | head -3
