#!/bin/bash
# DIE-KV-27: DIE-KV-26 proof.sh with MAIN trial_tap_arrivals.py (per-cell physical node paths = native6 stage path encoding)
set -u; T=e26a; O=/srv/opentallas-scratch2/claude/die-kv-27-1029; I=/srv/opentallas-scratch2/claude/die-kv-26-1029; cd $O
S=/srv/opentallas-scratch2/claude/wt/die-kv-27/tools/die_plan; L=/srv/opentallas-scratch2/claude/die-kv-2-1027/l128
P=$O/proof_m; PT=$O/proofT_m; PF=$O/proofF_m; mkdir -p $P
for C in TT FF; do python3 $S/trial_tap_arrivals.py $I/clk_$T/tree.json $I/out_${T}_$C/arr_$C.txt $C $P/tap_arrivals_$C.json || exit 1; done
cp $I/proof_$T/mesh.json $I/proof_$T/droop_regions.json $P/
python3 $S/tap_fall_merge.py $P TT $I/out_${T}_TT/duty_TT.txt --out $PT || exit 1
python3 $S/tap_fall_merge.py $PT FF $I/out_${T}_FF/duty_FF.txt --out $PF || exit 1
echo PROOF_DONE $(date)
