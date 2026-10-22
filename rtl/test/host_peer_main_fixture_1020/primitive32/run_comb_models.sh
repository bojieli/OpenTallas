#!/bin/bash
set -eu
python3 check_comb_models.py > models/truth_receipt.json
python3 - <<'MUT'
from pathlib import Path
import re
s=Path('models/comb_models.v').read_text()
s,n=re.subn(r'assign (\w+) = (.*?);',r'assign \1 = ~(\2);',s,count=1);assert n==1
Path('models/comb_models_mut.v').write_text(s)
MUT
V=/opt/verilator-5.050/bin/verilator;[ -x "$V" ] || V=$(command -v verilator)
"$V" --version
for case in exact mutant;do
 src=models/comb_models.v;[ "$case" != mutant ] || src=models/comb_models_mut.v
 "$V" --binary --timing -Wno-fatal -j 4 --top-module tb_comb --Mdir "models/obj_$case" "$src" models/tb_comb.sv > "models/build_$case.log" 2>&1
 set +e;"models/obj_$case/Vtb_comb" > "models/run_$case.log" 2>&1;rc=$?;set -e
 cat "models/run_$case.log"
 if [ "$case" = exact ];then [ "$rc" = 0 ];else [ "$rc" != 0 ];grep -q 'COMB_MODELS FAIL' models/run_mutant.log;fi
done
