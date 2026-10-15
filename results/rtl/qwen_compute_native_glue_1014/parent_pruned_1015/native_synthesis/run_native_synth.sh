#!/usr/bin/env bash
set -euo pipefail
stage=/srv/opentallas-scratch/claude/qce-parent-prune-native899
base=/srv/opentallas-scratch/claude/ref_gate/qfd_tile_nk_banked_v1-20261015-035551
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
python3 - <<'PY'
from pathlib import Path
import hashlib,json
R=Path('/srv/opentallas-scratch/claude/qce-parent-prune-native899')
p=R/'work/config.mk'
p.write_text(p.read_text()+'\nexport VERILOG_FILES += /src/rtl/qwen_sys/tile_parent_banked_20261015/ot_qce_banked_v1_prunable_arith.sv\n')
files=['rtl/qwen_sys/tile_parent_banked_20261015/ot_qwen_w12_matvec_part_banked_v1.sv','rtl/qwen_sys/tile_parent_banked_20261015/ot_qce_banked_v1_prunable_arith.sv']
h={n:hashlib.sha256((R/'src'/n).read_bytes()).hexdigest()for n in files}
(R/'native_input_hashes.json').write_text(json.dumps(h,indent=2)+'\n')
print('NATIVE_PRUNE_INPUTS',h)
PY
docker image inspect --format '{{.Id}}' "$image"
docker run --rm -e LEC_CHECK=0 -e OT_ORFS_CORNER_OVERRIDE=TC -v "$stage/src:/src:ro" -v "$stage/work:/work" -w /OpenROAD-flow-scripts/flow "$image" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > "$stage/native_synth.log" 2>&1
echo NATIVE_SYNTH_COMPLETE
