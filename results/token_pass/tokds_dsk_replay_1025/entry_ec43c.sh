#!/bin/bash
# Native HOST entry proof on the deskew (ec43 XRT) cut_3S_ctl binary (Claude TOK-DS 10-25).
# c: hf_7N bit13 dropped = known NULL mutant (unused CSR padding; results/token_pass/codex_s81_entry_1024/README.md); bit33 is the canonical control.
# src31dsk = root30 with ot_s81sl_xrt.sv = ec43 (exactly the dsk_cuts kit RTL) + tools/ of codex-tok-ds-1025.
# 1) entry_boot.py STRICT (fresh ec43 receipt from tools/s81_dv/entry_vp_1025, no drift);
#    receipt pins cfc3; the drift is recorded and the replay below is the runtime proof);
# 2) 2000-cycle idle trace run of the dsk cut_3S_ctl binary; 3) run_entry_replay.py jobs + 2 corrupt mutants, KS probe.
set -u
S=/srv/opentallas-scratch2/claude/tok-ds; C=$S/dsk_cuts; CT=/srv/opentallas-scratch2/claude/wt/codex-tok-ds-1025
L=$S/stw-s81d-tok/layers; SRC=$L/src31dsk; O=$S/runs/claude_dsk; I=$O/idle_3S_ctl; P=$O/entry_jobs_ec43b; mkdir -p $O
if [ ! -e $SRC ]; then cp -al $L/root31dsk $SRC && rm -rf $SRC/tools && cp -a $CT/tools $SRC/tools; fi
sha256sum $SRC/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$SRC OT_SVC_ALLQ=1
cd $SRC
if [ ! -e $P ]; then
  python3 tools/s81_dv/layer_prog/entry_boot.py --tree $S/fc31/tree_fc31 --fixtures $L/fix/L0 \
    --mechanism-receipt /srv/opentallas-scratch2/claude/tok-ds/entry_vp_1025/entry_mechanism_ec43.json --out $P \
    --replay-job 15 --replay-job 16 --replay-job 17 --replay-job 20 --replay-job 21 --replay-job 22 \
    > $O/entry_boot_b.log 2>&1 || { echo "entry_boot FAIL"; tail -5 $O/entry_boot_b.log; exit 1; }
fi
[ -e $I/trace.txt ] || { cd $C && OBJ=$C/out_cut_3S_ctl/obj J=1 bash $SRC/tools/s81_dv/run_dv_slice.sh K_cut_3S_ctl $I +NCYC=2000 +TRACE=$I/trace.txt > $O/idle_3S_ctl.log 2>&1; echo "idle rc $? (zero-check FAIL expected)"; }
cd $SRC
python3 tools/s81_dv/tokfunc/run_entry_replay.py --src $SRC --die-v $S/fc31/tree_fc31/results/arch/s81_dv_1016/bind9/die.v.gz \
  --cut $C/cut_3S_ctl --kit $C/K_cut_3S_ctl --obj $C/out_cut_3S_ctl/obj --idle-run $I --progs $P \
  --fixture-meta $L/fix/L0/meta.json --ks-user 0 --out $O/entry_ec43c --jobs 15 16 17 20 21 22 \
  --mutant 15:corrupt:hf_7N_l0:33 --ks-probe --par 8 > $O/entry_ec43c.log 2>&1
echo "ENTRY rc $? $(grep ENTRY_REPLAY $O/entry_ec43c.log | tail -1)"
