#!/bin/bash
# DIE-KV-41 KV-022 SD try4: try3 kits with ring bands moved east of the PHY supply-region blockage (DPL-0033 fix), place -> CDC sdc -> cts + FF hold gate
F=/srv/opentallas-scratch2/claude/die-kv-41-1029/sdfix; CDC=/srv/opentallas-scratch2/claude/die-kv-39-1029/sdv2/kv38_cdc_fdi.sdc; cd $F
for T in kv3_sys_SD kv3_sys_SD_v1; do (
  bash kits/run_kit.sh kits/$T place 32 16; echo "SD41 $T PLACE_RC $? $(date)"
  S=$(ls kits/$T/run/results/asap7/*/base/3_place.sdc 2>/dev/null | head -1)
  if [ -n "$S" ]; then [ -f $S.orig ] || cp $S $S.orig; grep -q OT_CDC_FDI $S || cat $CDC >> $S
    bash kits/run_kit.sh kits/$T cts 32 16; echo "SD41 $T CTS_RC $? $(date)"; tail -3 kits/$T/hold_gate.log; fi ) & done; wait
echo "SD41 DONE $(date)"
