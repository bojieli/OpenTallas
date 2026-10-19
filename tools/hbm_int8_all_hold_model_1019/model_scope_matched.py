import json,pathlib,gzip,re,itertools,collections
from lib_native import blocks,scalar,vec,interp,ranges
P=pathlib.Path(__file__).parent;B=pathlib.Path('/srv/opentallas-scratch/claude/hbm-int8-cts-v2-run-1019');a=json.load(open(P/'typed_lowmargin_manifest.json'));out={}
for co in ['TT','FF']:
 lib={}
 for f in (B/'input/native_libs').glob('*'+co+'*.lib*'):
  s=gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()
  for name,b in blocks(s,'cell'):
   pins=dict(blocks(b,'pin'));op=pins.get('Y',pins.get('QN',''));tabs={}
   for k in ['cell_rise','cell_fall','rise_transition','fall_transition']:
    z=list(blocks(op,k))
    if z:tabs[k]={'x':vec(z[0][1],'index_1'),'y':vec(z[0][1],'index_2'),'v':vec(z[0][1],'values')}
   caps={n:[min(z),max(z)] for n,pb in pins.items() if (z:=[scalar(pb,k) for k in ['capacitance','rise_capacitance','fall_capacitance'] if scalar(pb,k) is not None])}
   checks=[]
   for pn in ['D','RESETN','SETN']:
    for _,t in blocks(pins.get(pn,''),'timing'):
     ty=re.search(r'timing_type\s*:\s*(\w+)',t);when=re.search(r'when\s*:\s*"([^"]*)"',t)
     if not ty or ty[1] not in ['hold_rising','setup_rising','removal_rising','recovery_rising']:continue
     for k in ['rise_constraint','fall_constraint']:
      for _,z in blocks(t,k):checks.append(dict(pin=pn,type=ty[1],edge=k,when=when[1] if when else None,x=vec(z,'index_1'),y=vec(z,'index_2'),v=vec(z,'values')))
   lib[name]=dict(area=scalar(b,'area'),caps=caps,tables=tabs,checks=checks)
 hb=lib['HB4xp67_ASAP7_75t_R'];cases={}
 for master,pin in [('DFFHQNx1_ASAP7_75t_R','D'),('DFFASRHQNx1_ASAP7_75t_R','D'),('DFFASRHQNx1_ASAP7_75t_R','RESETN')]:
  wave=[5,120];total=[0.,0.];stages=[]
  for i in range(3):
   cap=hb['caps']['A'] if i<2 else lib[master]['caps'][pin];load=[cap[0],cap[1]+.5];z=ranges(hb,wave,load);total=[total[0]+min(z[k][0] for k in ['cell_rise','cell_fall']),total[1]+max(z[k][1] for k in ['cell_rise','cell_fall'])];wave=[min(z[k][0] for k in ['rise_transition','fall_transition']),max(z[k][1] for k in ['rise_transition','fall_transition'])+5];stages.append(dict(input_cap_range_ff=load,native=z,output_waveform_ps=wave))
  final=[wave[0],wave[1]+20];checks=[]
  for t in lib[master]['checks']:
   if t['pin']!=pin:continue
   xs=[x for x in t['x'] if final[0]<=x<=final[1]]+final;ys=[y for y in t['y'] if 5<=y<=40]+[5,40]
   values=[interp(t,x,y) for x,y in itertools.product(xs,ys)];checks.append(dict(pin=pin,type=t['type'],edge=t['edge'],when=t['when'],range_ps=[min(values),max(values)]))
  cases[master+'/'+pin]=dict(chain_minmax_ps=total,stages=stages,final_slew_with25ps_wire_bound=final,native_checks_all_conditionals=checks)
 out[co]=dict(cases=cases,HB4_area=hb['area'],HB4_input_cap_ff=hb['caps']['A'])
# Match each actual launch FF to its exact selected source-domain change.
oldsource=json.load(open(P/'integrated_inputs/source_bound_with_native_CQ.json'));resetmodel=json.load(open(P/'integrated_inputs/integrated_model.json'));cqmap={}
for co in ['TT','FF']:
 cqmap[co]={}
 for z in oldsource[co]['boundary_sources']:
  cqmap[co][z['source']['pin']]=dict(new=z['new_ff']['range_ps'],role='boundary_INV6')
 for net,z in oldsource[co]['changed_cones'].items():
  for v in z['sources']:
   new=v['new_ff']['range_ps'] if z['old_master'].startswith('NAND') else resetmodel[co]['reset'][net]['new_source_ff']
   assert v['source']['pin'] not in cqmap[co]
   cqmap[co][v['source']['pin']]=dict(new=new,role='NAND2x2' if z['old_master'].startswith('NAND') else 'two_reset_HB4_inputs')
# Preserve baseline final-driver wire+cell minimum as ZERO credit; no subgrid extrapolation.
# Removed timing budget is explicit, and new capture check takes worst native conditional arc.
plans=[]
for r in a:
 ep=r['endpoint'];master=r['paths']['FF_min_rise']['source_path'][-1]['cell'] if 'FF_min_rise' in r['paths'] else r['paths']['FF_min_fall']['source_path'][-1]['cell'];pin=ep.rsplit('/',1)[1];bound={}
 for co in ['TT','FF']:
  case=out[co]['cases'][master+'/'+pin];holdtype='hold_rising' if pin=='D' else 'removal_rising';setuptype='setup_rising' if pin=='D' else 'recovery_rising';hmax=max(z['range_ps'][1] for z in case['native_checks_all_conditionals'] if z['type']==holdtype);smax=max(z['range_ps'][1] for z in case['native_checks_all_conditionals'] if z['type']==setuptype);h=[];su=[]
  for edge in ['rise','fall']:
   key=co+'_min_'+edge
   if key in r['paths']:
    z=r['paths'][key];path=z['source_path'];driver=r['driver']['cell'];inputs=[v for v in path if v['instance']==driver and v['pin'].rsplit('/',1)[1]!='Y'];assert inputs,(ep,key)
    original_final_gate_and_net=(z['data_arrival_time']-inputs[-1]['arrival'])*1e12
    # Ignore all new original-driver minimum delay; no negative CQ delta allowed from 359 upsizes.
    lower=z['slack']*1e12-original_final_gate_and_net+case['chain_minmax_ps'][0]+z['margin']*1e12-hmax
    h.append(dict(edge=edge,baseline_slack_ps=z['slack']*1e12,old_gate_plus_net_removed_ps=original_final_gate_and_net,baseline_check_ps=z['margin']*1e12,new_max_check_ps=hmax,conditional_margin_ps=lower))
   key=co+'_max_'+edge
   if key in r['paths']:
    z=r['paths'][key]
    # +18.505TT/+13.718FF source CQ bound inherited from all boundary-upsizing source audit.
    actual_start=z['startpoint']; oldcq=(z['source_path'][0]['arrival']-z['source_clock_path'][-1]['arrival'])*1e12
    source_change=cqmap[co].get(actual_start)
    source_cq_budget=max(source_change['new']['cell_rise'][1],source_change['new']['cell_fall'][1])-oldcq if source_change else 0
    lower=z['slack']*1e12-case['chain_minmax_ps'][1]-source_cq_budget-smax+z['margin']*1e12
    su.append(dict(edge=edge,baseline_slack_ps=z['slack']*1e12,conditional_margin_ps=lower,source_CQ_budget_ps=source_cq_budget,actual_source=actual_start,source_change_role=source_change['role'] if source_change else 'UNCHANGED'))
  bound[co]=dict(hold_or_removal=h,setup_or_recovery=su)
 plans.append(dict(endpoint=ep,role=r['role'],original_net=r['net'],driver=r['driver'],source_owned_branch='keep original driver and all sibling endpoints; insert three real HB4 only on this exact native sink',added_cells=[dict(name='int8_'+r['role']+'_'+str(len(plans))+'_hb'+str(k),master='HB4xp67_ASAP7_75t_R') for k in range(3)],bound=bound))
json.dump(dict(schema='int8.all_hold.source_model.v1',conditional_bounds='no ECO or closure claim; new original-driver min credited ZERO; original driver MAX replay is an explicit additional acceptance budget; first-HB input5..120ps, all new wire cap<=.5fF/stage, waveform degradation5ps/stage+20psfinal; both corners/native transitions/all check conditions retained; no subgrid extrapolation',native=out,plans=plans),open(P/'full_scope_model.json','w'),indent=2)
for co in ['TT','FF']:
 for role in ['data','async']:
  for check in ['hold_or_removal','setup_or_recovery']:
   vals=[b['conditional_margin_ps'] for p in plans if p['role']==role for b in p['bound'][co][check]];print(co,role,check,min(vals), 'below30',sum(x<30 for x in vals))
print('added ordinary+reset branches',len(plans)*3,'area',len(plans)*3*out['TT']['HB4_area'])
