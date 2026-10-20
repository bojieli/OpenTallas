#!/bin/bash
# QW-TOK3 10-19: start the gold4 shared-prefix driver the moment the canonical TP4 gold (ep5 PID1583528,
# local ot-run 1216760) finishes. Polls every 10 min (cheap ssh). Never launches if the gold has no oracle.json.
D=/srv/opentallas-scratch/claude/qw-gold4-shared-prefix-1019
T=/srv/opentallas-scratch/claude/tokpass-qwen-1018
L=/home/ubuntu/scratch/qw-tok3-1019/gold4_trigger.prep-v2.log
log() { echo "$(TZ=America/Los_Angeles date '+%F %T') $*" >> $L; }
log "trigger start pid $$"
while kill -0 1216760 2>/dev/null || ssh -o ConnectTimeout=20 ot-epyc5 'kill -0 1583528' 2>/dev/null; do sleep 600; done
log "gold driver exited; $(ssh ot-epyc5 "tail -2 $T/STATUS.log" | tr '\n' ' ')"
if ! ssh ot-epyc5 "test -s $T/fx/gold/tp4/oracle.json && test -d $T/fx/gold/tp4/P8191"; then
  log "GOLD_INCOMPLETE: no oracle.json/P8191 -> NOT launching gold4"; exit 3; fi
log "launching gold4 via ot-run (data only on ep5 -> placement follows --dir)"
/home/ubuntu/bin/ot-run --mem 64 --threads 32 --dir $D -- bash -c "cd $D/src-prep-receipt-v2 && $T/py tools/qwen_layerbench/gold4_shared_prefix.py --fx $T/fx --canonical-gold $T/fx/gold/tp4 --oracle-root $T/src --out $D/out --python $T/py --threads 32 --run > $D/gold4.log 2>&1; rc=\$?; echo rc=\$rc >> $D/gold4.log; exit \$rc" >> $L 2>&1
log "gold4 ot-run rc=$?"
