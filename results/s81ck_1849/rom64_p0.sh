#!/bin/bash
set -uo pipefail
R=/srv/opentallas-scratch2/claude/codex-s81ck-1849/rom64_p0
mkdir -p "$R/out"
echo "start $(date -Is)" > "$R/run.status"
docker run --rm --name codex-s81ck-rom64-p0-1857 --memory=64g --memory-swap=64g --cpus=8 -v "$R/kit":/work:ro -v "$R/out":/lecout -v /srv/opentallas-scratch2/claude/die-s81-25/lec.py:/lec.py:ro -e HUID=$(id -u) -e HGID=$(id -g) -e OT_LEC_RESET_CYCLES=64 openroad/orfs:asap7lock bash -lc 'python3 -I /lec.py /work --out /lecout --conflicts 1000 --jobs 8 > /lecout/run.log 2>&1; rc=$?; chown -R $HUID:$HGID /lecout; exit $rc'
rc=$?
echo "lec rc $rc $(date -Is)" >> "$R/run.status"
exit $rc
