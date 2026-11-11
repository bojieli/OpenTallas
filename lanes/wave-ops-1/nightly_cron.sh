#!/bin/bash
# WAVE-OPS-1 nightly wave-source rebuild (OWNER 11-10 item B).  build at ~02:00 PST (after ROOT-MERGE-57's ~01:30
# UNLANDED train post): main + approved unlanded overlays + each die's wave branch + the live tree's own overlays ->
# NEW dated trees /srv/opentallas-scratch2/claude/wave-src/<YYYYMMDD>/<die> on every gen host (byte-checked), strict
# binds launched; advance (every 30 min) collects the binds, bind-diffs and posts.  The wave config switches only with
# lanes/wave-ops-1/SWITCH-OK.  Disable: remove the "wave-ops-1/nightly_cron.sh" lines from the localhost crontab.
set -u
cd /
MODE=${1:-advance}
H=/home/ubuntu/coord/lanes/wave-ops-1
ST=/home/ubuntu/.local/state/wave-ops-1
mkdir -p $ST
exec 9>$ST/nightly.lock; flock -n 9 || exit 0
D=$(TZ=America/Los_Angeles date +%Y%m%d)
if [ "$MODE" = advance ]; then           # the build of tonight, or of yesterday while its binds still run
  for d in $D $(TZ=America/Los_Angeles date -d yesterday +%Y%m%d); do
    timeout 7000 python3 -I $H/nightly_wave_src.py advance $d >> $ST/nightly-$d.log 2>&1
  done
  exit 0
fi
[ "$(TZ=America/Los_Angeles date +%H)" = 02 ] || exit 0
echo "$(date '+%F %T %Z') build $D" >> $ST/nightly-$D.log
timeout 21000 python3 -I $H/nightly_wave_src.py build $D >> $ST/nightly-$D.log 2>&1
echo "$(date '+%F %T %Z') build rc=$?" >> $ST/nightly-$D.log
