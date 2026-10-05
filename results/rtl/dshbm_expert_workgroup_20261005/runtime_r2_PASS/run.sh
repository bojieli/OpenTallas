#!/bin/bash
set -eu
src=/srv/opentallas/repos/hubble-expert-workgroup-90b8a03e8
out=/srv/opentallas-scratch/jobs/hubble-expert-workgroup-actual-r2
receipt=/srv/opentallas-scratch/jobs/hubble-expert-workgroup-build-r1/terminal.json
while [ ! -f "$receipt" ]; do sleep 10; done
python3 - "$receipt" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))['status']=='PASS_COMPILED_ONLY'
PY
cd "$src"
git rev-parse HEAD > "$out/source_commit"
sha256sum tools/dshbm_expert_workgroup.py tools/dshbm_matched_sm_seq.py tools/hdc_golden.py tools/hdc_golden_v41.py > "$out/host_source_sha256.txt"
for layer in 20 3; do
 /srv/opentallas-scratch/admit.sh 16 -- python3 tools/dshbm_expert_workgroup.py \
  --weight-rows "/srv/opentallas-scratch/jobs/hubble-expert-workgroup-source-inputs-20261005/L$layer" \
  --layer "$layer" --position 1048575 \
  --activation-u32 "$src/results/rtl/dshbm_expert_workgroup_20261005/source_inputs/L$layer/ffn_norm.u32" \
  --router-ids-u32 "$src/results/rtl/dshbm_expert_workgroup_20261005/source_inputs/L$layer/expert_ids.u32" \
  --native-receipt "$receipt" --workdir "$out/L$layer" --jobs 8 > "$out/L${layer}.log" 2>&1
 printf 'L%s_rc=0\n' "$layer" >> "$out/exit"
done
