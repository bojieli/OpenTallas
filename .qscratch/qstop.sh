#!/bin/bash
# usage: qstop.sh <round>   stop only this agent's own jobs of that round (never another owner's)
# Matches only processes whose command line names this round's case directory or "qgrt_all.sh/qir_all.sh <round>";
# never a bare admit.sh / run_case.sh pattern (those match other owners' jobs).  Keeps the round directory as evidence.
set -u
R=$(cd $(dirname $0) && pwd); RD=$R/cases/$1
docker ps --format '{{.Names}}' | grep -F "hfd_$1_" | xargs -r docker stop > /dev/null
for p in $(ps -eo pid=,args= | awk -v rd="$RD/" -v r="$1" -v me=$$ \
           '$1 != me && (index($0, rd) || $0 ~ ("q(grt|ir)_all\\.sh " r "( |$)")) && $0 !~ /awk -v rd/ {print $1}'); do
  kill "$p" 2>/dev/null || true
done
echo "stopped by owner $(date -Is)" > "$RD/STOPPED"
echo STOPPED $1
