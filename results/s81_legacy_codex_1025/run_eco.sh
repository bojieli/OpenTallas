#!/bin/bash
set -euo pipefail
K=$(cd "$1" && pwd); MEM=${2:-24}; CPUS=${3:-8}
case "$K" in /srv/opentallas-scratch2/claude/codex-s81-legacy/eco/*) ;; *) exit 2;; esac
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
NAME=codex-legacy-eco-$(basename "$K")-$$
docker run --rm --name "$NAME" --cpus "$CPUS" --memory "${MEM}g" --memory-swap "${MEM}g" -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; rc=0; \$M do-route CORNER=BC CORNERS=bc SKIP_INCREMENTAL_REPAIR=1; rc=\$?; if [ \$rc = 0 ]; then \$M do-finish && \$M do-generate_abstract; rc=\$?; fi; chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_eco.log" 2>&1
python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff_codex" --image "$IMAGE" --docker docker > "$K/signoff_codex.log" 2>&1
