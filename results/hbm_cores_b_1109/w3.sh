end=$(( $(date +%s) + 10800 ))
while [ $(date +%s) -lt $end ]; do
  if ssh -n -o ControlPath=none intel1 "test -s /srv/opentallas-scratch2/claude/qct13/lec_coll_core_v3/lec.json"; then echo COLL_CORE_V3_DONE; exit 0; fi
  O=$(ssh -n -o ControlPath=none intel2 "awk -F'\t' '\$1==\"qwen_compute\" && \$4 ~ /^7e478/ && \$7==\"route\" && \$8!=\"RUNNING\" {n++} \$1==\"qwen_compute\" && \$4 ~ /^7e478/ && \$7==\"place\" && \$8==\"FAIL\" && \$12>=\"2026-11-09 02:40\" && \$14 ~ /OT_CLAND/ {m++} END{print n+0, m+0}' ~/coord/autopilot/kit_wave_stages.tsv")
  set -- $O
  if [ "${1:-0}" -ge 1 ]; then echo ROUTE_RESULT $1; exit 0; fi
  if [ "${2:-0}" -ge 1 ]; then echo NEW_CLAND $2; exit 0; fi
  sleep 300
done
echo TIMEOUT_3H
