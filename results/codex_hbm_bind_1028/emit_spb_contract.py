"""Emit the actual selected SPB wrappers and scalar clock/reset connections only.

This is a scoped source contract, not whole-die closure. The original complete
source findings remain in the receipt. No route, STA, pin or timing is waived.
Usage: emit_spb_contract.py PLAN ASBUILT MANIFEST OUT
"""
import collections,hashlib,json,re,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'))
import bind as M
plan,asbuilt,manifest,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
p=json.loads(plan.read_text());ab=json.loads(manifest.read_text())
ab['reset_carrier_parts']=['NW_mca','NE_mca']
if ab.get('map_file') and not Path(ab['map_file']).is_absolute():ab['map_file']=str(manifest.parent/ab['map_file'])
p['asbuilt']=ab;b=M.Binder(p,json.loads(asbuilt.read_text()),plan.parent,ab['base'])
b.map_cells();b.analyse();b.build_buses();b.align_landings();b.uniform_inner();b.regen_params()
findings=list(b.errors);counts=dict(b.counts);parts=['NW_spb0','NE_spb0']
allmembers=b.members
# Exact existing type-signature and emitter on just the requested source parts.
# No source/crossing is removed from F/G/sinks, and no whole-die PASS is reported.
b.members={part:allmembers[part] for part in parts};b.check_types()
b._native_glue=None;b.io_used={};b.pnames={}
records=[]
for part in parts:
 tn=b.parts[part]['type'];text,pnames=b.emit_type(tn,part)
 path=out/(tn+'.sv');path.write_text(text)
 cores=[]
 for ci in b.members[part]:
  cell=b.F.cells[ci]
  if b.G.kind[ci]!='leaf':continue
  name=M.short_id('u_'+b.rel_of(ci),90)
  match=re.search(r'\b'+re.escape(name)+r'\s*\(\s*(.*?)\n\s*\);',text,re.S)
  if not match:raise ValueError('missing actual emitted source leaf '+cell.path)
  conns=dict(re.findall(r'\.(\w+)\(([^()]*)\)',match[1]))
  roles={}
  for pn,bits in cell.ports.items():
   if cell.dirs.get(pn)!='input':continue
   ds=[b.sinks[(ci,pn,i)] for i in range(len(bits))]
   if all(d[0] in ('clk','rst') for d in ds):
    if len(bits)!=1:raise ValueError('non-scalar source clock/reset '+cell.path+'.'+pn)
    expr=conns[pn]
    if '{' in expr or ',' in expr:raise ValueError('non-scalar emitted source clock/reset '+expr)
    roles[pn]=dict(width=1,kind=ds[0][0],source=list(ds[0]),bound_expression=expr)
  cores.append(dict(path=cell.path,module=cell.module,plan_instance=b.rel_of(ci),
                    emitted_instance=name,clock_reset=roles))
 records.append(dict(partition=part,type=tn,wrapper=b.types[tn]['module'],
                     rtl=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cores=cores))
rec=dict(schema='opentallas.hbm.bound_spb_contract.v1',parts=records,
         reset_carriers=b.reset_carriers,source_counts=counts,whole_source_errors=findings,
         scope='ACTUAL_SELECTED_RAW_BOUND_WRAPPERS_ONLY_NATIVE_SPB_ADAPTER_NOT_INSERTED',
         status='DIAGNOSTIC_NO_WHOLE_DIE_OR_PHYSICAL_PASS')
(out/'contract.json').write_text(json.dumps(rec,indent=2)+'\n')
print('SPB source contract',len(records),'wrappers; actual scalar core clock/reset; global findings',len(findings),flush=True)
