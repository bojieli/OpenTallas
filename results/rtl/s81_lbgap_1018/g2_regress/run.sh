#!/bin/bash
# G2 regression benches after the rstop sid decode change (fleet, Verilator 5.050)
R=/srv/opentallas-scratch/claude/s81lbgap_g2/src; O=/srv/opentallas-scratch/claude/s81lbgap_g2/out_reg
L=/home/ubuntu/scratch/s81-lbgap/g2/reg
j() { n=$1; m=$2; shift 2; ( /home/ubuntu/bin/ot-run --mem $m --threads 8 --dir $R -- bash -c "$*" > $L/$n.log 2>&1; echo "EXIT $?" >> $L/$n.log ) & }
j slice_eng_0 64 "J=8 bash tools/s81_slice/slice_eng_bench.sh $O/eng 0"
j slep_none_lepe 64 "J=8 bash tools/s81_slice/slice_lep_bench.sh $O/slep none lepe"
j slep_none_lepenh 64 "J=8 bash tools/s81_slice/slice_lep_bench.sh $O/slep none lepe_nh"
j slep_swap_lepe 64 "J=8 bash tools/s81_slice/slice_lep_bench.sh $O/slep swap lepe"
j xdie_min 48 "mkdir -p $O/xd && python3 tools/xdie_s81/gen_golden.py --out $O/xd/gm --reps 1 --only a_allgather,stage_hop --lat S=556,N=556 --per S=1.345,N=1.345 > $O/xd/genm.txt 2>&1 && J=6 bash tools/xdie_s81/run_xdie_s81.sh $O/xd min $O/xd/gm ep -GCHB=1 -GLOVR=1 -GCHB_OVR=700 -GCRED_OVR=512 -GSEQW_OVR=10 -GLSRAM=1 -GMAXCYC=40000"
wait; touch $L/DONE
