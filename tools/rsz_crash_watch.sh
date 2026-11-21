#!/bin/bash
# RSZ-CRASH-2200 / COORD 11-20: label any NEW RSZ-0074 repair fallback INFRA[rsz_crash] (a crashed repair, not a timing failure).
# usage (hub, nohup, 12 h): bash ~/coord/tools/rsz_crash_watch.sh   ; state ~/.local/state/rsz_crash_seen.txt ; one post per fallback log.
# A fallback = kit tt_setup_repair_fallback.log with 'GRT step failed' / 'FAIL class=tt_setup_repair_fallback' and RSZ-0074 in tt_setup_repair_grt.log or tt_setup_repair.log.
ST=$HOME/.local/state/rsz_crash_seen.txt; mkdir -p "$(dirname "$ST")"; touch "$ST"
END=$(( $(date +%s) + ${RSZ_WATCH_SECS:-43200} ))
scan='nice -n 19 ionice -c3 find /srv/opentallas-scratch /srv/opentallas-scratch2 /srv/opentallas-scratch3 -xdev -name tt_setup_repair_fallback.log -mmin -45 -size +0 2>/dev/null | while read f; do d=$(dirname "$f"); grep -qs "tt_setup_repair_fallback\|step failed" "$f" || continue; grep -qs "RSZ-0074" "$d/tt_setup_repair_grt.log" "$d/tt_setup_repair.log" || continue; echo "$(hostname) $d $(stat -c %Y "$f")"; done'
while [ "$(date +%s)" -lt "$END" ]; do
  for h in intel1 epyc2 epyc7 epyc8 epyc9 epyc10; do
    timeout 600 ssh -o ControlPath=none -o ConnectTimeout=20 $h "$scan" < /dev/null 2>/dev/null | while read host dir t; do
      key="$host:$dir:$t"; grep -qxF "$key" "$ST" && continue; echo "$key" >> "$ST"
      bash $HOME/coord/bin/post.sh RSZ-CRASH-WATCH "INFRA[rsz_crash] $host:$dir: repair_timing crashed with RSZ-0074 and the kit kept the UNREPAIRED DB; not a timing failure, relaunch/refresh with main tt_setup_repair.tcl (504fcadebf6)"
    done
  done
  sleep 1800
done
