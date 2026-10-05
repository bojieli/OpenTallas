#!/bin/bash
set -uo pipefail
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
export OMP_NUM_THREADS=16 OT_ORFS_NUM_CORES=16
job=/srv/opentallas-scratch/codex/kant-code-pair-reverse-td-diamond-20261005-r2
while ! test -f "$job/supervisor.exit"; do sleep 30; done
rc=$(cat "$job/supervisor.exit")
if test "$rc" != 0; then echo "$rc" > "$job/collector.exit"; exit "$rc"; fi
image=$(docker image inspect openroad/orfs:asap7lock --format "{{.Id}}")
if test "$image" != sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29; then echo "Pinned STA image mismatch: $image" > "$job/collector.log"; echo 2 > "$job/collector.exit"; exit 2; fi
/srv/opentallas-scratch/admit.sh 8 -- python3 "$job/collector_source/tools/qwen_code_pair_directcapture_corner.py" --orfs-dir "$job/route" --macro physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 --macro physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 --output "$job/corner_sta.json" > "$job/collector.log" 2>&1
rc=$?
echo "$rc" > "$job/collector.exit"
exit "$rc"
