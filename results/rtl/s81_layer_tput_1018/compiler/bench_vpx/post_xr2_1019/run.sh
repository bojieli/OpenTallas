#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/claude/tok2-vpx/takeover3
F=/srv/opentallas-scratch/claude/layerbench-s81/fixtures/L0
B=/srv/opentallas-scratch/claude/tok2-vpx/out_head/obj/Vtb_vpx_ag
sha256sum "$B" tools/s81_dv/layer_prog/lower_vpx.py tools/s81_dv/layer_prog/vpx/* "$F"/files.json "$F"/ops/attn.a_allgather.bin > inputs.sha256
rc=0
for m in none row shift; do
 C=cases/$m
 python3 tools/s81_dv/layer_prog/vpx/gen_vpx_ag.py --fixtures "$F" --out "$C" --mut "$m"
 /usr/bin/time -v -o "$C/time_run.log" "$B" +STIM="$C/stim.txt" > "$C/run.log" 2>&1
 set +e
 python3 tools/s81_dv/layer_prog/vpx/check_vpx_ag.py --dir "$C" > "$C/check.out" 2>&1
 r=$?
 set -e
 echo "CASE $m rc=$r"
 head -2 "$C/check.out"
 if [ "$m" = none ]; then [ "$r" = 0 ] || rc=1; else [ "$r" = 1 ] || rc=1; fi
 echo "$r" > "$C/check.exit"
done
echo VPX_FIXED_DONE_RC=$rc
exit "$rc"
