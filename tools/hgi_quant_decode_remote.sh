#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
setsid /usr/bin/time -v bash tools/hgi_quant_decode_bench.sh "$out" > "$out/driver.log" 2>&1 &
pid=$!
printf '%s\n' "$pid" > "$out/driver.pid"
while kill -0 "$pid" 2>/dev/null; do
 ps -eo pid,ppid,pgid,rss,args | awk -v pg="$pid" '$3==pg' >> "$out/process_samples.log"
 sleep 5
done
set +e
wait "$pid"
rc=$?
set -e
printf '%s\n' "$rc" > "$out/rc"
exit "$rc"
