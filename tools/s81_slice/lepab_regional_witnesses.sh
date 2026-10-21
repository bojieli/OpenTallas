#!/usr/bin/env bash
set -u
P=${1:?result-prefix}
pids=()
for m in TAGDROP WRONGCOPY LANDCUT STALEHD; do
 bash tools/s81_slice/lepab_regional_bench.sh "$P-$m" "$m" 1 > "$P-$m.log" 2>&1 & pids+=("$!")
done
rc=0
for p in "${pids[@]}"; do wait "$p" || true; done
for m in TAGDROP WRONGCOPY LANDCUT STALEHD; do
 if grep -q '^FAIL lepab_regional:' "$P-$m/run.log"; then echo "MUTANT_CAUGHT $m"; else echo "MUTANT_NOT_CAUGHT $m";rc=1;fi
done
exit "$rc"
