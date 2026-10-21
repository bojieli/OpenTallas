from pathlib import Path
import json,sys
base=Path('/srv/opentallas-scratch/claude/closure-loop/s81dvbk_hist32_b0r3-hb0r3-bd6f52e8c');sys.path.insert(0,str(base/'codex_native_audit/tools'));import textbook_lint as TL
p=next(base.glob('routes/*/work/orfs/results/asap7/*/base/6_final.v'));g,top=TL.flatten(TL.parse_verilog(p.read_text()),'ot_s81ph_native_sel_hist_bank');d=json.loads((base/'codex_native_audit/native_final.json').read_text())
for v in d['violations']:
 print('ROOT',v['driver'],'LOADS',v['loads'])
 for ci,pin,bit in v['endpoints'][:6]: print('END',g.cells[ci][0],g.cells[ci][1],pin,g.cells[ci][2])
