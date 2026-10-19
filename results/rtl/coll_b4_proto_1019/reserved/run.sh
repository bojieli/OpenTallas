#!/bin/bash
set -eu
D=/srv/opentallas-scratch/claude/coll-b4-reserved-r2-1019
cd "$D/src"
python3 tools/qwen_coll_b4_reserved_proto.py --cache-record "$D/cache/record_production.json" --cache-exe "$D/cache/Vtb_coll_tp8_static" --snapshot-manifest "$D/snapshot_source_manifest.json" --out "$D/out"
