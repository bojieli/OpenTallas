#!/bin/bash
# REFILL-0730/MUQWREG: full MU bench + mutant regression on claude/mu-qwen-all-1019 0e6795834 (Verilator 5.050).
# Legs run via ot-run on the two staged hosts (ot-agidock128, ot-pve1); src = $D/src (git archive of 0e6795834 subset).
set -u
D=/srv/opentallas-scratch/claude/refill-0730/MUQWREG; S=$D/src; O=$D/out
L=/home/ubuntu/scratch/refill-0730/MUQWREG/legs; mkdir -p $L
VL='$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
PFX="export PATH=\$HOME/.local/opentallas-tools/verilator-5.050/bin:\$PATH VERILATOR=$VL OT_VERILATOR=$VL; cd $S &&"
leg() { # name mem threads cmd
  local n=$1 m=$2 t=$3; shift 3
  ( echo "# leg $n mem $m threads $t $(date -Is)"; echo "# cmd: $*"
    /home/ubuntu/bin/ot-run --mem $m --threads $t --dir $S --disk 10 -- bash -lc "$PFX mkdir -p $O/$n && { $*; } > $O/$n.out 2>&1; rc=\$?; echo \"# exit \$rc\" >> $O/$n.out; exit \$rc"
    echo "# ot-run rc=$? $(date -Is)" ) > $L/$n.log 2>&1 &
  sleep 2
}
# HOST: MU 1 benches + mutants + MU 0 identity (ex_new vs pre-MU head tree)
leg host 48 8 "bash rtl/test/mu_qwen_1018/run_all.sh $S $D/head $O/host/runs 8"
leg hroot 16 8 "bash rtl/test/mu_qwen_1018/run_all_hroot.sh $S $O/hroot/runs"
leg kv 32 8 "bash rtl/test/mu_qwen_1018/run_all_kv.sh $S $O/kv/runs"
leg ctlm_mu 32 8 "bash rtl/test/mu_qwen_seq/run_mu_ctlm.sh $O/ctlm_mu/w mu"
leg ctlm_rest 32 8 "bash rtl/test/mu_qwen_seq/run_mu_ctlm.sh $O/ctlm_rest/w prog lp eq seq"
leg ctlm_nsl12 96 8 "bash rtl/test/mu_qwen_seq/run_mu_ctlm.sh $O/ctlm_nsl12/w ctlm"
leg opseg_pass 32 8 "bash rtl/test/mu_qwen_seq/run_mu_opseg.sh $O/opseg_pass/w pass"
leg opseg_mut 32 8 "bash rtl/test/mu_qwen_seq/run_mu_opseg.sh $O/opseg_mut/w mut emb"
leg tok 8 8 "bash rtl/test/mu_qwen_tok/run_mu_tok_smoke.sh $O/tok/w"
leg head 24 8 "OT_HEAD_BUILD=$O/head/build bash results/rtl/mu_qwen_1018/head/run_head.sh; rc=\$?; cp -r results/rtl/mu_qwen_1018/head/runs $O/head/runs; exit \$rc"
for c in mu_bi mu_bi_neg_overlap mu_bi_mut_rlat mu_bi_mut_rank; do
  leg coll_$c 32 8 "a=\$(python3 tools/xdie_qtp8/cases.py args $c) && python3 tools/qwen_coll_tp8_static_links_bench.py --out $O/coll/$c \$a; rc=\$?; rm -rf $O/coll/$c/obj_*; exit \$rc"
done
# AMIX groups (superset of slice positives at MU_NU 1/4, bench m/n, NEG am7, bench h, FACES)
for g in F0 F1 F2 G0 G1 G2 N0 N1 N2 FACES1 FACES4; do
  leg amix_$g 16 8 "bash results/rtl/mu_qwen_1018/amix/run_group.sh $g $O/amix_w/$g"
done
for g in H1 H4; do leg amix_$g 96 8 "bash results/rtl/mu_qwen_1018/amix/run_group.sh $g $O/amix_w/$g"; done
# adopt_slice negatives (one build per job), gap sweep, FACES mutants, dhuser leaf
A="bash results/rtl/mu_qwen_1018/adopt_slice/run_group.sh ONE $O/slice_w"
leg sl_NEG_m_nu1_w 16 8 "$A NEG_m_nu1_w DV2_FACE=1 DV2_MU_NU=1 -- m --work $O/slice_w/NEG_nu1"
for m in 1 2 3 4; do leg sl_NEG_m_am$m 16 8 "$A NEG_m_am$m DV2_FACE=1 DV2_MU_NU=4 DV2_AM_MUT=$m -- m --work $O/slice_w/NEG_am$m"; done
leg sl_NEG_m_am2_e 16 8 "$A NEG_m_am2_e DV2_FACE=2 DV2_MU_NU=4 DV2_AM_MUT=2 -- m --work $O/slice_w/NEG_am2e"
leg sl_NEG_i_mut11_nu4 16 8 "$A NEG_i_mut11_nu4 DV2_FACE=1 DV2_MU_NU=4 -- i --mut 11 --work $O/slice_w/NEG_s11"
leg sl_NEG_j_mut12_nu4 16 8 "$A NEG_j_mut12_nu4 DV2_FACE=1 DV2_MU_NU=4 -- j --mut 12 --work $O/slice_w/NEG_s12"
leg sl_NEG_m_am6_rootnoclr 16 8 "$A NEG_m_am6_rootnoclr DV2_FACE=1 DV2_MU_NU=4 DV2_AM_MUT=6 -- m --work $O/slice_w/NEG_am6"
leg sl_NEG_m_gap12_stnpend 16 8 "$A NEG_m_gap12_stnpend DV2_FACE=0 DV2_MU_NU=4 DV2_GAP=12 -- m --work $O/slice_w/NEG_g12"
for g in 16 20 24 30; do leg sl_F0_nu4_m_gap$g 16 8 "DV2_GAP=$g $A F0_nu4_m_gap$g DV2_FACE=0 DV2_MU_NU=4 DV2_GAP=$g -- m --work $O/slice_w/gap$g"; done
for m in 11 12; do leg sl_FACES_mut${m}_nu4 16 8 "bash results/rtl/mu_qwen_1018/adopt_slice/run_group.sh FONE $O/slice_w $m 4"; done
leg sl_DHUSER 8 8 "bash results/rtl/mu_qwen_1018/adopt_slice/run_group.sh DHUSER $O/slice_w/dh"
wait
echo "ALL LEGS DONE $(date -Is)" > /home/ubuntu/scratch/refill-0730/MUQWREG/ALL_DONE
