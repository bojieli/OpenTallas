#!/bin/bash
# waits for the R5 synth+LEC unit (oth-ubuntu-697730-1793093921) to end, then launches chain_r5.sh through ot-run only if LEC is EQUIVALENT
D=/srv/opentallas-scratch2/claude/hbm-core-lat-r5-hcroot/hcp_sys1
while grep -q "admitted" $D/synth_r5.otrun.log && ! grep -q "RAN on\|NOT RUN" $D/synth_r5.otrun.log; do sleep 30; done
if grep -q "\"verdict\": *\"EQUIVALENT\"" $D/lec/lec.json; then
  echo "launch chain $(date -Is)" >> $D/chain_r5.status
  ~/.local/bin/ot-run --mem 40 --threads 8 --dir $D -- bash $D/chain_r5.sh > $D/chain_r5.otrun.log 2>&1
else echo "NOT launched: synth LEC $(grep -o "\"verdict\": *\"[A-Z ]*\"" $D/lec/lec.json) $(date -Is)" >> $D/chain_r5.status; fi
