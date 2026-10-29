#!/usr/bin/env python3
"""Independent actual-netlist clock recurrence and generic CA counter arithmetic.
Only the comparison target calls the implementation. All expected arithmetic is
below, separately coded from raw T/N/F/M and actual cell connectivity.
"""
import json,math,re,sys,pathlib,collections
R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-kv-1028');C=pathlib.Path('/srv/opentallas-scratch2/claude/codex-clock-components-1028');O=pathlib.Path(sys.argv[1]);O.mkdir(exist_ok=True)
KEYS=['late_ps','early_ps','fall_late_ps','fall_early_ps'];NK=['node_'+x for x in KEYS]
# Published calibrated constants, independently transcribed. Not new calibration.
BUF={'BUFx24_ASAP7_75t_R':{'TT':[1.0473,1.0222,1.0227,1.0206],'FF':[1.0552,1.0073,1.0257,1.0025]},
'BUFx4_ASAP7_75t_R':{'TT':[1.0443,1.0164,1.0388,1.0018],'FF':[1.0263,.9972,1.024,.9877]},
'BUFx6f_ASAP7_75t_R':{'TT':[1.0243,1.0463,1.0218,1.0417],'FF':[1.0101,1.0301,1.0056,1.025]}}
INV={'TT':[.9324,1.0241,.9324,1.0241],'FF':[.938,1.0487,.938,1.0487]}
text=pathlib.Path('/srv/opentallas-scratch2/claude/die-kv-21-1028/kit_c/clock/ctree.v').read_text()
cells={};driver={};alias=dict(re.findall(r'\bassign\s+(\S+)\s*=\s*(\S+)\s*;',text))
for master,inst,body in re.findall(r'^\s*(\w+)\s+(\w+)\s*\((.*?)\);',text,re.M|re.S):
 pins=dict(re.findall(r'\.(\w+)\s*\(\s*([^()\s]+)\s*\)',body))
 if 'A' in pins and 'Y' in pins:cells[inst]=(master,pins['A']);driver[pins['Y']]=inst
assert cells

def drive(net):
 seen=set()
 while net in alias:
  assert net not in seen;seen.add(net);net=alias[net]
 return driver.get(net)

def dist(lo,hi,T,off):
 k=math.floor((lo-off)/T);return min(lo-(off+k*T),off+(k+1)*T-hi)

report={'scope':'actual measured netlist recurrence plus CA integer/sample arithmetic; not independent characterization or full OCV re-solve','clocks':{},'errors':[]}
sys.path.insert(0,str(R/'mixed_source/tools/die_plan'))
import die_sta_related as D # comparison target only, never expected recurrence
for corner in ['TT','FF']:
 raw={q:{} for q in 'TNFM'}
 for line in (C/f'arr_{corner}.txt').read_text().splitlines():
  f=line.split()
  if f and f[0] in raw and len(f)>=4:raw[f[0]][f[1]]=list(map(float,f[2:4]))
 d=json.load(open(R/f'proof_mixed/tap_arrivals_{corner}.json'));taps={t['port']:t for t in d.pop('taps')}
 meta,got=D.apply_clock_cal(d,taps,corner,'inv','spice_edge')
 # A cell contributes its incoming wire+cell delay. Its factors follow the ACTUAL
 # local input edge reached by source rise. Parent parity is derived from netlist.
 memo={};parity={};negative=[];masters=collections.Counter();phasecount=collections.Counter()
 def factors(master,phase):
  f=INV[corner] if master.startswith('CKINVDCx16_') else BUF[master][corner]
  return [f[2],f[3],f[0],f[1]] if phase else f
 def arrival(cell):return raw['N'][cell]+raw['M'][cell]
 def accumulate(cell):
  if cell in memo:return memo[cell]
  master,net=cells[cell];p=drive(net);parent=accumulate(p) if p else [0.]*4;phase=parity[p] if p else 0
  a=arrival(cell);b=arrival(p) if p else [0.]*4;delta=[x-y for x,y in zip(a,b)]
  if min(delta)<-.001:negative.append((cell,min(delta)))
  parity[cell]=phase^('INV' in master.upper());masters[master]+=1;phasecount[str(phase)]+=1
  memo[cell]=[x+(y-z)*f for x,y,z,f in zip(parent,a,b,factors(master,phase))]
  return memo[cell]
 def capped(v):return [v[0],min(v[1],v[0]),v[2],min(v[3],v[2])]
 maximum=0.;rawerr=0.;sums=0.;tap_errors=[];weighted={}
 for name,t in taps.items():
  cell=drive(name);assert cell is not None
  v=raw['T'][name]+raw['F'][name];a=arrival(cell);master,net=cells[cell];p=drive(net)
  base=accumulate(cell);phase=parity[p] if p else 0
  want=capped([x+(y-z)*f for x,y,z,f in zip(base,v,a,factors(master,phase))]);weighted[name]=want
  maximum=max(maximum,max(abs(want[i]-got[name][k]) for i,k in enumerate(KEYS)))
  rawerr=max(rawerr,max(abs(v[i]-t[k]) for i,k in enumerate(KEYS)))
  sums=max(sums,max(abs(sum(q[k] for q in t['clock_components'])-v[i]) for i,k in enumerate(KEYS)))
 for path,cell in d['node_cell'].items():
  want=capped(accumulate(cell));maximum=max(maximum,max(abs(want[i]-meta[k][path]) for i,k in enumerate(NK)))
  rawerr=max(rawerr,max(abs(arrival(cell)[i]-d[k][path]) for i,k in enumerate(NK)))
 duty=[50+100*(v[2]-v[0])/833 for v in weighted.values()]
 report['clocks'][corner]=dict(taps=len(taps),nodes=len(d['node_cell']),physical_cells=len(memo),masters=dict(masters),local_input_phases=dict(phasecount),raw_max_error_ps=rawerr,telescoping_max_error_ps=sums,weighted_both_edge_max_error_ps=maximum,negative_increments=negative[:5],duty_percent=[min(duty),max(duty)])
 assert maximum<1e-8 and rawerr<.001 and sums<.002 and not negative
b=json.load(open(R/'ca_mixed_replan.json'));s=json.load(open(R/'sta_replan/die_sta_related.json'));Tb=b['period_ps'];T=s['period_ps'];nom=b.get('parts',b['regions']);reg=b['regions'];errs=[]
for pid,c in b['ports'].items():
 src=c.get('src_part',c['src']);dst=c.get('dst_part',c['dst']);dn=nom[dst]['n_nominal']-nom[src]['n_nominal']
 if c['K']+1+dn!=c['sched_lat']:errs.append(['counter_identity',pid])
 if c['depth'] not in [4,8,16]:errs.append(['unsupported_depth',pid])
for name,q in nom.items():
 if q.get('role')=='relay' and q['n_nominal']!=nom[q['src']]['n_nominal']+q['stages']:errs.append(['relay_origin',name])
start_fail=[]
for pid,e in b['start_ports'].items():
 r=reg[e['dst']];off=Tb/2 if r.get('edge_fall') else 0
 # The first sampling edge at/after d gives the three-flop origin step.
 step=math.ceil((Tb+off-e['d_ps'])/Tb)+1+r['pad']
 if step!=e['step'] or reg[e['dst']]['n_nominal']-reg[e['src']]['n_nominal']!=step:start_fail.append(pid)
roots=[name for name,q in reg.items() if q['parent'] is None]
assert roots==[b['root']]
seen=set();todo=roots[:]
while todo:
 name=todo.pop();assert name not in seen;seen.add(name);todo.extend(x for x,q in reg.items() if q['parent']==name)
assert seen==set(reg)
report['counter']=dict(regions_reached=len(seen),crossings=len(b['ports']),start_ports=len(b['start_ports']),counter_errors=errs,start_step_errors=start_fail,sched_lat_total=sum(c['sched_lat'] for c in b['ports'].values()),max_origin=max(r['n_nominal'] for r in reg.values()),bind_period_ps=Tb,gate_period_ps=T)
assert not errs and not start_fail
for corner in ['TT','FF']:
 ca=s['count_aligned'][corner];rows=ca['rows'];worstlo=worsthi=math.inf;maxerr=0
 for q in rows:
  lo=q['L_lo_ps']-T/2;hi=(q['depth']-.5)*T-q['L_hi_ps'];worstlo=min(worstlo,lo);worsthi=min(worsthi,hi)
  maxerr=max(maxerr,abs(lo-q['margin_lo_ps']),abs(hi-q['margin_hi_ps']))
 ss=ca['start_skew']['rows'];sd=[];serr=0.;sfail=[]
 for q in ss:
  # The emitted gate rows already state which measured edge supplied these
  # intervals. Recompute the sampling distance independently, incl real clkQ.
  off=T/2 if q['edge']=='fall' else 0
  value=dist(q['d_lo_ps']-q['skew_hi_ps'],q['d_hi_ps']-q['skew_lo_ps'],T,off)
  sd.append(value);serr=max(serr,abs(value-q['sta_sync_dist_ps']))
  if value<26.5 or not q['ok']:sfail.append(q['port'])
 report[corner]=dict(data_rows=len(rows),min_margin_lo_ps=worstlo,min_margin_hi_ps=worsthi,margin_rounding_max_ps=maxerr,start_rows=len(ss),start_min_sampling_distance_ps=min(sd),start_rounding_max_ps=serr,start_fail=sfail,gate_missing=ca['no_taps'],gate_unbound=ca['unbound'])
 assert maxerr<=.101 and serr<=.201 and not sfail and len(ss)==139 and not ca['no_taps'] and not ca['unbound']
report['limitations']=['Published calibrated factors are inputs; no independent transistor characterization.','Margins/sample arithmetic checks reported OCV intervals, not an independent OCV/droop full-pair solve.','Bind T833 versus die STA T833.333 retained and exposed; both current gate phase arithmetic reproduced.','Conservative glue FF real-view -50.98 remains FAIL; no die freeze or signoff claim.']
(O/'independent_check.json').write_text(json.dumps(report,indent=1));print(json.dumps(report,indent=1))
