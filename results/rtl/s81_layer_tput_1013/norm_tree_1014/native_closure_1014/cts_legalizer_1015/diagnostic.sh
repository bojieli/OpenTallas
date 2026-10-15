#!/bin/bash
set -euo pipefail
BASE=/srv/opentallas-scratch/claude/ref_gate/s81hc_ctfxnt_ref-20261014-232510
DIAG=/srv/opentallas-scratch/codex/snorm-legalizer-1015
mkdir -p "$DIAG"
cp -a "$BASE/src" "$DIAG/src"
cp -a "$BASE/routes/gate/work/orfs" "$DIAG/orfs"
python3 - "$DIAG" <<'PYCODE'
from pathlib import Path
import sys
r=Path(sys.argv[1]);c=r/'orfs/config.mk';s=c.read_text();s+='\nexport OT_HOLD_MM = 1\nexport OT_MM_FF_SDC = /src/physical/ref_tile/s81hc_ctfxnt_ref/signoff.sdc\nexport HOLD_SLACK_MARGIN = 30\n';c.write_text(s)
p=r/'orfs/hooks/pre_cts_pre_cts.tcl';p.write_text(p.read_text()+'\n# Diagnostic: exact timing repair, alternate complete legalization algorithm.\nrename detailed_placement ::ot_norm_original_dpl\nproc detailed_placement {args} {\n  write_db /work/pre_legalize.odb\n  puts "NORM_DIAMOND diagnostic saved pre-legalization"\n  ::ot_norm_original_dpl -use_diamond_legalizer {*}$args\n  check_placement -verbose\n  write_db /work/post_legalize.odb\n}\n')
for p in (r/'orfs/results').rglob('4*'):
 if p.is_file():p.unlink()
PYCODE
docker run --rm -v "$DIAG/src:/src:ro" -v "$DIAG/orfs:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base cts' > "$DIAG/run.log" 2>&1
