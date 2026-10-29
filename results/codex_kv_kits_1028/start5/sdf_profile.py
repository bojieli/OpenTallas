import re,json,sys
from pathlib import Path
base=Path(sys.argv[1]); out=Path(sys.argv[2]); stages=json.load(open(out/'emitted/start_stages.json'))['stages']
num=r'\(([-+\deE.]+)::([-+\deE.]+)\)'
profiles={}
for corner in ['TT','FF']:
 s=(base/f'out_fb_inv_r150_{corner}/die_{corner}.sdf').read_text()
 wires={m[2]:(m[1],tuple(map(float,m.groups()[2:4])),tuple(map(float,m.groups()[4:6]))) for m in re.finditer(r'\(INTERCONNECT\s+(\S+)\s+(\S+)\s+'+num+r'\s+'+num+r'\)',s)}
 cells={}
 for m in re.finditer(r'\(CELLTYPE "([^"]+)"\)\s+\(INSTANCE (ck_\w+)\)\s+\(DELAY\s+\(ABSOLUTE\s+\(IOPATH A Y\s+'+num+r'\s+'+num,s):
  cells[m[2]]=(m[1],tuple(map(float,m.groups()[2:4])),tuple(map(float,m.groups()[4:6])))
 cache={'root':((0.,0.),(0.,0.))}
 def add(a,b):return tuple(x+y for x,y in zip(a,b))
 def arrival(pin):
  if pin in cache:return cache[pin]
  if pin in wires:
   src,rd,fd=wires[pin];r,f=arrival(src);v=add(r,rd),add(f,fd)
  else:
   cell,port=pin.split('/');assert port=='Y',pin
   typ,rd,fd=cells[cell];r,f=arrival(cell+'/A')
   if 'INV' in typ:r,f=f,r
   v=add(r,rd),add(f,fd)
  cache[pin]=v;return v
 rows=[]
 for st in stages:
  pin='ck_'+st['node_cell']+'/'+st['clock_from'];r,f=arrival(pin)
  rows.append(dict(clock_port=st['clock_port'],region=st['region'],physical_pin=pin,rise_early_ps=r[0],rise_late_ps=r[1],fall_early_ps=f[0],fall_late_ps=f[1],edge_fall=st['edge_fall']))
 profiles[corner]=rows
 print(corner,'wires',len(wires),'cells',len(cells),'stages',len(rows))
 # Corroborate cumulative SDF Y rise with the actual raw STA report (rounding only).
 raw={x.split()[1]:float(x.split()[2]) for x in (base/f'out_fb_inv_r150_{corner}/arr_{corner}.txt').read_text().splitlines() if x.startswith('N ')}
 diffs=[arrival('ck_'+st['node_cell']+'/Y')[0][1]-raw[st['node_cell']] for st in stages]
 print('SDF-vs-STA rise late diff ps',min(diffs),max(diffs))
 profiles[corner+'_sdf_vs_sta_rise_late_ps']={'min':min(diffs),'max':max(diffs)}
json.dump(dict(form='bind5_actual_clock_sdf_path_profile',source=str(base),basis='actual unique clock-tree SDF interconnect+cell arcs; TT/FF min/max rise/fall propagated with physical inverter polarity; no guessed delays',physical_timing='nominal functional fixture only; no added provider load or stage-pin route included',profiles=profiles),open(out/'phase_profile.json','w'),indent=1)
