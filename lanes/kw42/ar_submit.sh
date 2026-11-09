#!/bin/bash
# KW-FIX-42: resubmit an auto-resign unit pinned to epyc7 (same argv as the waiting autopilot unit, own log)
set -eu
OLD=$1; NEW=kw42-$1-e7; LOG=$HOME/coord/autopilot/auto_resign_jobs/$NEW.log
A=$(systemctl --user show $OLD -p ExecStart | sed -e "s/^.*argv\[\]=\/bin\/bash -c //" -e "s/ ; ignore_errors=.*$//")
A=${A//$OLD.log/$NEW.log}; A=${A//AP_START \$(date +%s) $OLD/AP_START \$(date +%s) $NEW}
A=$(echo "$A" | sed -E "s/--hosts [a-z0-9]+ /--hosts epyc7 /")
echo "$A" | grep -q -- "--hosts epyc7 " || { echo "no host rewrite"; exit 2; }
systemd-run --user --unit $NEW /bin/bash -c "$A"
echo "submitted $NEW log $LOG"
