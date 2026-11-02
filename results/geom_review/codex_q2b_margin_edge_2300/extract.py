from pathlib import Path
import json,re
p=Path('/srv/opentallas-scratch2/claude/codex-kv-q2-1131/forceB/run/results/asap7/hc_qkd_ectlk_q2__233_28x172_8/base/6_final.def')
want={'codex_q2_force_B_312020','net11317'};out={'components':[],'nets':{},'clock_m3_near_south':[],'clock_records':0};section=None;record=''
for line in p.open():
 s=line.strip()
 if s.startswith('COMPONENTS '):section='components'
 if s.startswith('NETS '):section='nets'
 if s.startswith('END COMPONENTS') or s.startswith('END NETS'):section=None
 if not section:continue
 if s.startswith('- '):record=s
 elif record:record+=' '+s
 if record and record.endswith(';'):
  if section=='components':
   n=record.split()[1]
   if 'codex_q2_force_B_4_buf' in n or (record.split()[2]=='ot_sram_1r1w_128x256_m1_r2c2' and '.u_a.' in n):out['components'].append(record)
  else:
   name=record.split()[1]
   if name in want or 'codex_q2_force_B_4_buf' in record:out['nets'][name]=record
   if '+ USE CLOCK' in record:
    out['clock_records']+=1
    for path in re.findall(r'(?:ROUTED|NEW) M3\b(.*?)(?= NEW | \+ |;|$)',record):
     pts=re.findall(r'\(\s*([\d*]+)\s+([\d*]+)\s*\)',path);xx=yy=None
     previous=None
     for x,y in pts:
      xx=xx if x=='*' else int(x);yy=yy if y=='*' else int(y)
      if previous and xx is not None and yy is not None:
       ax,ay=previous
       if max(ax,xx)>=15120 and min(ax,xx)<=109944 and max(ay,yy)>=13160 and min(ay,yy)<=13320:out['clock_m3_near_south'].append({'net':name,'segment':[previous,[xx,yy]]})
      previous=[xx,yy]
  record=''
q=Path('/srv/opentallas-scratch2/claude/codex-kv-q2-1131/codex_prep2252.json');q.write_text(json.dumps(out,indent=2));print('components',len(out['components']),'nets',len(out['nets']),'clockpoints',len(out['clock_m3_near_south']))
