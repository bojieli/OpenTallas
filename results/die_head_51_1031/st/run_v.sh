#!/bin/bash
# DIE-HEAD-51 helper st: one l48w-st variant end to end.  usage: run_v.sh V BIND PINBUF_HOP
V=$1; BIND=$2; PH=$3
S=/srv/opentallas-scratch2/claude/die-head-48/clk_st51; cd $S; TL=/srv/opentallas-scratch2/claude/wt/dh51-st/tools/die_plan
exec > run_$V.log 2>&1
rm -rf kit_l48w_st$V patch_$V out_${V}_TT out_${V}_FF ck_$V base_$V proof_l48w_st$V o_l48w_st$V
cp -a ../clk/kit_l48c kit_l48w_st$V; rm -f kit_l48w_st$V/kit/clock/arr_*.txt kit_l48w_st$V/kit/clock/ctree_*.log
PINBUF_HOP=$PH CHAIN_UM=${4:-0} python3 st_ctree.py $BIND ../head_source_l48w/start_stages_src25q.json kit_l48w_st$V/kit/clock/tree.json kit_l48w_st$V/kit/clock $TL patch_$V BUFx8_ASAP7_75t_R || exit 1
cp patch_$V/ctree.v patch_$V/ctree.tcl kit_l48w_st$V/kit/clock/
python3 $TL/die_trial.py readout patch_$V/ctree.v --path "/out/edges_\$::env(CORNER).txt" --period 833.333 --cells "ck_*" --prefix ck_ > readout_$V.tcl || exit 1
sed -e "s#K=\$S/kit_l48w_st/kit#K=\$S/kit_l48w_st$V/kit#" -e "s#CK=\$S/ck;#CK=\$S/ck_$V;#" -e "s#O=\$S/out_\$C;#O=\$S/out_${V}_\$C;#" -e "s#\$S/readout.tcl#\$S/readout_$V.tcl#" -e "s#dh51st-clkst-\$C#dh51st-clkst$V-\$C#" -e 's#--memory=64g --memory-swap=64g#--memory=8g --memory-swap=8g#' clk_st.sh > clk_st$V.sh
grep -c "st$V\|_$V" clk_st$V.sh
mkdir -p out_${V}_TT out_${V}_FF
~/.local/bin/ot-run --mem 4 --dir $S/kit_l48w_st$V -- bash $S/clk_st$V.sh clock > clock_$V.otrun.log 2>&1 &
for c in TT FF; do ~/.local/bin/ot-run --mem 8 --dir $S/out_${V}_$c -- bash $S/clk_st$V.sh $c > grt_${V}_$c.otrun.log 2>&1 & done
wait
grep -h "EXIT\|VIOLATED\|Maximum resident" out_${V}_*/combo_*.log; grep -h -A12 "Final congestion" out_${V}_TT/combo_TT.log | tail -1; tail -n1 clock_$V.otrun.log
mkdir -p base_$V; cp ../sta/proof_l48c/mesh.json base_$V/
for c in TT FF; do python3 - $c <<PY
import sys
c=sys.argv[1]; O="out_${V}_"+c
E=open(f"{O}/edges_{c}.txt").read().splitlines(); A=open(f"{O}/arr_{c}.txt").read().splitlines()
at=[l for l in A if l.startswith("T ")]
open(f"{O}/both_{c}.txt","w").write("\n".join([E[0]]+at+[l for l in E[1:] if l[:2] in ("F ","N ","M ")])+"\n")
PY
python3 $TL/trial_tap_arrivals.py kit_l48w_st$V/kit/clock/tree.json out_${V}_$c/both_$c.txt $c base_$V/tap_arrivals_$c.json | tail -1; done
python3 $TL/start_stage_emit.py proof base_$V --stages patch_$V/start_stages_l48w_st.json --arr TT=out_${V}_TT/both_TT.txt --arr FF=out_${V}_FF/both_FF.txt --out proof_l48w_st$V 2>&1 | tail -2
python3 cmp_v.py proof_l48w_st$V
python3 fails.py proof_l48w_st$V $BIND patch_$V | tail -40
D=/srv/opentallas-scratch2/claude/die-head-48
~/.local/bin/ot-run --mem 8 --dir $S -- bash $D/sta/run_single.sh $S/proof_l48w_st$V $S/o_l48w_st$V $D/head_source_l48w/source_plan.json $BIND > otrun_sta_$V.log 2>&1
grep "COUNT-ALIGN .. crossings" o_l48w_st$V.log | sed "s/ ocv.*//" | cut -c1-230
grep -E "^proof.* (TT|FF) (intra|seam) " o_l48w_st$V.log | cut -c1-200
python3 -c "
import json;d=json.load(open('o_l48w_st$V/die_sta_related.json'));g=d['summary'].get('die_clock_gate')
print({k:g.get(k) for k in ('verdict','tt_setup_ps','contract_violations','reasons')})"
echo RUN_V_DONE
