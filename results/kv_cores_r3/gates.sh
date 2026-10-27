#!/bin/bash
# KV-CORES-R3 head type delta plan gates (check.py G0 + G0C --completeness), diagnostic, ulimit 48G each
cd /srv/opentallas-scratch2/claude/kv-cores-r3; ulimit -v 48000000; export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r19-1027/in/pylib:$PWD/tools/die_plan
CE=/srv/opentallas-scratch2/claude/kv-core-slice-1-1027/pd/hm_cells_evidence.json
for v in base:/srv/opentallas-scratch2/claude/clock-kv-r21-1027/slice/pd pdA:pdA pdB0:pdB0 pdBM:pdBM; do n=${v%%:*}; d=${v#*:}
 ( python3 tools/die_plan/check.py $d/hm_r21.json --out g0c_$n --completeness --cells-evidence $CE > g0c_$n.log 2>&1; echo "g0c_$n rc=$?" >> gates.done ) &
done; wait; echo ALL $(date -Is) >> gates.done
