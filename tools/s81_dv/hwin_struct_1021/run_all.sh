#!/usr/bin/env bash
set -euo pipefail
O=${1:?outdir}; mkdir -p "$O"
for v in ns47 ns2 norelay eastcopy eastdue mut2; do
 rc=0
 bash tools/s81_dv/hwin_struct_1021/run.sh "$O/$v" "$v" > "$O/$v.log" 2>&1 || rc=$?
 case "$v" in
 ns47|ns2) test "$rc" = 0; grep -q '^MUWIN PASS$' "$O/$v.log";;
 eastdue) test "$rc" != 0; grep -q 'event boot count differs' "$O/$v.log";;
 *) test "$rc" != 0; grep -q -E 'Assertion failed.*(EARLY_MITER|CBREF_MITER)' "$O/$v.log";;
 esac
 echo "EXPECTED $v rc=$rc"
done
