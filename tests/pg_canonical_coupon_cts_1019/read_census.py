from pathlib import Path
import sys,json,copy,gzip
root=Path.cwd();out=root/'output/default/analysis'
sys.path.insert(0,str(root/'tools/closure_loop'));import safe_source_contract as S
raw=json.loads((out/'raw.json').read_text());top='ot_pg_canonical_xor16_1019';mod=raw['modules'][top]
for name,c in mod['cells'].items():
 master=raw['native_master_pins'][c['type']]
 S.require(set(master)==set(c['connections'])==set(c['port_directions'])==set(c['pin_signal_types']),'complete master/ITerm '+name)
 for pin in list(c['connections']):
  S.require(c['pin_signal_types'][pin]==master[pin]['signal_type'],'native role '+name+'/'+pin)
  if master[pin]['signal_type'] in ('POWER','GROUND'):del c['connections'][pin];del c['port_directions'][pin]
for name,p in list(mod['ports'].items()):
 if p['signal_type'] in ('POWER','GROUND'):del mod['ports'][name]
used={c['type'] for c in mod['cells'].values()}
libs=[out/'libs'/n for n in ['asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz','asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz','asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz','asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib','asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz']]
native=S.native_cells(libs,used_masters=used);r=S.census(raw,top,native)
with gzip.open(out/'census.json.gz','wt') as f:json.dump(r,f)
print(json.dumps({k:v for k,v in r.items() if k not in ('drivers','input_registration','output_ownership')}))
(out/'census_summary.json').write_text(json.dumps({k:v for k,v in r.items() if k not in ('drivers','input_registration','output_ownership')},indent=2)+'\n')
