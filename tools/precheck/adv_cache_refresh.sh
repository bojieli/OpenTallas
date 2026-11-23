#!/bin/bash
# adv_cache_refresh.sh -- PRECHECK-R2: refresh the plan_advisory caches (DENSITY synth cells, TAP-LOAD kit-scan flops) and copy them
# to every gen host's /srv/opentallas-scratch2/claude/precheck-cache/.  Runs on the hub (intel2), read-only on the sources; minutes.
#   bash tools/precheck/adv_cache_refresh.sh [RT]     (hourly user cron on intel2)
set -u
RT=${1:-/srv/opentallas-scratch2/claude/rt/current}
P=$RT/tools/precheck
C=/srv/opentallas-scratch2/claude/precheck-cache
HOSTS=${OT_ADV_CACHE_HOSTS:-"intel1 epyc2 epyc7 epyc8 epyc9 epyc10"}
T=$C/tmp; mkdir -p "$T"
# never replace a cache by a smaller one (a harvest that found fewer records is a source problem, not news)
keep() {  # keep NEW OLD SECTION
  python3 -I -c 'import json,sys
n,o,k=sys.argv[1:4]
try: old=len(json.load(open(o)).get(k) or {})
except Exception: old=0
new=len(json.load(open(n)).get(k) or {})
print(f"{o}: {k} {old} -> {new}"); sys.exit(0 if new >= 0.9 * old and new > 0 else 1)' "$@"
}
python3 -I "$P/adv_harvest_cells.py" "$T/cells_cache.json.new" >/dev/null && keep "$T/cells_cache.json.new" "$C/cells_cache.json" cells \
  && mv "$T/cells_cache.json.new" "$C/cells_cache.json"
parts=()
[ -d ~/.local/state/precheck-kit-scan ] && python3 -I "$P/adv_harvest_flops.py" "$T/flops_intel2.json" >/dev/null && parts+=("$T/flops_intel2.json")
for h in $HOSTS; do
  timeout 120 scp -q -o ControlPath=none "$P/adv_harvest_flops.py" "$h:/tmp/precheck_r2_harvest_flops.py" &&
  timeout 300 ssh -n -o ControlPath=none "$h" "cd / && python3 -I /tmp/precheck_r2_harvest_flops.py /tmp/precheck_r2_flops_$h.json >/dev/null" \
    && timeout 300 scp -q -o ControlPath=none "$h:/tmp/precheck_r2_flops_$h.json" "$T/flops_$h.json" && parts+=("$T/flops_$h.json")
done
if [ ${#parts[@]} -gt 0 ]; then
  python3 -I "$P/adv_merge_flops.py" "$T/flops_cache.json.new" "${parts[@]}" && keep "$T/flops_cache.json.new" "$C/flops_cache.json" flops \
    && mv "$T/flops_cache.json.new" "$C/flops_cache.json"
fi
for h in $HOSTS; do
  timeout 300 ssh -n -o ControlPath=none "$h" "mkdir -p $C" && \
  timeout 300 scp -q -o ControlPath=none "$C/cells_cache.json" "$C/flops_cache.json" "$h:$C/" || echo "copy to $h failed"
done
echo "ADV-CACHE refreshed $(date '+%F %T') parts=${#parts[@]}"
