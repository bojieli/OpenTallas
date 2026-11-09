#!/bin/bash
cd /
for i in $(seq 1 400); do
  r=$(ssh -n -o ControlPath=none -o ConnectTimeout=20 intel2 'a=""; grep -q "^exit " ~/dh88/lep_fm.log && a="$a LEP_DONE"; test -f /srv/opentallas-scratch2/claude/head-forms-5/spn_end_eco1/finish_b.json && a="$a SPN_END_LEC"; grep -q "ot-run: RAN" ~/dh89/tile_eco.otrun.log && a="$a TILE_ECO_DONE"; echo $a' 2>/dev/null)
  if [ -n "$r" ]; then echo "WATCH: $r $(date)"; exit 0; fi
  sleep 60
done
echo "WATCH timeout $(date)"
