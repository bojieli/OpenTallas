#!/bin/bash
# QC-SMALLREG-1 post for RD (out_TT/out_FF/clk): per-region spread (x1.0485/x1.0552), proof with 12.15b spice-scaled clock,
# main die_sta_related --cppr-lca (+HB4), table OCV, shared droop per clock region.   usage: postS.sh RD MAP
set -u
RD=$1; R=$2; Q=/srv/opentallas-scratch2/claude/die-qc3-1027; D2=/srv/opentallas-scratch2/claude/die-qc2-1027
W=/srv/opentallas-scratch2/claude/wt/qc-smallreg-1027; PLAN=$W/physical/die_plan/qwen_compute/die_plan_sliceclk.json
log(){ echo "$* $(date)" >> $RD/post.log; }
cd $RD
for C in TT FF; do F=1.0485; [ $C = FF ] && F=1.0552; python3 -I $Q/pspread.py $RD out_$C/arr_$C.txt $R $F > spread_$C.txt; done
mkdir -p $RD/sc/out_TT $RD/sc/out_FF; ln -sfn $RD/clk $RD/sc/clk
for C in TT FF; do python3 -I $Q/scale_arr.py out_$C/arr_$C.txt sc/out_$C/arr_$C.txt $C; done
python3 -I $D2/mk_proof.py $RD/sc $R $RD/proof > $RD/proof.log 2>&1; log "proof rc $?"
for M in lca lcaHB4; do HB=none; [ $M = lcaHB4 ] && HB=HB4
  ~/.local/bin/ot-run --mem 32 --threads 4 --hosts localhost --dir $RD --priority die -- python3 -I $W/tools/die_plan/die_sta_related.py $RD/proof --plan $PLAN --out $RD/sta_$M --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $RD/proof/droop_regions.json --hold-buffers $HB --cppr-lca > $RD/sta_$M.log 2>&1; log "sta $M rc $?" &
done; wait
log POST_DONE
