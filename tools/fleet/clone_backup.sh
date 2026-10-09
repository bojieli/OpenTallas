#!/bin/bash
# clone_backup.sh HOST EVAL_JSONL OUT_OKLIST   (HOST=localhost for local paths)
H=$1; E=$2; OK=$3; LOG=/home/ubuntu/disk_recovery_20261007.log; : > $OK
cd /home/ubuntu/OpenTallas
python3 -c "
import json,sys
for l in open('$E'):
    r=json.loads(l)
    if r['v']=='CANDIDATE': print('|'.join([r['wt'],r['sha'],r['ref'],str(r['ndirty'])]))
" | while IFS='|' read w sha ref nd; do
  name=$(basename $(dirname "$w"))-$(basename "$w")
  if [ "$nd" = "0" ] && git cat-file -e $sha 2>/dev/null && [ -n "$(git branch -r --contains $sha 2>/dev/null | head -1)" ]; then
     echo "$w" >> $OK; echo "$(date -Is) $H clone $w clean, HEAD ${sha:0:12} on origin; no backup needed" >> $LOG; continue; fi
  if [ "$H" = localhost ]; then url="$w"; else url="ssh://$H$w"; fi
  if ! timeout 900 git fetch -q "$url" "+$ref:refs/diskrec-tmp/$H" 2>/dev/null; then echo "$(date -Is) $H SKIP clone $w: fetch failed" >> $LOG; continue; fi
  if [ "$nd" = "0" ] && [ -n "$(git branch -r --contains $sha 2>/dev/null | head -1)" ]; then echo "$w" >> $OK; echo "$(date -Is) $H clone $w HEAD ${sha:0:12} on origin; no backup needed" >> $LOG; git update-ref -d refs/diskrec-tmp/$H; continue; fi
  br="backup/wt-$H-$name-20261007"
  if git push -q origin "$sha:refs/heads/$br" 2>/dev/null; then echo "$w" >> $OK; echo "$(date -Is) $H BACKUP clone $w -> origin/$br @ ${sha:0:12} (dirty=$nd)" >> $LOG
  else echo "$(date -Is) $H SKIP clone $w: push failed" >> $LOG; fi
  git update-ref -d refs/diskrec-tmp/$H
done
wc -l < $OK
