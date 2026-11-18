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
[ -f "$AR" ] && [ -f "$G" ] || { echo "auto_retire.py / guard missing in rt/current: nothing done" >&2; exit 3; }
SSH="ssh -o BatchMode=yes -o ConnectTimeout=15 -o ControlPath=none"
if [ "$(hostname -s)" = tolerant-swine ]; then
  cp $HC/autopilot/kit_wave.json $HC/autopilot/kit_wave_state.json "$W/" && cat $HC/lanes/handoff/tree_switch_*.json > "$W/markers.json" && cp $C/fleet-ops-r/protected_struct.txt "$L" && (cd $HC/signed-store/records && ls */ | grep json.gz | sed 's/.json.gz//' | sort -u) > "$W/ids.txt"
else
  scp -q -o BatchMode=yes -o ControlPath=none $HUB:$HC/autopilot/kit_wave.json $HUB:$HC/autopilot/kit_wave_state.json "$W/" || exit 3
  $SSH $HUB "cat $HC/lanes/handoff/tree_switch_*.json" > "$W/markers.json" || exit 3
  scp -q -o BatchMode=yes -o ControlPath=none $HUB:$C/fleet-ops-r/protected_struct.txt "$L" || exit 3
  $SSH $HUB "cd $HC/signed-store/records && ls */ | grep json.gz | sed 's/.json.gz//' | sort -u" > "$W/ids.txt" || exit 3
fi
[ -s "$W/ids.txt" ] || { echo "signed store id list empty: nothing done" >&2; exit 3; }
MODE=""; [ "${1:-}" = apply ] && MODE=--apply
echo "df before: $(df -BG --output=avail $C | tail -n 1)"
python3 -I "$AR" --kit-wave "$W/kit_wave.json" --state "$W/kit_wave_state.json" --markers "$W/markers.json" --store-ids "$W/ids.txt" \
  --guard-module "$G" --list "$L" --log "$D/log.jsonl" --target "${TARGET_GB:-350}" $MODE
rc=$?
echo "df after: $(df -BG --output=avail $C | tail -n 1)"
exit $rc
