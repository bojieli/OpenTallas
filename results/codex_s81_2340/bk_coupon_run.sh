#!/bin/bash
set -eu
b=/srv/opentallas-scratch2/claude/codex-s81-2340/bk_dme_coupon
old=/srv/opentallas-scratch2/claude/die-s81-18/go16/kit/grt/obs.tcl
printf 'START %s native c0e4ae487, homesFIRM, actual2W2S, PGobstructions, nooverlay\n' "$(date)" > "$b/status"
for c in TT FF; do
 mkdir -p "$b/out_$c"
 cp "$b/coupon.tcl" "$b/out_$c/coupon.tcl"
 docker run --rm --name "codex-s81-bkdme-$c" --memory=24g --memory-swap=24g --cpus=4 -e CORNER="$c" -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v "$b":/work:ro -v "$b/out_$c":/out -v "$old":/inputs/pg_obs.tcl:ro openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 4 -exit /out/coupon.tcl > /out/openroad.log 2>&1; run_rc=$?; echo EXIT "$run_rc" >> /out/openroad.log; exit "$run_rc"' > "$b/out_$c/docker.log" 2>&1 &
 if [ "$c" = TT ]; then tt_pid=$!; else ff_pid=$!; fi
done
rc=0;wait "$tt_pid" || rc=$?;wait "$ff_pid" || rc=$?
for c in TT FF; do tail -n 5 "$b/out_$c/openroad.log" >> "$b/status";done
printf 'DONE %s RC%s\n' "$(date)" "$rc" >> "$b/status"
exit "$rc"
