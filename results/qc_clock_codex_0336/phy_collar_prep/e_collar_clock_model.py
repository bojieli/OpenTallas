import runpy,json,math,gzip,re,sys
from pathlib import Path
v=runpy.run_path('/tmp/qcclock0336/pack_e_collar.py');cells=v['cells'];alloc=v['alloc'];route=v['route'];clock=[];roots=[]

def chunks(a,n):
 axis=0 if max(z['xy'][0] for z in a)-min(z['xy'][0] for z in a)>=max(z['xy'][1] for z in a)-min(z['xy'][1] for z in a) else 1
 a=sorted(a,key=lambda z:(z['xy'][axis],z['xy'][1-axis],z['id']));groups=math.ceil(len(a)/n)
 return[a[round(i*len(a)/groups):round((i+1)*len(a)/groups)] for i in range(groups)]
for bank in range(1,10):
 sinks=[]
 for c in cells[:]:
  if not c['id'].startswith(f'b{bank}.') or c['kind'] not in ['DFF_INV','ASR_INV_TIEHI','CONTROL_DFF_LOGIC']:continue
  x,y=c['origin_um'];sinks.append({'id':c['id'],'xy':[x+.108,y+(.209 if c['kind']=='ASR_INV_TIEHI' else .200)],'kind':'ASR' if c['kind']=='ASR_INV_TIEHI' else 'DFF'})
 level=0
 while True:
  groups=chunks(sinks,32 if level==0 else 4);new=[]
  for i,g in enumerate(groups):
   ideal=[sum(z['xy'][k] for z in g)/len(g) for k in [0,1]];c=alloc(ideal,width_sites=38,kind='CONNECTED_CLOCK_BUF24',ident=f'b{bank}.clkL{level}.{i}');x,y=c['origin_um'];node={'id':c['id'],'xy':[x+.048,y+.135],'Y_xy':[x+.956,y+.234],'children':g,'level':level};clock.append(node);new.append(node)
  if len(new)==1:roots.append(new[0]);break
  sinks=new;level+=1
# Actual stockM6/M7 fromlockedplatform; explicit1.7 capguard, fullR (no unclaimedNDR).
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import die_clock_128 as D
libdir=Path('/home/ubuntu/.cache/opentallas/asap7_nldm');ff=json.load(open('/tmp/qcclock0336/collar_cell_pins.json'))
lib={}
for co in ['TT','FF']:
 txt=gzip.open(libdir/f'asap7sc7p5t_INVBUF_RVT_{co}_nldm_220122.lib.gz','rt').read();i=txt.index('cell (BUFx24_ASAP7_75t_R)');j=txt.find('cell (',i+10);b=txt[i:j];lib[co]={'cap':float(re.search(r'rise_capacitance : ([\d.]+)',b)[1]),'tables':{k:D._table(b,k) for k in ['cell_rise','cell_fall','rise_transition','fall_transition']}}
rh,rv=.0118796,.0125096;ch,cv=.187426*1.7,.162979*1.7;via=.0752
nets=[]
def mst(node,co):
 points=[node['Y_xy']]+[z['xy'] for z in node['children']];N=len(points);parents={0:None};edges={};unseen=set(range(1,N))
 while unseen:
  w,i,j=min((abs(points[i][0]-points[j][0])+abs(points[i][1]-points[j][1]),i,j) for i in parents for j in unseen);parents[j]=i;unseen.remove(j);path=route(points[i],points[j]);h=sum(abs(a[0]-b[0]) for a,b in zip(path,path[1:]));ve=sum(abs(a[1]-b[1]) for a,b in zip(path,path[1:]));edges[j]={'r':rh*h+rv*ve,'c':ch*h+cv*ve,'path':path}
 child={i:[] for i in range(N)}
 for j,i in parents.items():
  if i is not None:child[i].append(j)
 def load(i):
  sink=0 if i==0 else lib[co]['cap'] if 'children' in node['children'][i-1] else float(ff[co]['DFFASRHQNx1_ASAP7_75t_R' if node['children'][i-1]['kind']=='ASR' else 'DFFHQNx1_ASAP7_75t_R']['pins']['CLK']['capacitance'])
  return sink+sum(edges[j]['c']+load(j) for j in child[i])
 C={i:load(i) for i in range(N)};el={0:via*C[0]}
 def traverse(i):
  for j in child[i]:el[j]=el[i]+edges[j]['r']*(edges[j]['c']/2+C[j]);traverse(j)
 traverse(0);return C[0],el,edges
results={};sinkrows=[]
for co in ['TT','FF']:
 def walk(node,arrival,slew):
  total,el,edges=mst(node,co);b=lib[co];delay=max(D._bilin(b['tables'][k],slew,total) for k in ['cell_rise','cell_fall']);trans=max(D._bilin(b['tables'][k],slew,total) for k in ['rise_transition','fall_transition'])
  nr={'corner':co,'driver':node['id'],'load_ff':total,'input_slew_ps':slew,'output_cell_transition_ps':trans,'cell_delay_ps':delay,'tree_edges':edges};nets.append(nr)
  for j,s in enumerate(node['children'],1):
   at=arrival+delay+el[j];st=math.hypot(trans,2.2*el[j])
   if 'children' in s:walk(s,at,st)
   else:sinkrows.append({'corner':co,'sink':s['id'],'arrival_ps':at,'transition_ps':st,'clk_pin_um':s['xy']})
 for root in roots:walk(root,0,80)
 rr=[z for z in sinkrows if z['corner']==co];results[co]={'sinks':len(rr),'insertion_min_ps':min(z['arrival_ps'] for z in rr),'insertion_max_ps':max(z['arrival_ps'] for z in rr),'max_transition_ps':max(z['transition_ps'] for z in rr),'sinks_over80ps':sum(z['transition_ps']>80 for z in rr),'per_bank':{str(b):{'min_ps':min(z['arrival_ps'] for z in rr if z['sink'].startswith(f'b{b}.')),'max_ps':max(z['arrival_ps'] for z in rr if z['sink'].startswith(f'b{b}.'))} for b in range(1,10)}}
summary={'status':'CONNECTED LOCALCLOCK MODEL PREP; no actualdieinputarrivals, no nativeFFinternalwaveforms, no signoff or adoption','clock_BUF24':len(clock),'per_bank_roots':9,'actualFFclockpins':9*1208,'actual_data_master_ITerms':'CLK .108/.200, QN1.037/.234, INVinputA1.128/.135; ASRCLK .108/.209; actualBUF24A.048/.135,Y.956/.234','layers':{'H':'M6','V':'M7','r_kohm_um':[rh,rv],'c_ff_um_with1p7_guard':[ch,cv],'M1toM6_via_access_R_kohm':via},'root_input_slew_assumption_ps':80,'corners':results,'HOLD':['globaldieclockinputgraph+relatedCPPR+differentialdroop','negative-edgecontrolFFclockINVfunctionalwiring','clock/data/epoch/reset fullroutingtrackbudget','actualPHYnativeclkbranch/loadsourcewaveform','RTLlockstep+mutant andSTARTtokenpricing','oldclockplaceholder slots remain conservativelyreserved but unconnected'],'connected_clock_cells_are_additional_to_old_reserve':True}
clockedges=[]
for n in nets:
 if n['corner']=='TT':
  for e in n['tree_edges'].values():clockedges.extend(zip(e['path'],e['path'][1:]))
cn=v['cuts'](0,'N',clockedges);ce=v['cuts'](1,'E',clockedges)
summary['clock_only_trackcut']={'N_M6_H':cn,'E_M7_V':ce,'scope':'ActualclockMSTgeometry; no doublecornercount'}
summary['conservative_sum_of_separate_peak_cuts']={'N_data_plus_clock':v['summary']['N_global_M4_M6_cut']['peak_segments']+cn['peak_segments'],'E_data_plus_clock':v['summary']['E_global_M5_M7_cut']['peak_segments']+ce['peak_segments'],'scope':'Upperbound sumofpeakcuts atpossiblydifferentcoordinates; noPG/reset/epoch/rootfeeds'}
summary['additional_clock_master_raw_area_um2']=len(clock)*.4374;summary['additional_clock_master_reserved_um2']=len(clock)*.4374/.4
summary['HOLD'].append('actualTAPCELL/well/endcap/PGbodyledger, notabsorbedasactualcellsby40pctreserve')
out={'summary':summary,'clock_nodes':clock,'clock_nets':nets,'sink_model':sinkrows,'cells':cells};gzip.open('/tmp/qcclock0336/e_collar_connected_clock_prep.json.gz','wt').write(json.dumps(out,separators=(',',':')));Path('/tmp/qcclock0336/e_collar_connected_clock_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
