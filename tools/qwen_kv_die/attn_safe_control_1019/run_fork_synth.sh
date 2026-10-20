#!/bin/bash
set -euo pipefail
mkdir -p synth_fork_r2
python3 - <<'PY'
import pathlib,re
p=pathlib.Path('synth/config.mk').read_text().replace('qkd_kvs_attn_fl_ba5','qkd_kvs_attn_safe_control')
p=re.sub(r'^export VERILOG_FILES = .*$', 'export VERILOG_FILES = /work/candidate/qkd_kvs_attn_safe_control.v',p,flags=re.M)
p+='\n# Source already contains original two reset landing stages.\nexport OT_RST_LAND = 0\n'
pathlib.Path('synth_fork_r2/config.mk').write_text(p)
PY
docker run --rm --name kv-attn-sc-fork-synth-1019 -v "$PWD/src:/src:ro" -v "$PWD:/work" --entrypoint bash openroad/orfs:asap7lock -lc 'source /OpenROAD-flow-scripts/env.sh; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/work/synth_fork_r2/config.mk WORK_HOME=/work/synth_fork_r2 synth' > synth_fork_r2/run.log 2>&1
