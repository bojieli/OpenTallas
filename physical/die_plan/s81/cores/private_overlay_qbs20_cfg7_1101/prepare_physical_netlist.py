#!/usr/bin/env python3
from pathlib import Path
import ast,re,json,hashlib,sys
k=Path(sys.argv[1]);base=k/'run/results/asap7/dp_col_h10_r0_p4__t1/base';source=base/'1_2_yosys.v';s=source.read_text()
ns=dict(ast=ast,re=re,Path=Path,json=json)
helper=(Path(__file__).parent/'parameter_helper_source.py').read_text()
for n in ast.parse(helper).body:
 if isinstance(n,ast.FunctionDef) and n.name in {'_mask','_close','_integer'}:exec(compile(ast.Module(body=[n],type_ignores=[]),'<fixedparam>','exec'),ns)
mask=ns['_mask'](s)
ledger=json.load(open(k/'native_parameter_binding.json'));expected={x['master']:x['params'] for x in ledger['checks']}
bf=json.load(open(k/'bf_wrapper_parameters.json'));expected['ot_v41_bf_col']=bf['fixed_route_params']
top=(k/'rtl/s81p_col_h10_r0_p4__t1.sv').read_text();identities=dict(re.findall(r'\.(P_\w+_INSTANCE)\("([^"]*)"\)',top))
edits=[];records=[]
for mod,want in expected.items():
 for m in re.finditer(r'\b'+re.escape(mod)+r'\s*(#\s*\()',mask):
  start=mask.index('(',m.start(1));end=ns['_close'](mask,start);raw=s[start+1:end-1];argmask=mask[start+1:end-1]
  cell=re.match(r'\s*(\\\S+|\w+)\s*\(',s[end:])[1].lstrip('\\');got={};pos=0
  while pos<len(argmask):
   hit=re.match(r'\s*,?\s*\.(\w+)\s*\(',argmask[pos:]);assert hit,(mod,raw[pos:])
   a=pos+hit.end()-1;b=ns['_close'](argmask,a);text=raw[a+1:b-1].strip();name=hit[1]
   if name=='INSTANCE':
    v=ast.literal_eval(text) if text else chr(0)[:0];assert isinstance(v,str)
    if mod=='ot_v41_rom_elem_q_qxpq_w10_gb':
     key='P_'+cell.removeprefix('u_bound.u_')+'_INSTANCE';assert v==identities[key],(cell,v,key)
    else:assert v=='',(cell,v)
   elif name=='MB':
    v=ns['_integer'](text,{});assert mod=='ot_v41_bf_col' and v in [0,1]
   else:
    v=ns['_integer'](text,{});assert name in want and v==want[name],(mod,cell,name,v,want)
   got[name]=v;pos=b
   if not argmask[pos:].strip():break
  assert got,(mod,cell)
  edits.append((m.start(1),end));records.append(dict(master=mod,instance=cell,validated_parameters=got))
assert records,'no qualified parameter blocks found'
out=s
for a,b in sorted(edits,reverse=True):out=out[:a]+out[b:]
target=base/'1_2_yosys_physical.v';target.write_text(out)
receipt=dict(scope='PREPARED only: selected fixed hard-macro physical import removes validated decorations; originalsource/netlist unchanged',source=str(source),source_sha256=hashlib.sha256(s.encode()).hexdigest(),target=str(target),target_sha256=hashlib.sha256(out.encode()).hexdigest(),normalized_cells=records)
(k/'physical_netlist_parameter_candidate.json').write_text(json.dumps(receipt,indent=2));print('PREPARED',len(records),'qualified cell parameter lists; no active netlist overwritten')

