from pathlib import Path
import json,re,hashlib,sys,collections
sys.path.insert(0,str(Path('tools/hier_contract').resolve()))
import pinreg_audit as A
import child_lint as L
R=Path('physical/s81_engc_tiles/rso_views'); D=Path('physical/s81_engc_tiles/compose/gate/records/rso_children_d097')
for kind,name in [('pbb','ot_engc_t_pbb_rso_xt')]:
 v=R/name; ins=json.loads((v/'insertion.json').read_text()); (v/'insertion.json').write_text(json.dumps(ins,indent=2)+'\n')
 libs={c:A.parse_lib(v/(name+'_'+c+'.lib')) for c in ['tt','ff','ss']}; pins=libs['tt']['pins']; lef=L.parse_lef((v/(name+'.lef')).read_text()); power={n for n,p in lef['pins'].items() if p.get('use') in ('POWER','GROUND')}
 assert all(set(l['pins'])==set(pins) and l['cell']==name for l in libs.values())
 groups=collections.defaultdict(list)
 for n,p in pins.items():
  if n in power:continue
  m=re.fullmatch(r'(\w+)\[(\d+)\]',n)
  groups[m[1] if m else n].append((int(m[2]) if m else None,p['dir'],n))
 ports=[]
 for base,items in sorted(groups.items()):
  dirs={x[1] for x in items};assert len(dirs)==1
  indices=[x[0] for x in items if x[0] is not None]
  if indices:
   assert len(indices)==len(items) and set(indices)==set(range(max(indices)+1)); width=f'[{max(indices)}:0] '
  else:assert len(items)==1;width=''
  ports.append('    '+next(iter(dirs))+' wire '+width+base)
 bb=v/(name+'_bb.sv');bb.write_text('// Physical symbol derived from actual matching TT/FF/SS ETM pins.\n// Use source RTL for simulation; native slot/source binding remains open.\n(* blackbox, keep_hierarchy *) module '+name+' (\n'+',\n'.join(ports)+'\n);\nendmodule\n')
 packet={'schema':'opentallas.engram.source0.per_pin_endpoint_prices.v1','native_admission':False,'exact_export_context':'Chosen final ODB/SPEF/source0 serialized SDC; scalar ETM export entries at original root slew/default driver and output-load context. Native driver/load binding is separate.','corners':{},'physical_symbol':{'file':bb.name,'sha256':hashlib.sha256(bb.read_bytes()).hexdigest(),'signal_pin_count':len(pins)-len(power),'power_pins':sorted(power)}}
 for c,lib in libs.items():
  mean=ins[c]['boundary']['mean']; refs={'ck':{'rise':mean,'fall':mean}}
  metrics=A.pin_metrics(lib,refs)
  packet['corners'][c]={'lib_sha256':hashlib.sha256((v/(name+'_'+c+'.lib')).read_bytes()).hexdigest(),'boundary_reference':ins[c]['boundary'],'pins':metrics,'reset_port_classification':{'rst':'asynchronous reset input; exported setup_rising/hold_rising includes recovery/removal and must remain separate from ordinary data. IO also directly resets command-side endpoint controls; raw finalDB reports bind exact endpoint roles.'}}
  print(name,c,'normalized maxO',max((x['out'] for x in metrics.values() if x['out'] is not None),default=None),'maxS',max((x['inp'] for x in metrics.values() if x['inp'] is not None),default=None))
 (v/'source0_endpoint_prices.json').write_text(json.dumps(packet,indent=2)+'\n')
