#!/bin/bash
# PROTO 1025 launcher: one ot-run per generated skeleton part dir listed in GEN/jobs.json (types filter optional file)
GEN=$1; ONLY=${2:-}
cd $GEN
python3 -c "
import json,sys
only=set(open('$ONLY').read().split()) if '$ONLY' else None
for j in json.load(open('jobs.json')):
    if only is None or j['type'] in only: print(j['dir'], j['mem_gb'])
" | while read D M; do
  [ -e $D.otrun.log ] && continue
  nohup ~/.local/bin/ot-run --mem $M --threads 8 --dir $D --stage $D -- bash $D/run.sh < /dev/null > $D.otrun.log 2>&1 &
  sleep 1
done
