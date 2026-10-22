#!/bin/bash
set -euo pipefail
yosys -V > yosys.version
yosys -Q -T -p 'read_verilog tiny.sv; hierarchy -top top; proc; techmap; opt_clean; write_json in.json; write_rtlil original.il' > prep.log 2>&1
python3 old.py --json in.json --max 256 --ys old.ys --tsv old.tsv > old_tool.log
python3 fixed.py --json in.json --max 256 --ys fixed.ys --tsv fixed.tsv > fixed_tool.log
if yosys -Q -T -p 'read_rtlil original.il; script old.ys' > old.log 2>&1;then echo OLD_UNEXPECTED_PASS;exit 1;fi
grep -q "Failed to parse port expression" old.log
yosys -Q -T -p 'read_rtlil original.il; script fixed.ys; check -assert; write_rtlil fixed.il' > fixed.log 2>&1
python3 - <<'PY'
from pathlib import Path
s=Path('fixed.ys').read_text();lines=s.splitlines()
i=next(i for i,x in enumerate(lines) if x.startswith('connect -set') and '__c1__v2[0]' in x)
lines[i]=lines[i].rsplit(' ',1)[0]+" 1'0"
Path('mutant.ys').write_text('\n'.join(lines)+'\n')
PY
yosys -Q -T -p 'read_rtlil original.il; script mutant.ys; check -assert; write_rtlil mutant.il' > mutant.log 2>&1
for label in fixed mutant;do
 cat > "$label.formal.ys" <<EOT
read_rtlil original.il
rename top gold
read_rtlil -overwrite $label.il
rename top gate
read_verilog miter.sv
hierarchy -top miter
flatten
async2sync
opt_clean
sat -seq 4 -set-init-zero -prove trigger 0 -verify
EOT
 rc=0;yosys -Q -T -s "$label.formal.ys" > "$label.formal.log" 2>&1 || rc=$?
 echo "$label formal_rc=$rc"
 if [ "$label" = fixed ];then [ "$rc" = 0 ];grep -q 'SUCCESS' "$label.formal.log";else [ "$rc" != 0 ];grep -q 'proof did fail' "$label.formal.log";fi
done
echo RESET_MULTIBIT_REAL_YOSYS_PASS
