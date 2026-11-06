#!/bin/bash
set -eu
cd "$(dirname "$0")"
K=/srv/opentallas-scratch2/claude/codex-s81-colle-compact-1106/e
docker run --rm --memory 8g --memory-swap 8g --cpus 2 -v "$K:/source:ro" -v "$PWD:/work" -w /work --entrypoint bash openroad/orfs:asap7lock -c '
 set -eu
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 python3 prepare_canary.py
 for tool in pin_audit.py pin_audit_core.py; do
  for mode in baseline declared wrong_rectangle wrong_layer wrong_anchor wrong_name; do
   ODB=/source/run/results/asap7/kl_dsfd_coll_lane_e_safe8_ntf_compact_m6_pg6_vB/base/6_final.odb PINS=/work/$mode.json OUT=/work/${tool%.py}_${mode}.json openroad -python -exit /work/$tool > /work/${tool%.py}_${mode}_run2.log 2>&1
  done
 done
 python3 -c '\''import json;from pathlib import Path
for tool in ["pin_audit","pin_audit_core"]:
 for mode in ["baseline","declared","wrong_rectangle","wrong_layer","wrong_anchor","wrong_name"]:
  r=json.loads(Path(f"{tool}_{mode}.json").read_text());print(tool,mode,r["verdict"],r["ok"],r["pins"]);assert (r["verdict"]=="PASS")== (mode=="declared")
'\''
'
