#!/bin/bash
set -eu
W=/srv/opentallas-scratch2/claude/codex-s81-rck-1106
cd "$W/landing_keep"
docker run --rm --memory 4g --cpus 2 -v "$W":/work -v /srv/opentallas-scratch3/claude/wt/codex-lec-transfer-1106:/src:ro openroad/orfs:asap7lock bash /work/landing_keep/run.sh > result.log 2>&1
