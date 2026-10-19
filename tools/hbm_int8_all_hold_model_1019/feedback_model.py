import json,pathlib,gzip,re,itertools,csv
from lib_native import blocks,scalar,vec,interp
P=pathlib.Path(__file__).parent;B=pathlib.Path('/srv/opentallas-scratch/claude/hbm-int8-cts-v2-run-1019');manifest=json.load(open(P/'typed_lowmargin_manifest.json'));source=json.load(open(P/'integrated_inputs/source_bound_with_native_CQ.json'));loadmodels=json.load(open(P/'source_electrical_model.json'))['corners'];full=json.load(open(P/'full_scope_model.json'));out={}
for co in ['TT','FF']:
 lib={}
 for f in (B/'input/native_libs').glob('*'+co+'*.lib*'):
  text=gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()
  for n,b in blocks(text,'cell'):
   if n not in {'INVx6_ASAP7_75t_R','NAND2xp33_ASAP7_75t_R','OAI21xp33_ASAP7_75t_R'}:continue
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
 rows=[];cq={r['source']['pin']:r['new_ff']['range_ps'] for r in source[co]['boundary_sources']};loads={r['net']:r['new_total_source_load_ff'] for r in loadmodels[co]}
 clocks={(r['pin'],r['mode']):float(r['arrival_ps']) for r in csv.DictReader(open(P/f'clock_all_{co}.tsv'),delimiter='\t')}
 for r in manifest:
  if r['role']!='data':continue
  for edge in ['rise','fall']:
   z=r['paths'][co+'_max_'+edge]
   if z['startpoint'] not in cq:continue
   wave=[min(cq[z['startpoint']][k][0] for k in ['rise_transition','fall_transition']),max(cq[z['startpoint']][k][1] for k in ['rise_transition','fall_transition'])];path=z['source_path'];stages=[];total=[0.,0.]
   for i in range(1,len(path)-1,2):
    ip,op=path[i:i+2];oldmaster=op['cell'];master='INVx6_ASAP7_75t_R' if i==1 else oldmaster;pin=ip['pin'].rsplit('/',1)[1];arcs=[t for t in lib[master]['arcs'] if t['input']==pin and t['output']=='Y'];assert arcs
    cap=loads[r['net']] if op['instance']==r['driver']['cell'] else [op['capacitance']*1e15-.1,op['capacitance']*1e15+.1]
    # Keep last-driver low-load qualification separate: native min grid must be physically met.
    cap[0]=max(cap[0],max(t['y'][0] for t in arcs))
    inp=[wave[0],wave[1]+5];vals={}
    for k in ['cell_rise','cell_fall','rise_transition','fall_transition']:
     tt=[t for t in arcs if t['table']==k];v=[interp(t,x,y) for t in tt for x,y in itertools.product(inp,cap)];vals[k]=[min(v),max(v)]
    d=[min(vals[k][0] for k in ['cell_rise','cell_fall']),max(vals[k][1] for k in ['cell_rise','cell_fall'])];total=[total[0]+d[0],total[1]+d[1]];wave=[min(vals[k][0] for k in ['rise_transition','fall_transition']),max(vals[k][1] for k in ['rise_transition','fall_transition'])];stages.append(dict(instance=op['instance'],master=master,input=pin,input_wave=inp,load_ff=cap,native=vals,old_delay_ps=(op['arrival']-ip['arrival'])*1e12))
   case=full['native'][co]['cases']['DFFASRHQNx1_ASAP7_75t_R/D'];holdmax=max(q['range_ps'][1] for q in case['native_checks_all_conditionals'] if q['type']=='hold_rising');sc=z['startpoint'].rsplit('/',1)[0]+'/CLK';dc=r['endpoint'].rsplit('/',1)[0]+'/CLK';cqmin=min(cq[z['startpoint']]['cell_rise'][0],cq[z['startpoint']]['cell_fall'][0]);lower=clocks[(sc,'min')]+cqmin+total[0]+case['chain_minmax_ps'][0]-clocks[(dc,'max')]-25-holdmax
   rows.append(dict(endpoint=r['endpoint'],source=z['startpoint'],baseline_edge=edge,stages=stages,new_feedback_comb_delay_ps=total,final_OAI_wave_ps=wave,new_feedback_hold_absolute_lower_bound_ps=lower,all_real_clocks=dict(source_min=clocks[(sc,'min')],capture_max=clocks[(dc,'max')]),existing_all_comb_delay_ps=sum(s['old_delay_ps'] for s in stages)))
 out[co]=rows
json.dump(dict(schema='int8.seven_feedback.source_model.v1',scope='Actual7 feedback endpoints/14 transition paths per corner; source-bound native CQ/waves, actual clock early/late, INV6→NAND2→OAI21 propagation, exact inherited output loads and proposed final net loads. All arcs in-range conditional on explicit lower-load qualification; no baseline topN selection.',corners=out),open(P/'feedback_model.json','w'),indent=2)
for co,a in out.items():print(co,'feedback paths',len(a),'min_newhold',min(r['new_feedback_hold_absolute_lower_bound_ps'] for r in a),'maxwave',max(r['final_OAI_wave_ps'][1] for r in a),'maxcombdelay',max(r['new_feedback_comb_delay_ps'][1] for r in a),'minoldcombdelay',min(r['existing_all_comb_delay_ps'] for r in a))
