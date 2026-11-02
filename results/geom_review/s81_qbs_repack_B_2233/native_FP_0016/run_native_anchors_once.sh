#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-hist-nativeanchors-0005
docker run --rm --memory=4g --memory-swap=4g --cpus=1 -e HUID="$(id -u)" -e HGID="$(id -g)" -v "$R":/work openroad/orfs:asap7lock bash -lc 'set -euo pipefail; trap '\''chown -R "$HUID:$HGID" /work'\'' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; ODB=/work/fresh_fp.odb TARGETS=/work/targets.json OUT=/work/anchored.odb openroad -python -exit /work/apply.py' > "$R/native.log" 2>&1
