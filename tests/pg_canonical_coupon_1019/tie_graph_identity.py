from pathlib import Path
import json
p=Path(__file__).resolve().parent
a=json.loads((p/'evidence_native_v2/raw.json').read_text())
b=json.loads((p/'evidence_native_v3/raw.json').read_text())
top='ot_pg_canonical_xor16_1019'
def graph(r):
 m=r['modules'][top];dr={};cells={};loads={}
 for n,x in m['ports'].items():
  if x['direction']=='input':dr[tuple(x['bits'])]=('port',n)
 for n,x in m['cells'].items():
  # Actual used native TIEHI/H function1 was verified by strict native Liberty.
  static=x['type']=='TIEHIx1_ASAP7_75t_R'
  if not static:cells[n]=(x['type'],x['port_directions'],x['pin_signal_types'])
  for pin,bs in x['connections'].items():
   if x['port_directions'][pin]=='output':
    key=tuple(bs);assert key not in dr
    dr[key]=('constant',1) if static else ('cell',n,pin)
 for n,x in m['cells'].items():
  for pin,bs in x['connections'].items():
   if x['pin_signal_types'][pin] not in ('POWER','GROUND') and x['port_directions'][pin]=='input':
    loads[(n,pin)]=dr[tuple(bs)]
 for n,x in m['ports'].items():
  if x['direction']=='output':loads[('port',n)]=dr[tuple(x['bits'])]
 return cells,loads
x=graph(a);y=graph(b);assert x==y
r={'verdict':'PASS','scope':'exact nonstatic nativecell/pin identities and all input/output direct-source relationships, treating actual TIEHI H function1 as constants','nonstatic_cells':len(x[0]),'input_and_output_relationships':len(x[1]),'FF_state_edges_added':0,'physical_pg_equivalence':'not_claimed;all276unbound at synthesis','actual_source_odb_sha256':a['source_odb_sha256'],'copied_tie_odb_sha256':b['source_odb_sha256']}
(p/'evidence_native_v3/tie_signal_graph_identity.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
