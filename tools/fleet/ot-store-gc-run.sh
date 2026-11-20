#!/bin/bash
# ot-store-gc-run (STORE-GC-HOURLY-1120, COORD/OWNER 11-20: apply cleanup on all hosts automatically): hourly, every gen host AND the hub: the ot-store's own by-reference GC for both scratch stores
# (gc-all --apply) with a 24 h record age-out.  An artifact record younger than 24 h, any record whose tree holds a SIGNED signoff.json, live job refs (job-*) and objects hardlinked into a live job
# dir are kept; nothing outside the store is touched.  The signed-store ingest (coord/tools/signed_store_ingest.py) reads sign-off records from the HOST DISKS (kits/lanes), never from the store, so a
# collected object cannot be an unread signed record; signed store trees are pinned by the GC itself.  Log: ~/.local/state/ot-store-gc/log.jsonl.
set -u
T=/srv/opentallas-scratch2/claude/rt/current/tools/fleet
D=$HOME/.local/state/ot-store-gc; mkdir -p "$D"
exec 9>"$D/lock"; flock -n 9 || { echo "another store GC is running: skipped"; exit 0; }
[ -f "$T/ot_store.py" ] || { echo "rt/current has no ot_store.py: nothing done" >&2; exit 3; }
OT_STORE_RECORD_AGE_H=${OT_STORE_RECORD_AGE_H:-24} nice -n 10 ionice -c2 -n 6 python3 -I "$T/ot_store.py" gc-all --apply 2>&1 | tee -a "$D/log.jsonl" | tail -2
exit ${PIPESTATUS[0]}
