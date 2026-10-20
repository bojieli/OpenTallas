#!/bin/bash
set -euo pipefail
mkdir -p source;tar xzf source.tgz -C source
cp tb_parent_earliest.sv source/
cd source
python3 - <<'PY2'
from pathlib import Path
s=Path('rtl/test/run_hbm_hc_root_landed.sh').read_text();s=s.split('src=(',1)[1].split(')\n',1)[0]
s=s.replace('$H','rtl/hbm_accel/generic/peers/static_hc').split()
s=[x for x in s if x!='rtl/test/tb_hbm_hc_eng4_static.sv']
Path('files.f').write_text('\n'.join(s)+'\n')
PY2
iverilog -g2012 -DOT_FP_DATA_NORST -s tb_parent_earliest -o ../parent.vvp tb_parent_earliest.sv -f files.f >../build.log 2>&1
cd ..
vvp parent.vvp +MUT=0 | tee parent_positive.log
vvp parent.vvp +MUT=1 | tee parent_mutant.log
