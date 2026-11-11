#!/bin/bash
# FTLOCK-S81 (COORD 11-10): strict bind of event plan 9c9ac92a70d1 on epyc8 in a memory-capped container (64g; first
# attempt peaked >= 38 GB).  Source bsrc = hardlinked wave src (writable files privately copied, tools + s81 real copies),
# whole scratch2 mounted read-only, only OUT writable.  Elab reused from bind8 (real copies).
set -u
F=/srv/opentallas-scratch2/claude/die-s81-85/ftlock; O=$F/bind_ftlk; CAP=64; YCAP=32   # bind_elab runs yosys in a sibling ORFS container capped at 32g (try1 failed: no docker in container)
need=$(( (CAP + YCAP + 32) * 1024 * 1024 )); avail=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
[ "$avail" -ge "$need" ] || { echo "MemAvailable $avail kB < cap+ycap+32 GB"; exit 3; }
docker run --rm --name ftlk_bind_$$ -u $(id -u):$(id -g) --group-add $(stat -c %g /var/run/docker.sock) -v /usr/bin/docker:/usr/bin/docker:ro -v /var/run/docker.sock:/var/run/docker.sock -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 \
  --memory ${CAP}g --memory-swap ${CAP}g --cpus 2 \
  -v /srv/opentallas-scratch2:/srv/opentallas-scratch2:ro -v /srv/opentallas-scratch3:/srv/opentallas-scratch3:ro -v $O:$O -w $F/bsrc python:3.14-slim \
  python -I -B tools/die_plan/bind.py bind physical/die_plan/s81/plan_h2_2249.json \
    --asbuilt /srv/opentallas-scratch2/claude/type-safe-4/s81p3/asbuilt_f.json --out $O --strict > $F/bind_ftlk.log 2>&1
rc=$?
echo "BIND rc=$rc $O" > $F/bind_ftlk.rc
exit $rc
