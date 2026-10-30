from pathlib import Path
import json
p=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336');out={'scope':'complete public E/M4 entry and actual ITerm leaf clock points; feed included once; pureNLDM design estimate, not signed STA','external_input_slew_ps':20,'types':{},'public_pin_audit':'impact/public_pin_table_audit.json'}
for k,old,count in [('nk',{'TT':665.8,'FF':576.5},720),('nl',{'TT':692.6,'FF':601.9},48)]:
 stem='nk_pin_flex_centres' if k=='nk' else 'nl_pin_w16_centres';s=json.load(open(p/'plans'/(stem+'.json')))['core_tree'];m=json.load(open(p/'natural_model'/(stem+'_model.json')));pairs=json.load(open(p/'natural_model'/(stem+'_pairs.json')));ls={l['node']:l for l in s['leaves']};q={'model':str(p/'natural_model'/(stem+'_model.json')),'plan':str(p/'plans'/(stem+'.json')),'cores':count,'clock_cells':len(s['nodes']),'public_ck':{'layer':'M4','xy_um':[457.824,668.076]},'entry_feed_included':True,'actual_clock_geometry_installed':(p/f'physical/{k}_pin_clock_install/clock_installed.odb').exists(), 'checkpoint':str(p/f'physical/{k}_pin_clock_install/clock_installed.odb'), 'source_geometry_qualified':True, 'clock_sink_points_source':json.load(open(p/'plans'/(stem+'.json')))['clock_sink_points_source'],'related_pair_qualified':all(v['over80']==0 for v in pairs['corners'].values()),'corners':{}}
 for c,mc in m['corners'].items():
  total=weight=0;values=[]
  for r in mc['leaf_means']:
   l=ls[r['node']];i=l.get('early_tap_ps',{}).get(c,{'min':0,'max':0});n=len(l['sinks']);mean=r['mean_ps']+(i['min']+i['max'])/2;total+=n*mean;weight+=n;values.append((r['min_ps']+i['min'],r['max_ps']+i['max']))
  mean=total/weight;q['corners'][c]={'effective_min_ps':min(v[0]for v in values),'effective_max_ps':max(v[1]for v in values),'weighted_mean_ps':mean,'old_percore_insertion_ps':old[c],'delta_from_old_percore_ps':mean-old[c],'slew_max_ps':mc['slew_max_ps'],'related_worst_ps':pairs['corners'][c]['worst_ps'],'related_over80':pairs['corners'][c]['over80'],'entry_wire_model':mc['entry_wire_model'], 'estimated_public_clock_cap_ff':mc['entry_wire_model']['input_cap_ff']+mc['entry_wire_model']['wire_um']*mc['entry_wire_model']['wire_c_ff_um']}
 out['types'][k.upper()]=q
json.dump(out,open(p/'impact/a0_public_clock_frames.json','w'),indent=2)
for k,r in out['types'].items():print(k,r['related_pair_qualified'],{c:{n:v for n,v in q.items()if n!='entry_wire_model'}for c,q in r['corners'].items()})
