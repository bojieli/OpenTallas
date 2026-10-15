#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,'tools/s81_static_control')
from program import encode_program
rows=[dict(engine=i%13,arg=0x010203+i*0x001523,issue=i,done=i+3)for i in range(126)]
rows += [dict(engine=14,arg=0,issue=129,done=0),dict(engine=15,arg=0,issue=130,done=0)]
p=encode_program(rows,7,1)
base=encode_program([dict(engine=10,arg=11880,issue=4,done=7),dict(engine=15,arg=0,issue=10,done=0)],7,1)
Path('base_program.hex').write_text(''.join(f"{w['word']:09x}\n" for w in base['writes']))
Path('program.hex').write_text(''.join(f"{w['word']:09x}\n"for w in p['writes']))
w=encode_program([dict(engine=0,arg=0x102938,issue=0,done=3),dict(engine=11,arg=0xfa0312,issue=1,done=4),dict(engine=14,arg=0,issue=6,done=0),dict(engine=15,arg=0,issue=7,done=0)],7,0)
Path('wrapper.hex').write_text(''.join(f"{x['word']:09x}\n"for x in w['writes']))
PY
iverilog -g2012 -s tb_s81_fixed_issue -o sim rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv rtl/dsrom_sys/s81_static_control/test/tb_s81_fixed_issue.sv
for mode in 0 1 2 3 4 5 6 7 8 9;do vvp sim +mode="$mode";done
for mutant in 1 2;do
 iverilog -g2012 -DISSUER_MUT="$mutant" -s tb_s81_fixed_issue -o mutant rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv rtl/dsrom_sys/s81_static_control/test/tb_s81_fixed_issue.sv
 if vvp mutant +mode=0;then echo "ERROR: mutant $mutant escaped";exit 1;fi
done

iverilog -g2012 -s tb_s81_fixed_wrapper -o wrapper rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv rtl/dsrom_sys/s81_static_control/ot_s81_fixed_mailbox.sv rtl/dsrom_sys/s81_static_control/dsfd_stage_seq_static_c.sv rtl/dsrom_sys/s81_static_control/test/tb_s81_fixed_wrapper.sv
vvp wrapper +mode=0
vvp wrapper +mode=1

iverilog -g2012 -s tb_s81_fixed_issue_base -o base rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv rtl/dsrom_sys/s81_static_control/test/tb_s81_fixed_issue_base.sv
vvp base +mode=0
vvp base +mode=1
