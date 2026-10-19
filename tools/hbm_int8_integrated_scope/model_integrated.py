import re,json,gzip,pathlib,itertools,hashlib
P=pathlib.Path(__file__).parent

def blocks(s,k):
 for m in re.finditer(r'\b'+k+r'\s*\(([^)]*)\)\s*\{',s):
  i=m.end();a=i;d=1
  while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m[1].strip('" '),s[a:i-1]
def scalar(s,k):
 m=re.search(r'\b'+k+r'\s*:\s*(-?[\d.]+(?:e[-+]?\d+)?)',s,re.I);return float(m[1]) if m else None
def vec(s,k):return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?',re.search(k+r'\s*\((.*?)\);',s,re.S)[1],re.I)]
def interp(t,x,y):
 xs,ys=t['x'],t['y'];assert xs[0]<=x<=xs[-1] and ys[0]<=y<=ys[-1],(x,y,xs,ys)
 i=min(len(xs)-2,max(0,next((j-1 for j,z in enumerate(xs) if z>=x),len(xs)-2)));j=min(len(ys)-2,max(0,next((j-1 for j,z in enumerate(ys) if z>=y),len(ys)-2)))
 a=(x-xs[i])/(xs[i+1]-xs[i]);b=(y-ys[j])/(ys[j+1]-ys[j]);v=t['v'];w=len(ys)
 return (1-a)*((1-b)*v[i*w+j]+b*v[i*w+j+1])+a*((1-b)*v[(i+1)*w+j]+b*v[(i+1)*w+j+1])
def ranges(c,inp,load):return {k:[min(interp(t,x,y) for x,y in itertools.product(inp,load)),max(interp(t,x,y) for x,y in itertools.product(inp,load))] for k,t in c['tables'].items()}
D=json.load(open(P/'source_bound_with_native_CQ.json'));S=json.load(open(P/'summary.json'));M=json.load(open(P/'model.json'));out={}
for co in ['TT','FF']:
 lib={}
 for f in P.glob('*'+co+'*lib*'):
  s=gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()
  for n,b in blocks(s,'cell'):
   ps=dict(blocks(b,'pin'));op=ps.get('Y',ps.get('QN',''));tabs={}
   for k in ['cell_rise','cell_fall','rise_transition','fall_transition']:
    a=list(blocks(op,k))
    if a:tabs[k]={'x':vec(a[0][1],'index_1'),'y':vec(a[0][1],'index_2'),'v':vec(a[0][1],'values')}
   caps={pn:[min(v for v in [scalar(pb,k) for k in ['capacitance','rise_capacitance','fall_capacitance']] if v is not None),max(v for v in [scalar(pb,k) for k in ['capacitance','rise_capacitance','fall_capacitance']] if v is not None)] for pn,pb in ps.items() if scalar(pb,'capacitance') is not None}
   checks=[]
   for pn in ['RESETN','D']:
    for _,tb in blocks(ps.get(pn,''),'timing'):
     ty=re.search(r'timing_type\s*:\s*(\w+)',tb)
     if not ty or ty[1] not in ['recovery_rising','removal_rising','hold_rising']:continue
     for k in ['rise_constraint','fall_constraint']:
      for _,q in blocks(tb,k):checks.append({'pin':pn,'type':ty[1] if ty else '?','edge':k,'x':vec(q,'index_1'),'y':vec(q,'index_2'),'v':vec(q,'values')})
   lib[n]={'area':scalar(b,'area'),'caps':caps,'tables':tabs,'checks':checks}
 hb=lib['HB4xp67_ASAP7_75t_R'];iv=lib['INVx6_ASAP7_75t_R'];old=lib['INVx1_ASAP7_75t_R'];rout={}
 for net,c in D[co]['changed_cones'].items():
  if not c['old_master'].startswith('INV'):continue
  source=c['sources'][0];sr=source['source'];nl=[sr['total_ff'][i]-old['caps']['A'][i]+2*hb['caps']['A'][i] for i in range(2)]
  nl[1]+=.5
  # Use new/old CQ from exact native source bounds when in-range; original measured CQ preserved.
  ff=lib['DFFHQNx1_ASAP7_75t_R'];ffv=ranges(ff,sr['clock_slew_ps']['rise'],nl);inp=[min(ffv[k][0] for k in ['rise_transition','fall_transition']),max(ffv[k][1] for k in ['rise_transition','fall_transition'])]
  total=[0.,0.];stages=[]
  for i in range(4):
   load=[hb['caps']['A'][0],hb['caps']['A'][1]+.5] if i<3 else [iv['caps']['A'][0],iv['caps']['A'][1]+.5]
   z=ranges(hb,inp,load);delay=[min(z[k][0] for k in ['cell_rise','cell_fall']),max(z[k][1] for k in ['cell_rise','cell_fall'])];total=[total[j]+delay[j] for j in range(2)];inp=[min(z[k][0] for k in ['rise_transition','fall_transition']),max(z[k][1] for k in ['rise_transition','fall_transition'])+5];stages.append({'stage':i,'load_ff':load,'range':z,'slew_with_wire_bound_ps':inp})
  z=ranges(iv,inp,c['actual_load_ff']);total=[total[0]+min(z[k][0] for k in ['cell_rise','cell_fall']),total[1]+max(z[k][1] for k in ['cell_rise','cell_fall'])]
  final=[min(z[k][0] for k in ['rise_transition','fall_transition']),max(z[k][1] for k in ['rise_transition','fall_transition'])+25] # existing distributed reset wire waveform bounded separately
  checks=[q for q in lib['DFFASRHQNx1_ASAP7_75t_R']['checks'] if q['pin']=='RESETN' and q['type'] in ['recovery_rising','removal_rising']]
  # Full native checked waveform domain, retaining every conditional check arc.
  checkranges=[]
  for q in checks:
   xx=[v for v in q['x'] if max(5,final[0])<=v<=min(260,final[1])]+[max(q['x'][0],final[0]),min(q['x'][-1],final[1])]
   yy=[v for v in q['y'] if 5<=v<=40]+[5,40]
   vals=[interp(q,x,y) for x,y in itertools.product(xx,yy)];checkranges.append({'type':q['type'],'edge':q['edge'],'range_ps':[min(vals),max(vals)]})
  paths=S[co]['cones'][net]['paths'];conds=[]
  # Existing native checks are frozen ONLY in conditional comparisons; root grant demands actual native replay.
  for p in paths:
   cq=min(ffv['cell_rise'][0],ffv['cell_fall'][0]);conds.append(p['existing_native_min_slack_ps']+cq-p['original_CQ_ps']+total[0]-p['original_gate_ps'])
  rout[net]={'new_source_load_ff':nl,'new_source_ff':ffv,'stages':stages,'chain_total_min_max_ps':total,'final_cell':z,'final_reset_slew_with_25ps_wire_budget':final,'native_new_check_ranges':checkranges,'conditional_min_slack_fixed_wire_and_check_ps':min(conds)}
 # Ordinary D hold: preserve inverter polarity and insert 2 true HB4 buffers after inverter before its sole target D.
 # Use the whole admissible 5..80ps waveform envelope; both actual DFFHQN and ASRHQN capture caps retained.
 dc=lib['DFFHQNx1_ASAP7_75t_R']['caps']['D'];inp=[5,80];dd=[0.,0.];ds=[]
 for load in [[hb['caps']['A'][0],hb['caps']['A'][1]+.5],[hb['caps']['A'][0],hb['caps']['A'][1]+.5],[dc[0],dc[1]+.5]]:
  z=ranges(hb,inp,load);dd=[dd[0]+min(z[k][0] for k in ['cell_rise','cell_fall']),dd[1]+max(z[k][1] for k in ['cell_rise','cell_fall'])];inp=[min(z[k][0] for k in ['rise_transition','fall_transition']),max(z[k][1] for k in ['rise_transition','fall_transition'])+5];ds.append(z)
 hchecks=[]
 for q in lib['DFFHQNx1_ASAP7_75t_R']['checks']:
  if q['pin']!='D' or q['type']!='hold_rising':continue
  xs=[v for v in q['x'] if inp[0]<=v<=inp[1]]+inp
  ys=[5,10,20,40]
  vv=[interp(q,x,y) for x,y in itertools.product(xs,ys)]
  hchecks.append({'edge':q['edge'],'range_ps':[min(vv),max(vv)]})
 out[co]={'ordinary_D_native_hold_check_ranges':hchecks,'reset':rout,'ordinary_D_three_HB4':{'delay_min_max_ps':dd,'stages':ds,'final_slew_ps':inp,'D_cap_ff':dc},'HB4_area':hb['area'],'HB4_cap_ff':hb['caps']['A']}
json.dump(out,open(P/'integrated_model.json','w'),indent=2)
for co,z in out.items():
 print(co,'D',z['ordinary_D_three_HB4']['delay_min_max_ps'])
 for n,r in z['reset'].items():print(n,'minmax',r['chain_total_min_max_ps'],'slackConditional',r['conditional_min_slack_fixed_wire_and_check_ps'],'wave',r['final_reset_slew_with_25ps_wire_budget'],'checks',r['native_new_check_ranges'])
