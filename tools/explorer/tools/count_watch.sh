#!/bin/bash
# Rebuild the explorer's design index as soon as the sign-off count has run (EXPLORER-FABLE-1, 2026-11-14).
# Every run (systemd user timer, 2 min): read the mtimes of the count outputs on the hub; when any changed, start the
# existing refresh unit (explorer2-refresh.service = refresh.sh: restage from the hub, plan_now, design_index, token map).
# Env: COUNT_HUB (default intel2), COUNT_STAMP (stamp file), REFRESH_UNIT (default explorer2-refresh.service).
HUB=${COUNT_HUB:-intel2}; UNIT=${REFRESH_UNIT:-explorer2-refresh.service}
STAMP=${COUNT_STAMP:-/srv/opentallas-scratch2/claude/explorer-fable-1/state/count_watch.stamp}
CENSUS="$(dirname "$STAMP")/signoff_census.json"
NOW=$(timeout 25 ssh -n -o BatchMode=yes -o ConnectTimeout=8 -o ControlPath=none "$HUB" \
  'stat -c "%n %Y" ~/.local/state/fleet-viz/release_tree_plan_cache.json ~/coord/lanes/COUNT-DIRECT.tsv ~/coord/lanes/AUTO-RESIGN.tsv ~/coord/RELEASE_TREE.md ~/.local/state/fleet-viz/agidock_archive_index.json ~/coord/signed-store ~/coord/lanes/COUNT-REVOKED.tsv 2>/dev/null') || exit 0
[ -n "$NOW" ] || exit 0
NOW="$NOW
$(stat -c '%n %Y' /srv/opentallas-scratch2/claude/explorer-fable-1/state/archive_index.json 2>/dev/null)"   # the archive gate follows the archive index too
if [ "$NOW" != "$(cat "$STAMP" 2>/dev/null)" ] || [ ! -s "$CENSUS" ]; then
  TMP=$(mktemp "${CENSUS}.XXXXXX") || exit 1
  trap 'rm -f "$TMP"' EXIT
  timeout 35 ssh -n -o BatchMode=yes -o ConnectTimeout=8 -o ControlPath=none "$HUB" \
    'python3 ~/coord/tools/count_hourly.py --explorer-json' > "$TMP" || exit 1
  [ -s "$TMP" ] || exit 1
  mv "$TMP" "$CENSUS" || exit 1
  systemctl --user start --no-block "$UNIT" && printf '%s\n' "$NOW" > "$STAMP" && echo "$(date -u +%FT%TZ) count outputs changed: refresh started"
fi
