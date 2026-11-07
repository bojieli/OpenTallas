#!/bin/bash
set -u
cd "$(dirname "$0")"
export CCACHE_DISABLE=1
python3 -I -c 'import json; c=json.load(open("candidate.json")); assert (c["common_KIT"],c["common_END"]) == (7163,7183), "finite47 fixture uses explicit KIT7163/END7183 book"' || exit 94
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --assert -Wno-fatal --top-module tb47 -j 2 -CFLAGS '-O1 -fno-var-tracking' -Mdir obj47 tb47.sv ot_dsdv_walk_issue.sv dsdv_mu_hslot.sv ot_rst_relay.sv ot_s81ph_mem1r1w.sv ot_sram_1r1w_512x128_m4_r2c2.v > build47.log 2>&1
rc=$?; echo "$rc" > build47.rc
[ "$rc" -eq 0 ] || exit "$rc"
obj47/Vtb47 > positive47.log 2>&1
rc=$?; echo "$rc" > positive47.rc
[ "$rc" -eq 0 ] || exit "$rc"
obj47/Vtb47 +OLDTAG=1 > oldtag47.log 2>&1
rc=$?; echo "$rc" > oldtag47.rc
[ "$rc" -ne 0 ] || exit 92
grep -Eq 'runtime page0 t[0-9]+ code(6|8)' oldtag47.log || exit 93
echo 'COMPONENT47_PASS actual8 pages, 47-entry native tracker, one reset, stale-tag control caught'
