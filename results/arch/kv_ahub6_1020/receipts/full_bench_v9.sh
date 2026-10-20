#!/bin/bash
set -eu
R=/srv/opentallas-scratch/codex/kv-ahub6
B=/srv/opentallas-scratch/claude/ref_gate/qkd_ahub_g4a-20261019-215713/src
W=$R/full_behavior_v9
mkdir -p "$W/src"
python3 - "$B" "$W/src" "$R" <<'INNER'
from pathlib import Path
import re,sys,shutil
b,w,r=map(Path,sys.argv[1:]);script=(b/'tools/qwen_kv_die/ahub4/g3_bench.sh').read_text()
sources=re.search(r'SRC="(.*?)"',script,re.S).group(1).replace('$DW','rtl/hdc/nearhbm/qkd_ahub_static_dw_safe.sv').split()
for f in sources:
 p=w/f;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(b/f,p)
shutil.copyfile(r/'control_overlay_v9.sv',w/'rtl/hdc/nearhbm/lp/qkd_ahub_static_dw_g3_lp.sv')
shutil.copyfile(r/'qkd_ahub6_controls_v9.sv',w/'rtl/hdc/nearhbm/qkd_ahub6_controls.sv')
p=w/'tools/qwen_kv_die/ahub4/g3_bench.sh';p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(script.replace('SRC="rtl/hdc/ot_hdc_fpu.sv','SRC="rtl/hdc/nearhbm/qkd_ahub6_controls.sv rtl/hdc/ot_hdc_fpu.sv'))
INNER
cd "$W/src"
for m in 0 1 19;do
set +e
bash tools/qwen_kv_die/ahub4/g3_bench.sh "$W/out" "$m" > "$W/m$m.log" 2>&1
rc=$?
set -e
if [ "$m" = 0 ];then grep '^AHUB_DW PASS' "$W/m$m.log";test "$rc" = 0;else grep '^AHUB_DW FAIL' "$W/m$m.log";test "$rc" != 0;fi
done
echo AHUB6_FULL_SUITE_PASS
