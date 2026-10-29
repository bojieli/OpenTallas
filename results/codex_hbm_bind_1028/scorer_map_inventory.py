"""Inventory actual scorerleaf paths versus existing plannedHCOL/tail locations; no placement invented."""
from pathlib import Path
import sys,json,collections
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'));import bind_elab as E
abp,planp,out=map(Path,sys.argv[1:4]);ab=json.loads(abp.read_text());p=json.loads(planp.read_text());F=E.flatten(ab,ab.get('top','hbm_current_native_top')) if 'cells' in ab else E.flatten(ab,'hbm_current_native_top')
actual=[];counts=collections.Counter()
for c in F.cells:
 if not c.path.startswith('hb_idx__s_'):continue
 counts[c.module]+=1
 if not c.module.startswith('$'):actual.append(dict(path=c.path,module=c.module,params=c.params,port_widths={k:len(v) for k,v in c.ports.items()},identity_source={k:v for k,v in c.ports.items() if k in ('hid4','cs_in','cf_in')}))
planned=[]
for pp in p['partitions']:
 t=p['partition_types'][pp['type']]
 for h in t.get('hard_cores',[]):
  if 'hb_idx__s_' in h['inst']:planned.append(dict(partition=pp['name'],type=pp['type'],inst=h['inst'],module=h['module'],origin=h['origin_um'],outline=h['outline_um']))
rec=dict(actual_leaves=actual,module_counts=dict(counts),planned=planned);out.write_text(json.dumps(rec,indent=2)+'\n');print('actualnamed',len(actual),'planned',len(planned),dict(counts.most_common(8)));print('\n'.join(str(r)[:200] for r in actual[:20]))
