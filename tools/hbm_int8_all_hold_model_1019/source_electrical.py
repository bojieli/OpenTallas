import json,pathlib,gzip,re,collections,itertools
from lib_native import blocks,scalar,vec,interp
P=pathlib.Path(__file__).parent;B=pathlib.Path('/srv/opentallas-scratch/claude/hbm-int8-cts-v2-run-1019');manifest=json.load(open(P/'typed_lowmargin_manifest.json'));groups=collections.defaultdict(list)
for r in manifest:groups[r['net']].append(r)
needed={r['driver']['master'] for r in manifest}|{'HB4xp67_ASAP7_75t_R','DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R'};result={}
for co in ['TT','FF']:
 lib={}
 for f in (B/'input/native_libs').glob('*'+co+'*.lib*'):
  text=gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()
  for n,b in blocks(text,'cell'):
   if n not in needed:continue
   pins=dict(blocks(b,'pin'));caps={}
   for pn,pb in pins.items():
    v=[scalar(pb,k) for k in ['capacitance','rise_capacitance','fall_capacitance'] if scalar(pb,k) is not None]
    if v:caps[pn]=[min(v),max(v)]
   arcs=[]
   for pn,pb in pins.items():
    for _,tb in blocks(pb,'timing'):
     rp=re.search(r'related_pin\s*:\s*"([^"]+)"',tb)
     if not rp:continue
     for k in ['cell_rise','cell_fall','rise_transition','fall_transition']:
      for _,z in blocks(tb,k):arcs.append(dict(output=pn,input=rp[1],table=k,x=vec(z,'index_1'),y=vec(z,'index_2'),v=vec(z,'values')))
   lib[n]=dict(caps=caps,arcs=arcs)
 out=[]
 for net,rs in groups.items():
  r=rs[0];driver=r['driver'];cell=lib[driver['master']];oldcaps=[];sourcewaves=[];existingdelays=[]
  for rr in rs:
   for key,p in rr['paths'].items():
    if not key.startswith(co):continue
    path=p['source_path'];outs=[v for v in path if v['instance']==driver['cell'] and v['pin'].rsplit('/',1)[1]==driver['pin']];ins=[v for v in path if v['instance']==driver['cell'] and v['pin'].rsplit('/',1)[1]!=driver['pin']]
    if outs and ins:oldcaps.append(outs[-1]['capacitance']*1e15);sourcewaves.append(ins[-1]['slew']*1e12);existingdelays.append((outs[-1]['arrival']-ins[-1]['arrival'])*1e12)
  dcaps=[lib[rr['paths']['FF_min_rise']['source_path'][-1]['cell']]['caps'][rr['endpoint'].rsplit('/',1)[1]] for rr in rs]
  newcaps=[min(oldcaps)-sum(c[1] for c in dcaps)+len(rs)*lib['HB4xp67_ASAP7_75t_R']['caps']['A'][0],max(oldcaps)-sum(c[0] for c in dcaps)+len(rs)*lib['HB4xp67_ASAP7_75t_R']['caps']['A'][1]+.5]
  # Additional source-net wire allowance is .5fF TOTAL per actual shared source net.
  waves=[min(sourcewaves),max(sourcewaves)+10];native=[];refused=[]
  for t in cell['arcs']:
   if t['output']!=driver['pin']:continue
   if not (t['x'][0]<=waves[0]<=waves[1]<=t['x'][-1] and t['y'][0]<=newcaps[0]<=newcaps[1]<=t['y'][-1]):refused.append(dict(input=t['input'],table=t['table'],domain_x=t['x'],domain_y=t['y']));continue
   vals=[interp(t,x,y) for x,y in itertools.product(waves,newcaps)];native.append(dict(input=t['input'],table=t['table'],range=[min(vals),max(vals)]))
  maxdel=max((x['range'][1] for x in native if x['table'] in ['cell_rise','cell_fall']),default=None);maxwave=max((x['range'][1] for x in native if x['table'] in ['rise_transition','fall_transition']),default=None)
  out.append(dict(net=net,driver=driver,actual_branch_count=len(rs),all_actual_old_sinks=r['all_native_net_pins'],old_native_output_load_ff=[min(oldcaps),max(oldcaps)],new_total_source_load_ff=newcaps,source_input_wave_ps=waves,old_observed_driver_delay_ps=[min(existingdelays),max(existingdelays)],all_native_arc_bounds=native,table_domain_refusals=refused,max_new_driver_delay_ps=maxdel,max_new_driver_wave_ps=maxwave,conditional_delta_max_ps=maxdel-min(existingdelays) if maxdel is not None else None,requires_new_actual_wire_cap_ge_ff=max(0,max((t['y'][0] for t in cell['arcs']),default=0)-newcaps[0])))
 result[co]=out
json.dump(dict(source_net_wire_allowance_ff=.5,source_input_wave_extra_ps=10,corners=result),open(P/'source_electrical_model.json','w'),indent=2)
for co,a in result.items():
 print(co,'nets',len(a),'refused',sum(bool(x['table_domain_refusals']) for x in a),'maxdriverdelta',max(x['conditional_delta_max_ps'] for x in a if x['conditional_delta_max_ps'] is not None),'maxwave',max(x['max_new_driver_wave_ps'] for x in a if x['max_new_driver_wave_ps'] is not None));print('FIRSTREFUSALS',[(x['net'],x['new_total_source_load_ff'],x['source_input_wave_ps'],x['table_domain_refusals'][:1]) for x in a if x['table_domain_refusals']][:5])
