#!/bin/bash
set -euo pipefail
B=/srv/opentallas-scratch2/claude/codex-qc-mesh5-1029
A=/srv/opentallas-scratch2/claude/codex-qc-pg-access-1029
Q=/srv/opentallas-scratch2/claude/codex-qc-1029/baseline26/mechanics119_h800
mkdir -p "$B/census119_h800"
sudo docker run --rm --name codex-qcmesh5-export --memory=12g --memory-swap=12g --cpus=2 -v "$B/src/results/qc_pg_access_1029:/src:ro" -v "$Q:/in:ro" -v "$B/census119_h800:/out" openroad/orfs:asap7lock bash -c 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap "chown -R 1000:1000 /out" EXIT; openroad -python -exit /src/export_geometry119.py --odb /in/clock_grafted.odb --out /out'
cp "$Q/endpoints.json" "$B/census119_h800/"
cp "$A/census119/"{power_terms.json,pg_rects.json,probe_census.json} "$B/census119_h800/"
"$A/venv/bin/python3" "$B/src/results/qc_pg_access_1029/plan_access.py" --input "$B/census119_h800" --clock-seed /srv/opentallas-scratch2/claude/codex-qc-physical-1029/inputs/clock_base_access26_minarea.json --joint-clock-reserved "$B/joint_seed/joint_clock_reserved.json" --out "$B/pg_joint484"
