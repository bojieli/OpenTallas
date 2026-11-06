#!/usr/bin/env bash
# drive.sh NAME MLAT ALAT LDCS DM DA LANE_ID CYC MUT [DEFINES]   (inside docker)
E=/srv/opentallas-scratch2/claude/hbm-gaps-5-l1p/eq
N=$1; shift
exec "$E/run_bench.sh" "$E/src" "$E/runs/$N" "$@"
