"""Read-only actual native zero-logic frontier vs frozen regional ownership."""
import csv,json,pathlib,collections,re
R=pathlib.Path(__file__).parent
graph=pathlib.Path('/srv/opentallas-scratch2/claude/codex-programme-native-frontier-0545/graph.tsv')
model=json.loads((R/'clock_model.json').read_text())
rows=list(csv.DictReader((R/'input/actual_FF_rows.csv').open()))
norm=lambda x:x.replace('\\','').strip()
xy={norm(x['cell']):(float(x['x_um']),float(x['y_um'])) for x in rows}
owner={model['sinks'][i]['instance']:j for j,r in enumerate(model['roots']) for i in r['sink_indices']}
cells={};drivers=collections.defaultdict(list)
for r in csv.DictReader(graph.open(),delimiter='\t'):
 if r['kind']!='ITERM':continue
 c=cells.setdefault(r['owner'],dict(master=r['master'],pins=[]));c['pins'].append(r)
 if r['io']=='OUTPUT' and r['signal'] not in ('POWER','GROUND') and r['net']:drivers[r['net']].append(r['owner'])
pred={};ambiguous=[]
for name,c in cells.items():
 if not c['master'].startswith('DFF'):continue
 d=[x for x in c['pins'] if x['pin']=='D']
 if len(d)!=1:raise RuntimeError(('actual D pin',name))
 drv=drivers[d[0]['net']]
 if len(drv)!=1:
  if drv:ambiguous.append([name,drv])
  continue
 source=drv[0];via=None
 if re.match(r'^(INV|BUF)',cells[source]['master']) and 'clk' not in source:
  ins=[p for p in cells[source]['pins'] if p['io']=='INPUT' and p['signal'] not in ('POWER','GROUND')]
  if len(ins)!=1:raise RuntimeError(('native BUF/INV inputs',source))
  upstream=drivers[ins[0]['net']]
  if len(upstream)!=1:continue
  via=source;source=upstream[0]
 if not cells[source]['master'].startswith('DFF') or source==name:continue
 a,b=norm(source),norm(name)
 assert a in owner and b in owner and a in xy and b in xy
 dist=abs(xy[a][0]-xy[b][0])+abs(xy[a][1]-xy[b][1])
 pred[name]=dict(launch=source,capture=name,via_BUF_INV=via,launch_region=owner[a],capture_region=owner[b],FF_centre_L1_um=dist)
cross=[p for p in pred.values() if p['launch_region']!=p['capture_region']]
near=[p for p in cross if p['FF_centre_L1_um']<=20+1e-6]
same_near=[p for p in pred.values() if p['launch_region']==p['capture_region'] and p['FF_centre_L1_um']<=20+1e-6]
out=dict(status='SOURCE_ONLY_F4_OWNERSHIP_FRONTIER',actual_FF=len(xy),actual_regional_roots=len(model['roots']),actual_direct_or_one_BUF_INV_FF_pairs=len(pred),cross_regional_pairs=len(cross),cross_regional_FF_centre_L1_le_20_candidates=len(near),same_regional_FF_centre_L1_le_20=len(same_near),ambiguous_driver_cases=ambiguous,near_cross_pairs=near,all_cross_pairs=cross,scope='Necessary integration frontier, not actual F4 moves or timing FAIL. Native F4 tests capture-to-actual-leaf-driver distance, chain size and added sinks after CTS; FF-centre20 is only a proximity screen. Its same_native_root traces to public clk, so32 private regional roots do not prevent crossing. No source/model/physical change or CAD.',required='Preserve regional ancestry after CTS/F4 or revise the actual model/census before adoption; do not silently transfer this geometry ownership to the legacy hook.')
(R/'f4_frontier.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k not in ('all_cross_pairs','near_cross_pairs')},indent=2))
