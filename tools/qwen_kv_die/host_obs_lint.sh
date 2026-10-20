#!/bin/bash
# KV-BIND5-OBS 10-19: Verilator 5.050 elaboration lint of a HOST root closure with the die's parameters
# (kv_die.host_rt_binding: ENABLE_SERVICE / NATIVE / TOKEN = 1, NL = 2).  usage: host_obs_lint.sh MASTER OUTDIR
set -u
M=$1; O=$2; mkdir -p $O
R=$(cd "$(dirname "$0")/../.." && pwd)
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
python3 $R/tools/qwen_kv_die/kv_host_obs_classify.py filelist --master $M --out $O > $O/filelist.log 2>&1 || { cat $O/filelist.log; exit 2; }
OT_SRC=$R python3 - $O/files.json > $O/files.f <<'PY'
import json,sys,os
d=json.load(open(sys.argv[1]))
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[1]))))
# children the regex closure does not see (module in a differently named file / `include'd SRAM): explicit
extra=['rtl/physical/ot_qwen_host_ctl.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']
for f in d['files']: print(f)
for f in extra:
    q=os.path.join(os.environ['OT_SRC'],f)
    if os.path.exists(q) and q not in d['files']: print(q)
print('\n'.join('+incdir+'+x for x in sorted({os.path.dirname(f) for f in d['files']})))
PY
verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module $M \
  -GENABLE_SERVICE=1 -GENABLE_NATIVE=1 -GENABLE_TOKEN=1 -GNL=2 -f $O/files.f > $O/lint.log 2>&1
rc=$?
grep -c "%Error" $O/lint.log; grep "%Error" $O/lint.log | head -20
echo "lint rc=$rc"; exit $rc
