import sys,json,hashlib,gzip
from pathlib import Path
from collections import Counter
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'tools/closure_loop'));import safe_source_contract as S
out=root/('evidence_native_v3' if len(sys.argv)>2 else 'evidence_native_v2');rawpath=out/'raw.json';raw=json.loads(rawpath.read_text());top='ot_pg_canonical_xor16_1019';mod=raw['modules'][top];pg=[]
for name,c in mod['cells'].items():
 pins=raw['native_master_pins'][c['type']]
 S.require(set(c['connections'])==set(c['port_directions'])==set(c['pin_signal_types'])==set(pins),'complete native master/ITerm inventory '+name)
 for pin in list(c['connections']):
  S.require(c['pin_signal_types'][pin]==pins[pin]['signal_type'] and c['port_directions'][pin]==pins[pin]['direction'],'native role mismatch')
  if pins[pin]['signal_type'] in ('POWER','GROUND'):
   pg.append(dict(instance=name,pin=pin,role=pins[pin]['signal_type'],connections=c['connections'][pin]))
   del c['connections'][pin];del c['port_directions'][pin]
for name,p in list(mod['ports'].items()):
 if p['signal_type'] in ('POWER','GROUND'):del mod['ports'][name]
libs=sorted((out/'libs_TT').glob('*.lib*'));used={c['type'] for c in mod['cells'].values()};native=S.native_cells(libs,used_masters=used);r=S.census(raw,top,native)
r['native_pg_inventory']=pg;r['provenance']={'raw_sha256':S.sha(rawpath),'source_odb_sha256':raw['source_odb_sha256'],'collector_sha256':S.sha(S.__file__),'parser_sha256':S.sha(root/'tools/dft/liberty.py'),'libs':[{"path":str(p),"sha256":S.sha(p)} for p in libs]}
with gzip.open(out/'census.json.gz','wt')as f:json.dump(r,f)
summary={k:v for k,v in r.items() if k not in ('drivers','input_registration','output_ownership','native_pg_inventory')};summary['native_pg_term_count']=len(pg)
summary['violating_drivers']=[x for x in r['drivers'] if x['driver'] in r['violations']]
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
clock={}
for corner in ['TT','FF','SS']:
 ln=S.native_cells([(out/('libs_'+corner)/n) for n in [f'asap7sc7p5t_AO_RVT_{corner}_nldm_211120.lib.gz',f'asap7sc7p5t_OA_RVT_{corner}_nldm_211120.lib.gz',f'asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz',f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib',f'asap7sc7p5t_SIMPLE_RVT_{corner}_nldm_211120.lib.gz']],used_masters=used);total=0;counts=Counter()
 for name,c in mod['cells'].items():
  cell=ln[c['type']];counts[cell['role']]+=1
  for pin,info in cell['pins'].items():
   if info['role']=='clock':
    total+=float(info['native_capacitance']['capacitance'])
 clock[corner]={'cell_roles':dict(counts),'clock_capacitance_native_units':total,'capacitive_load_unit':next(info['capacitance_unit'] for cell in ln.values() for info in cell['pins'].values() if info['role']=='clock')}
(out/'clock_cost.json').write_text(json.dumps(clock,indent=2)+'\n');print(json.dumps(summary));S.require(r['verdict']=='PASS','strict native census failed')
