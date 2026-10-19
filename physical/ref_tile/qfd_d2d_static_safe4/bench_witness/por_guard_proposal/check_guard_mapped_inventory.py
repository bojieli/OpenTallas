import json,collections,csv,re,hashlib,gzip
from pathlib import Path
p=Path(__file__).parent;m=json.load(open(p/'guard_mapped31.json'))['modules']['qw_por_root_guard_proposal'];cc=collections.Counter(c['type'] for c in m['cells'].values());lef=(p/'guard_actual_std.lef').read_text() if (p/'guard_actual_std.lef').exists() else gzip.open(p/'guard_actual_std.lef.gz','rt').read();A={}
for v in re.finditer(r'^MACRO (\S+)\n(.*?)^END \1\s*$',lef,re.M|re.S):
 wh=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',v[2]);A[v[1]]=float(wh[1])*float(wh[2])
loads=collections.Counter();drivers={}
for n,c in m['cells'].items():
 for pin,bits in c['connections'].items():
  for bit in bits:
   if c['port_directions'][pin]=='input':loads[bit]+=1
   elif isinstance(bit,int):drivers[bit]=n+'/'+pin
for n,c in m['ports'].items():
 if c['direction']=='output':
  for b in c['bits']:loads[b]+=1
 else:
  for b in c['bits']:drivers[b]='PORT:'+n
r={'adoption':False,'FLUSH31_is_diagnostic_not_production_choice':True,'mapped_inventory':{k:{'count':v,'LEF_area_each_um2':A[k]} for k,v in cc.items()},'actual_LEF_area_um2':sum(A[k]*v for k,v in cc.items()),'sequential_FF_count':sum(v for k,v in cc.items() if k.startswith('DFF')),'comb_count':sum(v for k,v in cc.items() if not k.startswith('DFF')),'native_clock_loads':loads[m['ports']['ck']['bits'][0]],'POR_loads':loads[m['ports']['por_n']['bits'][0]],'max_actual_driver_terminal_load':max(c for b,c in loads.items() if isinstance(b,int)),'drivers_over16':{drivers.get(b,str(b)):c for b,c in loads.items() if isinstance(b,int) and c>16},'source_LEF_sha256':hashlib.sha256(lef.encode()).hexdigest(),'scope':'Mapped source proposal only; no placement/RC/nativephase/route/producerobserver joins. Actual-driver count excludes constants.'}
assert all(c['connections']['CLK']==m['ports']['ck']['bits'] and c['connections']['RESETN']==m['ports']['por_n']['bits'] and c['connections']['SETN']==['1'] for c in m['cells'].values() if c['type'].startswith('DFF'))
r['all_six_FFs_same_root_clock_POR_async_clear_preset_inactive']=True
(p/'guard_mapped31_inventory.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
