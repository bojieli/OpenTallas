exec(open('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030/loads.py').read().split('jobs=compile_jobs(')[0])
from layer_prog.entry_load_calendar import check_page
routes={(r['slice'],r['leaf']):r for r in t['leaves']};stages={p:bc.local('u_seqhost','calendar_command_to_'+p)['edges']for p in('vo_n','vo_s')}
paths=list((R/'load_pages_L14').glob('job*.json'))
for path in paths:
 j=read(path)
 for r in j['load_dates']:
  sid=die.slices()[r['slice']]['sid'];offset=stages['vo_n'if sid&1 else'vo_s']+c['paths'][r['slice']]['xr_command_pin_edge']+routes[(r['slice'],r['leaf'])]['command_transport_edges']
  r['issuer_to_vp_command_input_edges']=offset
 check_page(j);path.write_text(json.dumps(j,indent=1)+'\n')
controls=[]
def refuse(name,j):
 try:check_page(j)
 except ValueError:controls.append(name)
 else:raise AssertionError('control escaped '+name)
J=read(paths[0]);j=copy.deepcopy(J);j['load_dates'][0]['vp_command_input_edge']-=1;refuse('wrong_bound_arrival_age',j)
j=copy.deepcopy(J);ti=j['commands'][-1]['template'];j['templates'][ti]['payload186']='0';refuse('wrong_GAIN_source_payload',j)
q=read(R/'entry_loads_L14.json');q['controls_caught']+=controls;q['independent_exact_route_recheck_pages']=len(paths)
(R/'entry_loads_L14.json').write_text(json.dumps(q,indent=2)+'\n');print('LOADS_EXACT_ROUTE_CHECK',len(paths),'PASS',controls)
