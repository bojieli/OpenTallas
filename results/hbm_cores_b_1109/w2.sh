G=/srv/opentallas-scratch3/claude/kw26-wave-1106/runs/qwen_compute/kit-wave/qwen_compute/efdb36e864/items/glue/attempt_8/gen/glue/lec/lec.json
B=$(ssh -n -o ControlPath=none epyc2 "stat -c %Y $G")
end=$(( $(date +%s) + 10800 ))
while [ $(date +%s) -lt $end ]; do
  if ssh -n -o ControlPath=none intel1 "test -s /srv/opentallas-scratch2/claude/qct13/lec_coll_core_v3/lec.json"; then echo COLL_CORE_V3_DONE; exit 0; fi
  N=$(ssh -n -o ControlPath=none epyc2 "stat -c %Y $G"); if [ -n "$N" ] && [ "$N" != "$B" ]; then echo GLUE_LEC_CHANGED; exit 0; fi
  R=$(ssh -n -o ControlPath=none intel2 "awk -F'\t' '\$1==\"qwen_compute\" && \$4 ~ /^7e478/ && \$7 ~ /^(geom|signoff)/' ~/coord/autopilot/kit_wave_stages.tsv | wc -l")
  if [ "${R:-0}" -ge 3 ]; then echo ROWS_AT_GEOM $R; exit 0; fi
  sleep 300
done
echo TIMEOUT_3H
