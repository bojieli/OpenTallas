#!/bin/bash
# REFILL-1725/QWLAYER: Qwen MU control-plane bench+mutant regression (Verilator 5.050) on today's changed sources,
# one cohort per source head (they conflict on qfd_sys_face*.sv / d2d_cal_image_mu.svh, so no combined merge):
#   ctlm4 = claude/qw-ctlm4-1019 d60ab0461 (CTLM safe4 + SRAM3 p192 lineage), sysface3 = claude/qw-sysface3-1019 83fc1f355,
#   gen3c = codex/qwen-gen3-takeover3-1019 864d10c8e (QW-GEN2 6bca9694c + GEN3 source).
# Legs = the REFILL-0730/1225 harness legs that read control-plane RTL changed today + kvctx + sys_face MU0/MU1 benches.
# Datapath (amix/slice/coll) legs are NOT rerun: tb_qfd_dv2 sources are byte-identical 0d4c9808f..864d10c8e.
set -u
R=/srv/opentallas-scratch/claude/refill-1725/QWLAYER; H=$R/head
L=/home/ubuntu/scratch/refill-1725/QWLAYER/legs; mkdir -p $L
VL='$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
for n in ${COHORTS:-ctlm4 sysface3 gen3c}; do
S=$R/$n/src; O=$R/$n/out
PFX="export PATH=\$HOME/.local/opentallas-tools/verilator-5.050/bin:\$PATH VERILATOR=$VL OT_VERILATOR=$VL; cd $S &&"
leg() { # name mem threads cmd
  local b=$1 g=${n}_$1 m=$2 t=$3; shift 3
  ( echo "# leg $g mem $m threads $t $(date -Is)"; echo "# cmd: $*"
    /home/ubuntu/bin/ot-run --mem $m --threads $t --dir $S --disk 10 -- bash -lc "$PFX mkdir -p $O && { $*; } > $O/$b.out 2>&1; rc=\$?; echo \"# exit \$rc\" >> $O/$b.out; exit \$rc"
    echo "# ot-run rc=$? $(date -Is)" ) > $L/$g.log 2>&1 &
  sleep 2
}
leg host 48 8 "bash rtl/test/mu_qwen_1018/run_all.sh $S $H $O/host/runs 8"
leg hroot 16 8 "bash rtl/test/mu_qwen_1018/run_all_hroot.sh $S $O/hroot/runs"
leg kv 32 8 "bash rtl/test/mu_qwen_1018/run_all_kv.sh $S $O/kv/runs"
leg kvctx 32 8 "bash rtl/test/mu_qwen_1018/run_mu_kvctx.sh $O/kvctx/w"
leg ctlm_mu 32 8 "bash rtl/test/mu_qwen_seq/run_mu_ctlm.sh $O/ctlm_mu/w mu"
leg ctlm_rest 32 8 "bash rtl/test/mu_qwen_seq/run_mu_ctlm.sh $O/ctlm_rest/w prog lp eq seq"
leg ctlm_nsl12 96 8 "bash rtl/test/mu_qwen_seq/run_mu_ctlm.sh $O/ctlm_nsl12/w ctlm"
leg opseg_pass 32 8 "bash rtl/test/mu_qwen_seq/run_mu_opseg.sh $O/opseg_pass/w pass"
leg opseg_mut 32 8 "bash rtl/test/mu_qwen_seq/run_mu_opseg.sh $O/opseg_mut/w mut emb"
leg tok 8 8 "bash rtl/test/mu_qwen_tok/run_mu_tok_smoke.sh $O/tok/w"
leg head 24 8 "OT_HEAD_BUILD=$O/head/build bash results/rtl/mu_qwen_1018/head/run_head.sh; rc=\$?; cp -r results/rtl/mu_qwen_1018/head/runs $O/head/runs; exit \$rc"
leg sl_DHUSER 8 8 "bash results/rtl/mu_qwen_1018/adopt_slice/run_group.sh DHUSER $O/slice_w/dh"
leg sysface_mu0 16 8 "bash rtl/test/qwen_split/run_sys_face_bench.sh $O/sysface_mu0 1 2 3 4 5"
leg sysface_mu1 16 8 "D2D_MU=1 bash rtl/test/qwen_split/run_sys_face_bench.sh $O/sysface_mu1 1 2 3 4 5 6 7"
done
wait
echo "ALL LEGS DONE $(date -Is)" > /home/ubuntu/scratch/refill-1725/QWLAYER/ALL_DONE
