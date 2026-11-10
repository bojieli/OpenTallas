#!/bin/bash
# FTLOCK-S81 (DIE-S81-85 11-10): strict bind of the ft_hop_lockup event plan 9c9ac92a70d1 (= wave plan b05c29bb + clock.ft_hop_lockup t27/t49)
# on the wave source kw43/src_t51f_pbp (copy bsrc: tools + physical/die_plan/s81 real copies, rest symlinks); elab reused from bind8 (real copies).
set -u
F=/srv/opentallas-scratch2/claude/die-s81-85/ftlock
SRC=$F/bsrc; AB=/srv/opentallas-scratch2/claude/type-safe-4/s81p3/asbuilt_f.json; OUT=$F/bind_ftlk; LOG=$F/bind_ftlk.log
P=physical/die_plan/s81/plan_h2_2249.json
cd "$SRC" || exit 2
export PYTHONDONTWRITEBYTECODE=1
/usr/bin/time -v prlimit --as=100000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt "$AB" --out "$OUT" --strict > "$LOG" 2>&1
rc=$?
echo "BIND rc=$rc $OUT" | tee $F/bind_ftlk.rc
tail -n 2 "$LOG" | cut -c1-300
exit $rc
