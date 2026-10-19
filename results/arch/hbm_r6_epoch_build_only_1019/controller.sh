#!/bin/bash
set -uo pipefail
P=/home/ubuntu/artifacts/hbm-r6-epoch-build-only-1019
date -u +%FT%TZ > "$P/controller_started_utc"
/home/ubuntu/bin/ot-run --mem 320 --threads 8 --disk 60 --dir /srv -- python3 /tmp/hbm-r6-epoch-build-only-1019/compile_only.py > "$P/ot-run.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$P/controller_exit_code"
date -u +%FT%TZ > "$P/controller_finished_utc"
exit "$rc"
