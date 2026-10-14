import re,json,sys
from pathlib import Path
import signoff_analysis as S
actual=Path('6_final_canonical.v').read_text();
if int(sys.argv[1]):
 actual,n=re.subn(r'assign cut_5\s*=.*?;', 'assign cut_5 = 1\'b0;',actual);assert n==1,n
old=Path('eg_dut.sv').read_text();old,n=re.subn(r'module ot_smh_own_eg\b.*?endmodule',lambda _:actual,old,flags=re.S);assert n==1,n;Path('eg_dut.sv').write_text(old)
used=set(re.findall(r'^\s*([A-Z]\w*)\s+\S+\s*\(',actual,re.M))
physical={n for n in used if n.startswith(('DECAP','FILLER','TAPCELL'))}
for n in physical:
 for body in re.findall(r'^\s*'+re.escape(n)+r'\s+\S+\s*\((.*?)\);',actual,re.M|re.S):
  assert not body.strip(),(n,body)
r=S.write_cell_models([Path('../'+x+'.lib') for x in ['SEQ','AO','OA','SIMPLE','INVBUF']],Path('cell_models.sv'),used-physical);assert not r['missing'] and not r['skipped'],r
r['physical_only_zero_signal_port_stubs']=sorted(physical)
with open('cell_models.sv','a') as f:
 for n in sorted(physical):f.write('module '+n+'(); endmodule\n')
Path('cell_models.json').write_text(json.dumps(r,indent=2)+'\n')
