import json,pathlib,collections
P=pathlib.Path(__file__).parent;models=json.load(open(P/'full_scope_model.json'));old=json.load(open(P/'integrated_inputs/model.json'));sources=json.load(open(P/'integrated_inputs/source_bound_with_native_CQ.json'));resets=json.load(open(P/'integrated_inputs/integrated_model.json'));newplans={r['endpoint']:r for r in models['plans']};nandnames={next(z for z in c['native_pins'] if z['direction']=='output')['cell']:n for n,c in old['typed_cones'].items() if any(z['direction']=='output' and z['master'].startswith('NAND') for z in c['native_pins'])};out=[]
for co in ['TT','FF']:
 cq={r['source']['pin']:r['new_ff']['range_ps'] for r in sources[co]['boundary_sources']}
 for net,z in sources[co]['changed_cones'].items():
  for r in z['sources']:cq[r['source']['pin']]=r['new_ff']['range_ps'] if z['old_master'].startswith('NAND') else resets[co]['reset'][net]['new_source_ff']
 for role in ['data','async']:
  for delay in ['min','max']:
   for edge in ['rise','fall']:
    a=json.load(open(P/f'{co}_{role}_internal_{delay}_{edge}.json'))['checks']
    for z in a:
     changes=[];source=z['startpoint'];oldcq=(z['source_path'][0]['arrival']-z['source_clock_path'][-1]['arrival'])*1e12
     delta=0
     if source in cq:
      rr=cq[source];delta=(min(rr['cell_rise'][0],rr['cell_fall'][0]) if delay=='min' else max(rr['cell_rise'][1],rr['cell_fall'][1]))-oldcq;changes.append(dict(role='source_CQ',pin=source,delta_ps=delta))
     for point in z['source_path']:
      if point['instance'] in nandnames and point['pin'].endswith('/Y'):
       net=nandnames[point['instance']];g=sources[co]['changed_cones'][net];newg=g['new_gate']['range_ps'];oldpts=[p for p in z['source_path'] if p['instance']==point['instance'] and not p['pin'].endswith('/Y')];og=(point['arrival']-oldpts[-1]['arrival'])*1e12
       dg=(min(newg['cell_rise'][0],newg['cell_fall'][0]) if delay=='min' else max(newg['cell_rise'][1],newg['cell_fall'][1]))-og;delta+=dg;changes.append(dict(role='NAND_gate',net=net,delta_ps=dg))
     if not changes:continue
     value=z['slack']*1e12+(delta if delay=='min' else -delta)
     plan=newplans.get(z['endpoint']);scope='UNCHANGED_ENDPOINT_WITH_CHANGED_SOURCE' if not plan else 'IN_NEW_CHAIN_PLAN'
     out.append(dict(corner=co,role=role,delay=delay,edge=edge,startpoint=source,endpoint=z['endpoint'],baseline_slack_ps=z['slack']*1e12,matching_changes=changes,conditional_source_only_margin_ps=value,scope=scope))
json.dump(dict(schema='int8.changed_source.all_native_paths.v1',scope='Full actual native internal D/async path census matched by source pin and NAND arc identity; no aggregate CQ bound substituted. New chain bounds elsewhere; six inherited reset chains retained separately; changed output IO remains parent-reference unqualified.',rows=out),open(P/'all_changed_source_paths.json','w'),indent=2)
for co in ['TT','FF']:
 for de in ['min','max']:
  a=[r for r in out if r['corner']==co and r['delay']==de and r['role']=='data'];print(co,de,'matched_rows',len(a),'minimum_source_only',min((r['conditional_source_only_margin_ps'] for r in a),default=None),'outside_chain_rows',sum(r['scope'].startswith('UNCHANGED') for r in a))
