#!/bin/bash
# closed-archive-1011 post-close hook: closure_loop.finish(CLOSED) starts this detached (setsid -f) with the job name.
# Waits until the loop has saved the CLOSED state, then archives the job's final files and streams its GDS if missing.
# Never deletes anything on fleet hosts.  Disable: CL_CLOSED_ARCHIVE=0 in the daemon env, or remove this file.
name=$1; [ -n "$name" ] || exit 0
T=/home/ubuntu/closed_archive/_tools
S=$HOME/.local/state/closure_loop/jobs/$name.json
LOG=/home/ubuntu/claude-takeover-20261007/closed-archive-1011.log
for i in $(seq 1 120); do
  [ -f "$S" ] || [ $i -lt 5 ] || exit 0
  [ -f "$S" ] && python3 -c "import json,sys;sys.exit(0 if json.load(open('$S')).get('status')=='CLOSED' else 1)" 2>/dev/null && break
  sleep 30
done
python3 -c "import json,sys;sys.exit(0 if json.load(open('$S')).get('status')=='CLOSED' else 1)" 2>/dev/null || { echo "$(date -Iseconds) HOOK $name: not CLOSED after 1 h, skipped" >> $LOG; exit 0; }
echo "$(date -Iseconds) HOOK $name: archiving" >> $LOG
exec 9>"$T/.hook-$name.lock"; flock -n 9 || exit 0
nice -n 10 python3 "$T/archive.py" jobs "$name" >> "$T/hook.out" 2>&1
nice -n 10 python3 "$T/gen_gds.py" "$name" >> "$T/hook.out" 2>&1
rm -f "$T/.hook-$name.lock"
