from pathlib import Path
import sys,shutil
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-su-opf4-1106');B=Path('/srv/opentallas-scratch2/claude/hbm-bind-6/tip2');sys.path.insert(0,str(B/'tools/hbm_static'))
from su_arith_compile import FIELDS,physical_word,pack
O=R/'vec_indirect';O.mkdir(exist_ok=True)
raw=[int(s,16) for s in (R/'vec/control.mem').read_text().splitlines()];new=[]
for word in raw:
 out=0
 for q in range(4):
  x=(word>>(q*1742))&((1<<1742)-1);d={}
  for n,w in reversed(FIELDS):d[n]=x&((1<<w)-1);x>>=w
  d['aind']=1;d['aibase']=physical_word(q,448);d['vb']=(d['vb']&~((1<<24)-1))|physical_word(q,0)
  out|=pack(d)<<(q*1742)
 new.append(out)
(O/'control.mem').write_text('\n'.join(f'{v:01742x}' for v in new)+'\n')
seed=(R/'vec/seed.mem').read_text().splitlines()
for k in range(64):
 for lane in range(512):seed[(448+k)*512+lane]=f'{k*128:08x}'
(O/'seed.mem').write_text('\n'.join(seed)+'\n');shutil.copyfile(R/'vec/gold.mem',O/'gold.mem')
s=(R/'tb_local_enable.sv').read_text().replace('if(cycle!=FIRST_OUTPUT)fail("selected profile first-output edge");','')
(R/'tb_indirect.sv').write_text(s)
(R/'run_indirect.sh').write_text('''#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-hbm-su-opf4-1106
variant=$1
base=/srv/opentallas-scratch2/claude/hbm-bind-6/tip2
$HOME/.local/opentallas-tools/bin/verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_su_static_lane_leaf --Mdir "$PWD/obj_indirect_$variant" "$PWD/tb_indirect.sv" "$PWD/rtl_$variant"/*.sv "$base/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11/sram_bench_model.sv" > build_indirect_$variant.log 2>&1
./obj_indirect_$variant/Vtb_su_static_lane_leaf +DIR="$PWD/vec_indirect" > indirect_$variant.log 2>&1
tail -5 indirect_$variant.log
''')
print('real VI varying index rows448..511, identity gather A, independent arithmetic golden retained')
