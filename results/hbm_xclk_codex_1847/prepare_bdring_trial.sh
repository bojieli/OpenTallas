#!/bin/bash
# Execute on epyc2; copies only, never changes the inherited source kit.
set -euo pipefail
src=/srv/opentallas-scratch2/claude/hbm-cores-kits-20/bd/bdring_k20vb
dst=${1:?Supply a NEW empty trial directory under scratch2}
case "$dst" in /srv/opentallas-scratch2/claude/*) ;; *) echo 'scratch2 destination required' >&2; exit 2;; esac
[ ! -e "$dst" ] || { echo 'destination exists; preserve it' >&2; exit 2; }
mkdir -p "$dst"
rsync -a --exclude='4_*' --exclude='5_*' --exclude='6_*' --exclude=signoff --exclude=views "$src/" "$dst/"
cat >> "$dst/config.mk" <<'CFG'
# Structural tree; no placement-RC delay padding. Clock/IO contracts unchanged.
export OT_TAP_REPORT_ONLY = 1
CFG
# Stage the selected/current shared orfs_hold_mm.tcl BEFORE pinning/launching.
# Existing trial3391167 used the hub main hold Tcl staged at18:51 (01ddd2e80 basis).
# Correct optional50-iteration setting for a NEW trial (not active3391167):
# export GLOBAL_ROUTE_ARGS = -congestion_iterations 50 -verbose
# Then review source placement image and record review, and submit through ot-run:
# ot-run --mem 40 --threads 16 --hosts epyc2 --dir "$dst" -- bash ./run_kit_hbm.sh "$dst" finish 40 16
