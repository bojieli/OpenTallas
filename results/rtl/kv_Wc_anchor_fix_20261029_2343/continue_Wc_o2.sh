#!/bin/bash
# Client on intel2; never edits or cancels the inherited Wc build.
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-kvtok-2249
C=/srv/opentallas-scratch2/claude/codex-kvtok-2249-client
O=$HOME/.local/bin/ot-run
exec >>$C/chain.log 2>&1
printf 'WAIT inherited Wc baseline %s\n' "$(date)"
while ! grep -q '^BUILD_DONE rc=0 ' "$HOME/tok-kv-7-wc.out"; do
 if grep -q '^BUILD_DONE rc=[1-9]' "$HOME/tok-kv-7-wc.out"; then echo 'STOP inherited build failed; no duplicate'; exit 1; fi
 sleep 30
done
printf 'START own corrected top %s\n' "$(date)"
$O --mem 120 --threads 24 --hosts intel1 --disk 60 --dir $D -- bash $D/build_Wc_o2.sh >$C/build.log 2>&1
rc=$?; echo "corrected_build rc=$rc $(date)"; [ $rc = 0 ] || exit $rc
$O --mem 24 --threads 2 --hosts intel1 --dir $D -- bash $D/build_gate_o2.sh >$C/relink.log 2>&1
rc=$?; echo "corrected_relink rc=$rc $(date)"; [ $rc = 0 ] || exit $rc
$O --mem 16 --threads 1 --hosts intel1 --dir $D -- bash $D/run_Wc_o2.sh $D/bWc_o2_gate/obj/Vtb_kvslice probe_Wc_o2 10000 >$C/probe.log 2>&1
rc=$?; echo "corrected_probe_runner rc=$rc $(date) (36-layer classifier on short probe)"
ssh intel1 "python3 $D/probe_gate.py" >$C/probe_gate.log 2>&1
rc=$?; cat $C/probe_gate.log; [ $rc = 0 ] || exit $rc
printf 'PAIR launch %s\n' "$(date)"
$O --mem 16 --threads 1 --hosts intel1 --dir $D -- bash $D/run_Wc_o2.sh $D/bWc_o2/obj/Vtb_kvslice nom_Wc_o2 300000 >$C/nominal.log 2>&1 & np=$!
$O --mem 16 --threads 1 --hosts intel1 --dir $D -- bash $D/run_Wc_o2.sh $D/bWc_o2/obj/Vtb_kvslice m3_Wc_o2 40000 phy_WS_0 >$C/mutant.log 2>&1 & mp=$!
wait $np; nr=$?; wait $mp; mr=$?
echo "PAIR done nominal=$nr mutant=$mr $(date)"
[ $nr = 0 ] && [ $mr = 0 ]
