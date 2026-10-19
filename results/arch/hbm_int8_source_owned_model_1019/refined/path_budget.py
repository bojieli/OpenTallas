"""Native characterized-range path budget of the frozen SOURCE model.
Not STA: upstream arrival/clock difference/actual wire and slew remain unknown.
Reuses immutable lib_native interpolation; no table clamping or nominal min-CQ.
"""
import json,gzip,pathlib,sys,re,itertools,collections
P=pathlib.Path(__file__).parent;K=P/'kit';sys.path.insert(0,str(K))
from lib_native import blocks,scalar,vec,interp
plan=json.load(gzip.open(P/'site_plan.json.gz','rt'));atoms=json.load(open(P/'source_atoms.json'));branches=json.load(open(P/'branch_legs.json'))
raw=json.load(gzip.open(K/'inputs/raw.json.gz','rt'));m=next(iter(raw['modules'].values()));a=json.load(open(K/'allowlist.json'))
native={};units={}
for corner in ('TT','FF'):
 native[corner]={};units[corner]=[]
 for path in sorted((K/'inputs/native_libs').glob('*'+corner+'*')):
  text=gzip.open(path,'rt').read() if path.suffix=='.gz' else path.read_text()
  units[corner].append(dict(file=path.name,time_unit=re.search(r'time_unit\s*:\s*"([^"]+)"',text)[1],capacitance_unit=re.search(r'capacitive_load_unit\s*\(([^)]+)',text)[1]))
  assert units[corner][-1]['time_unit']=='1ps' and units[corner][-1]['capacitance_unit'].replace(' ','')=='1,ff'
  for master,body in blocks(text,'cell'):
   pins={}
   for pin,pb in blocks(body,'pin'):
    tables=[];constraints=[]
    for _,arc in blocks(pb,'timing'):
     rel=re.search(r'related_pin\s*:\s*"([^"]+)"',arc);typ=re.search(r'timing_type\s*:\s*(\w+)',arc)
     for kind in ('cell_rise','cell_fall','rise_transition','fall_transition'):
      for _,tb in blocks(arc,kind):
       tables.append(dict(kind=kind,related=rel[1] if rel else None,timing_type=typ[1] if typ else None,x=vec(tb,'index_1'),y=vec(tb,'index_2'),v=vec(tb,'values')))
     for kind in ('rise_constraint','fall_constraint'):
      for _,tb in blocks(arc,kind):constraints.append(dict(kind=kind,timing_type=typ[1] if typ else None,v=vec(tb,'values')))
    pins[pin]=dict(cap=[v for v in [scalar(pb,k) for k in ('capacitance','rise_capacitance','fall_capacitance')] if v is not None],tables=tables,constraints=constraints)
   native[corner][master]=pins
def cap(c,n,p):return native[c][plan[n]['master']][p]['cap']
def stage(c,n,p,load):
 tabs=native[c][plan[n]['master']][p]['tables']
 # Sequential source uses clock-to-Q arcs, never asynchronous preset/clear arcs.
 if plan[n]['master'].startswith('DFF'):tabs=[t for t in tabs if t['related']=='CLK']
 if not tabs:return dict(status='REFUSE_NO_ARCS',cell=n,output=p)
 refuse=[];vals=collections.defaultdict(list);records=[]
 for t in tabs:
  if not(t['y'][0]<=load[0]<=load[1]<=t['y'][-1]):refuse.append(dict(kind=t['kind'],related=t['related'],load_fF=load,domain_fF=[t['y'][0],t['y'][-1]]));continue
  assert len(t['v'])==len(t['x'])*len(t['y'])
  # Piecewise bilinear extrema occur at every native slew knot and load bounds.
  vs=[interp(t,x,y) for x,y in itertools.product(t['x'],load)]
  vals[t['kind']]+=vs;records.append(dict(kind=t['kind'],related=t['related'],input_wave_native_domain_ps=[t['x'][0],t['x'][-1]],range_ps=[min(vs),max(vs)]))
 if refuse:return dict(status='REFUSE_NATIVE_LOAD_DOMAIN',cell=n,master=plan[n]['master'],output=p,load_fF=load,refusals=refuse)
 delays=vals['cell_rise']+vals['cell_fall'];waves=vals['rise_transition']+vals['fall_transition']
 return dict(status='CHARACTERIZED_RANGE_MODEL_ONLY',cell=n,master=plan[n]['master'],output=p,load_fF=load,delay_ps=[min(delays),max(delays)],output_wave_ps=[min(waves),max(waves)] if waves else None,native_arcs=records,wire_delay_ps=None)
by_source={r['source_net']:r for r in atoms};out=[]
for br in a['branches']:
 for corner in ('TT','FF'):
  sr=by_source[br['source_net']];d=sr['driver'];stages=[stage(corner,d['cell'],d['pin'],sr['corner_loads'][corner]['total_model_fF'])]
  rs=next(r for r in branches if r['first_HB']==br['buffers'][0]);outputs=collections.defaultdict(list)
  for leg in rs['legs']:outputs[tuple(leg['source'])].append(leg)
  for n,p in outputs:
   # Shared tail branches get one total load and one total conservative star wire,
   # never an independent 0.5-fF allowance for each sink.
   legs=outputs[n,p];caps=[cap(corner,*r['sink']) for r in legs];wire=sum(r['nominal_signal_wire_fF'] for r in legs)
   load=[sum(min(v) for v in caps)+wire,sum(max(v) for v in caps)+wire]
   stages.append(stage(corner,n,p,load))
  issues=[s for s in stages if s['status'].startswith('REFUSE')]
  ranges=None if issues else [sum(s['delay_ps'][k] for s in stages) for k in (0,1)]
  # This is a sufficient characterized-range delay model; it cannot establish
  # actual waveform composition. Any downstream-wave table mismatch is explicit.
  waveissues=[]
  for prev,nxt in zip(stages,stages[1:]):
   if prev.get('output_wave_ps') and nxt.get('native_arcs'):
    domains=[r['input_wave_native_domain_ps'] for r in nxt['native_arcs']]
    lo=max(v[0] for v in domains);hi=min(v[1] for v in domains)
    if prev['output_wave_ps'][0]<lo or prev['output_wave_ps'][1]>hi:waveissues.append(dict(driver=prev['cell'],receiver=nxt['cell'],wave_ps=prev['output_wave_ps'],receiver_domain_ps=[lo,hi]))
  endpoints=[]
  for s in br['sinks']:
   master=plan[s['cell']]['master'];pin=s['pin'];cs=native[corner][master][pin]['constraints']
   typ='setup' if pin=='D' else 'recovery';vv=[v for t in cs if (t['timing_type'] or '').startswith(typ) for v in t['v']]
   check=max(vv) if vv else None
   mintyp='hold' if pin=='D' else 'removal';mv=[v for t in cs if (t['timing_type'] or '').startswith(mintyp) for v in t['v']];mincheck=max(mv) if mv else None
   # T + capture_clock - launch_clock - upstream - wires - uncertainty - margin.
   rem=833.3333333333334-60-15-check-ranges[1] if ranges is not None and check is not None else None
   minbound=25+15+mincheck-ranges[0] if ranges is not None and mincheck is not None else None
   endpoints.append(dict(sink=s,native_worst_characterized_check_ps=check,native_worst_hold_or_removal_check_ps=mincheck,required_combined_upstream_arrival_plus_wire_delay_minus_clock_difference_le_ps=rem,required_combined_earliest_upstream_plus_min_wire_minus_clock_difference_ge_ps=minbound))
  out.append(dict(source_net=br['source_net'],first_HB=br['buffers'][0],role=br['role'],corner=corner,stages=stages,cell_delay_sum_ps=ranges,waveform_domain_refusals=waveissues,endpoints=endpoints,actual_whole_path_slack=None,physical_qualification=False))
summary=dict(schema='int8.source_owned.native_whole_path_budget.v1',status='REFUSED_ACTUAL_WIRE_WAVEFORM_AND_UPSTREAM_CLOCK_UNBOUND',units=units,corner_branch_rows=len(out),load_domain_refused_rows=sum(any(s['status'].startswith('REFUSE') for s in r['stages']) for r in out),waveform_domain_refused_rows=sum(bool(r['waveform_domain_refusals']) for r in out),native_budget_evaluated_rows=sum(r['cell_delay_sum_ps'] is not None for r in out),actual_SS_slack=None,actual_FF_hold=None,all3186endpoint_coverage=None,old_headroom_reused=False,source_table_slew_policy='entire actual characterized slew axis, no old observed slew transfer; unsupported load refuses',wire_capacitance_policy='nominal geometrical model only; never minimum actual extracted capacitance',symbolic_clock='capture_clock minus launch_clock remains unknown; no old phases or ideal skew credit',physical_qualification=False)
(P/'native_path_budget_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(P/'native_path_budget.json.gz','wt') as f:json.dump(out,f)
print(json.dumps(summary,indent=2))
