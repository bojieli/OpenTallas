#!/bin/bash
# usage: qstop.sh <round>   stop only this agent's own jobs of that round (never another owner's)
set -u
R=$(cd $(dirname $0) && pwd); RD=$R/cases/$1
docker ps --format '{{.Names}}' | grep -F "hfd_$1_" | xargs -r docker stop > /dev/null
for p in $(pgrep -f "^/bin/bash .*run_case.sh" ; pgrep -f qgrt_all.sh ; pgrep -f qir_all.sh ; pgrep -f admit.sh); do
  [ "$p" = "$$" ] || [ "$p" = "$PPID" ] || kill "$p" 2>/dev/null || true
done
sleep 2
rm -rf "$RD"
echo STOPPED $1
