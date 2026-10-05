import gzip,hashlib,json,re,sys
from decimal import Decimal as D
from pathlib import Path
sys.path.insert(0,'/src')
from tools.w10_liberty_event_energy import events
from tools.w10_q_power_envelope import coefficients
counts=json.load(open('/out/BF_raw_cell_counts.json'))['cell_counts'];needed=set(counts)-{'ot_rom_4096x274_m8'};out={};sources={}
for corner in ('SS','TT','FF'):
 for group,date in [('SIMPLE','211120'),('AO','211120'),('OA','211120'),('INVBUF','220122'),('SEQ','220123')]:
  p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')/f'asap7sc7p5t_{group}_RVT_{corner}_nldm_{date}.lib';p=p if p.exists() else Path(str(p)+'.gz');b=p.read_bytes();s=gzip.decompress(b).decode() if p.suffix=='.gz' else b.decode();sources[str(p)]=hashlib.sha256(b).hexdigest()
  for m in re.finditer(r'cell\s*\(([^)]*)\)\s*\{',s):
   name=m[1]
   if name not in needed:continue
   i=m.end();depth=1
   while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
   cell=s[m.start():i];fixed={'RESETN':True,'SETN':True} if name.startswith('DFFASR') else {}
   if name.startswith('TIE'):
    assert re.search(r'function\s*:\s*"[01]"',cell);energy=D(0);cap=D(0);output=D(0)
   else:
    ev=events(cell,name,fixed);energy=sum((D(v) for k,v in ev['event_cycle_fJ'].items() if k not in ('CLK','RESETN','SETN')),D(0));co=coefficients(cell,name,D('1e-12'))
    cap=sum((v['cap_fF'] for k,v in co['pins'].items() if v['direction']=='input' and k not in ('CLK','RESETN','SETN')),D(0));output=sum((v['max_cap_fF'] for v in co['pins'].values() if v['direction']=='output'),D(0))
   item=out.setdefault(name,{'data_cycle_energy_fJ':D(0),'nonclock_pin_cap_fF':D(0),'output_load_ceiling_fF':D(0)})
   for k,val in [('data_cycle_energy_fJ',energy),('nonclock_pin_cap_fF',cap),('output_load_ceiling_fF',output)]:item[k]=max(item[k],val)
assert set(out)==needed,needed-set(out)
Path('/out/BF_data_coefficients.json').write_text(json.dumps({'source_image':'af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34','source_sha256':sources,'coefficients':{n:{k:str(v) for k,v in x.items()} for n,x in sorted(out.items())},'scope':'Compatible when-state SS/TT/FF actual cell data-event maxima, warm reset-deasserted; not actual activity/RC'},indent=2)+'\n')
