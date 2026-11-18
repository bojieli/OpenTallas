#!/bin/bash
# ot-auto-retire-run [apply]  (runs ON the host; FLEET-OPS-R, FABLE-FLOW-2200): retire superseded die source trees through auto_retire.py:
# reference proof (kit_wave.json / state / markers from the hub), ot_delete_guard whole-tree delete, SIGNED units must be in the signed store.
# Dry run unless the first argument is "apply".  Stops at TARGET_GB free (default 350) and prints df before / after.
set -u
C=/srv/opentallas-scratch2/claude
RT=$C/rt/current/tools; HUB=ubuntu@185.8.106.226; HC=$C/hub-coord
G=$RT/fleet/ot_delete_guard.py; AR=$RT/fleet/auto_retire.py
L=$HOME/.local/state/ot-delete-guard/protected_struct.txt
D=$HOME/.local/state/ot-auto-retire; mkdir -p "$D"
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
CACHE=$D/inputs; mkdir -p "$CACHE"; CACHE_MAX_S=${AC_CACHE_MAX_S:-21600}
[ -f "$AR" ] && [ -f "$G" ] || { echo "auto_retire.py / guard missing in rt/current: nothing done" >&2; exit 3; }
SSH="ssh -o BatchMode=yes -o ConnectTimeout=15 -o ControlPath=none"
fetch_inputs() {
if [ "$(hostname -s)" = tolerant-swine ]; then
  cp $HC/autopilot/kit_wave.json $HC/autopilot/kit_wave_state.json "$W/" && cat $HC/lanes/handoff/tree_switch_*.json > "$W/markers.json" && cp $C/fleet-ops-r/protected_struct.txt "$L" && (cd $HC/signed-store/records && ls */ | grep json.gz | sed 's/.json.gz//' | sort -u) > "$W/ids.txt"
else
  scp -q -o BatchMode=yes -o ControlPath=none $HUB:$HC/autopilot/kit_wave.json $HUB:$HC/autopilot/kit_wave_state.json "$W/" || exit 3
  $SSH $HUB "cat $HC/lanes/handoff/tree_switch_*.json" > "$W/markers.json" || exit 3
  scp -q -o BatchMode=yes -o ControlPath=none $HUB:$C/fleet-ops-r/protected_struct.txt "$L" || exit 3
  $SSH $HUB "cd $HC/signed-store/records && ls */ | grep json.gz | sed 's/.json.gz//' | sort -u" > "$W/ids.txt" || exit 3
fi
if [ "${AC_FULL:-0}" = 1 ]; then
  YD=$(date -d yesterday +%F); TD=$(date +%F)
  if [ "$(hostname -s)" = tolerant-swine ]; then
    cat $HC/autopilot/auto_resign_state.json $HC/lanes/COUNT-DIRECT.tsv $HC/lanes/AUTO-RESIGN.tsv $HC/autopilot/auto_resign.tsv $HC/lanes/AUTO-RESIGN-HOLD.tsv > "$W/refs.txt" 2>/dev/null
    cat $HC/lanes/posts/*.md 2>/dev/null | grep -E "^- ($YD|$TD) " > "$W/posts.txt"
  else
    $SSH $HUB "cd $HC && cat autopilot/auto_resign_state.json lanes/COUNT-DIRECT.tsv lanes/AUTO-RESIGN.tsv autopilot/auto_resign.tsv lanes/AUTO-RESIGN-HOLD.tsv 2>/dev/null" > "$W/refs.txt"
    $SSH $HUB "cat $HC/lanes/posts/*.md 2>/dev/null | grep -E '^- ($YD|$TD) '" > "$W/posts.txt"
  fi
fi
}
if [ "${AC_NO_FETCH:-0}" != 1 ] && (set +e; fetch_inputs) ; then
  for f in kit_wave.json kit_wave_state.json markers.json ids.txt refs.txt posts.txt; do [ -f "$W/$f" ] && cp "$W/$f" "$CACHE/$f"; done; cp "$L" "$CACHE/protected_struct.txt" 2>/dev/null; date +%s > "$CACHE/t"
else
  age=$(( $(date +%s) - $(cat "$CACHE/t" 2>/dev/null || echo 0) ))
  [ "$age" -le "$CACHE_MAX_S" ] || { echo "hub inputs unreachable and cache is ${age}s old (> ${CACHE_MAX_S}s): nothing done" >&2; exit 3; }
  cp "$CACHE"/kit_wave.json "$CACHE"/kit_wave_state.json "$CACHE"/markers.json "$CACHE"/ids.txt "$W/" && cp "$CACHE/protected_struct.txt" "$L" && echo "hub unreachable: using the ${age}s old input cache"
  [ -f "$CACHE/refs.txt" ] && cp "$CACHE/refs.txt" "$W/refs.txt"; [ -f "$CACHE/posts.txt" ] && cp "$CACHE/posts.txt" "$W/posts.txt"
fi
if [ "${AC_FULL:-0}" = 1 ]; then      # FLEET-OPS-R 11-18 automatic cleanup: attempts + idle lanes (12 h); refs + 24 h posts come with the inputs (or the cache)
  [ -f "$W/refs.txt" ] && [ -f "$W/posts.txt" ] || { echo "refs/posts inputs missing: nothing done" >&2; exit 3; }
  EXTRA="--lanes --attempts --idle-h ${AC_IDLE_H:-12} --refs $W/refs.txt --posts $W/posts.txt"
else
  EXTRA="${AC_FLAGS:-}"
fi
[ -s "$W/ids.txt" ] || { echo "signed store id list empty: nothing done" >&2; exit 3; }
MODE=""; [ "${1:-}" = apply ] && MODE=--apply
FB=$(df -BG --output=avail $C | tail -n 1 | tr -dc 0-9)
echo "df before: ${FB}G"
OUT=$W/out.txt
python3 -I "$AR" --kit-wave "$W/kit_wave.json" --state "$W/kit_wave_state.json" --markers "$W/markers.json" --store-ids "$W/ids.txt" \
  --guard-module "$G" --list "$L" --log "$D/log.jsonl" --target "${TARGET_GB:-350}" $EXTRA $MODE | tee "$OUT"
rc=${PIPESTATUS[0]}
FA=$(df -BG --output=avail $C | tail -n 1 | tr -dc 0-9)
echo "df after: ${FA}G"
if [ "${AC_FULL:-0}" = 1 ] && [ "$MODE" = --apply ]; then
  AD=$HOME/.local/state/auto-clean; mkdir -p "$AD"
  now=$(date +%s)
  echo "$(date '+%F %T') $(hostname -s) rc=$rc deleted=$(grep -c '^DELETED' "$OUT") refused=$(grep -c '^REFUSED' "$OUT") failed=$(grep -c '^FAILED' "$OUT") before_gb=$FB free_gb=$FA" >> "$AD/host.log"
  echo "$now" > "$AD/last-pass"
fi
exit $rc
