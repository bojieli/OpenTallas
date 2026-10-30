#!/bin/bash
set -euo pipefail
w=/srv/opentallas-scratch2/claude/wt/codex-btab-fault-clone-1030
b=/srv/opentallas-scratch2/claude/codex-btab-fault-clone-1030
mkdir -p "$b"
yosys -Q -p "read_verilog -lib $w/rtl/test/btab_fault_clone/sram_bb.v; read_verilog -sv $w/rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv; hierarchy -top qfd_dv_s8x_btab -chparam MIF 1 -chparam FAULT_OUTPUT_CLONE 1; synth -top qfd_dv_s8x_btab; write_json $b/retained.json" >"$b/retention.log" 2>&1
python3 - "$b" <<'CHECK'
import json,sys
from pathlib import Path
b=Path(sys.argv[1]);d=json.load((b/'retained.json').open());top=d['modules']['qfd_dv_s8x_btab'];cs=top['cells'];names=[n for n in cs if 'g_fault_clone.u_' in n];assert len(names)==2,names
rows=[]
for n in names:
 c=cs[n];m=d['modules'][c['type']];ff=[x for x in m['cells'].values() if 'DFF' in x['type']];assert len(ff)==1,(n,ff);rows.append(dict(instance=n,type=c['type'],ports=c['connections'],flops=len(ff)))
assert rows[0]['type']!=rows[1]['type'];outs=[r for r in rows if r['instance'].endswith('u_output')];assert len(outs)==1 and outs[0]['ports']['q']==top['ports']['fault']['bits']
r=dict(status='GENERIC_SYNTH_RETENTION_ONLY; exact native mapped LEC/FACE+clock qualification still owed',added_flops=1,added_clock_loads=1,production_cycles=0,rows=rows)
(b/'retention.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
CHECK
