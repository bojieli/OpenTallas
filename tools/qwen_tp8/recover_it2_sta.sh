#!/bin/bash
# Preserve failed evidence; rerun only the six completed STA jobs missing clock sources.
set -eu
R=${1:-/srv/opentallas-scratch/claude/qwen-tp8-die/it2}
K=${2:-/srv/opentallas-scratch/claude/qwen-tp8-die/kit_it2}
F="$R/sta_clockfix_codex"
mkdir -p "$F"
for kind in pad cap140 cap244; do for corner in tt ff; do
  B="$R/sta_r22k_$corner"; S="${B}_$kind"; D="$F/${corner}_$kind"
  if [ -f "$D/run.start" ]; then echo "REFUSE duplicate $D"; exit 1; fi
  mkdir -p "$D/libs"
  ln -f "$S"/libs/* "$D/libs/"
  ln -f "$S/ckpt_grt.odb" "$S/die_grt.spef" "$D/"
  if [ -f "$S/route.guide" ]; then ln -f "$S/route.guide" "$D/"; fi
  cp "$S/grt_$corner.tcl" "$D/"
  cp "$B"/clock_*.tcl "$D/"
  # Preserve the pad run's modified clock arrivals, where present.
  for f in "$S"/clock_*.tcl; do [ ! -f "$f" ] || cp "$f" "$D/"; done
  for component in regions lat ocv; do test -s "$D/clock_${component}_$corner.tcl"; done
  date -Is >> "$F/STATUS.log"
  echo "START $corner $kind" >> "$F/STATUS.log"
  ot-heavy --mem 50 -- "$K/tools/qwen_kv_die/chain/dietop_run.sh" "$D" "grt_$corner.tcl" 8 50
  rc=$(cat "$D/run.exit")
  echo "END $corner $kind rc=$rc" >> "$F/STATUS.log"
  [ "$rc" = 0 ] || exit "$rc"
  grep -E '^(wns|tns|worst slack)' "$D/grt_$corner.log" >> "$F/STATUS.log"
done; done
echo ALL_DONE >> "$F/STATUS.log"
