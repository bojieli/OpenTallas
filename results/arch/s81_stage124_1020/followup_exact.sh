#!/bin/bash
# Already-authorized continuation: pure content/topology receipts only.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
cd "$D"
while [ ! -f stage_table_124.md ]; do
 if ! systemctl --user is-active --quiet oth-ubuntu-1235010-1792526112.scope; then
  echo 'CAPACITY_JOB_TERMINAL_WITHOUT_MERGED_TABLE; inspect probe.log/map.log/exact.log/merge.log'; exit 1
 fi
 sleep 30
done
python3 qualify_static.py stage_map_124.json > qualify_static.log 2>&1
python3 xs_stage_integrate.py --map stage_map_124.json --out physical_stage_composition.json > physical_stage_composition.log 2>&1
echo 'STATIC124_CONTENT_TOPOLOGY_PASS; AR/MTP calendar and behavioural chain still owed'
