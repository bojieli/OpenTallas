#!/bin/bash
# STW-S81d-TOK: native entry HOST jobs on the cap30-framecal cut_3S_ctl (die.v 3b4b975d); consumes the built binary + idle trace.
P=/srv/opentallas-scratch/claude/stw-s81d-tok/layers; C=/srv/opentallas-scratch/claude/stw-s81d-tok/fc30/cuts; O=$P/entry_fc30
[ -x $C/out_cut_3S_ctl/obj/sim ] && [ -f $C/out_cut_3S_ctl/trace.txt ] || { echo "ENTRY fc30 NOT RUN: missing binary/trace on $(hostname)"; exit 3; }
rm -rf $O
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
cd $P/root30 && OT_S81_SELECTED_SOURCE_ROOT=$P/root30 python3 tools/s81_dv/tokfunc/run_entry_replay.py --src $P/root30 \
  --die-v $P/tree_fc30/results/arch/s81_dv_1016/bind9/die.v.gz --cut $C/cut_3S_ctl --kit $C/K_cut_3S_ctl \
  --obj $C/out_cut_3S_ctl/obj --idle-run $C/out_cut_3S_ctl --progs $P/entry_jobs_fc30 --fixture-meta $P/fix/L0/meta.json \
  --ks-user 0 --out $O --jobs 15 16 17 20 21 22 --mutant 15:corrupt:hf_7N_l0:13 > $P/entry_fc30.log 2>&1
echo "ENTRY fc30 rc $? $(grep ENTRY_REPLAY $P/entry_fc30.log | tail -1)"
