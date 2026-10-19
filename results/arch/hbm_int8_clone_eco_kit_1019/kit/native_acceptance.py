"""Read-only diagnostic acceptance. Does not publish, mask paths or activate a view."""
import pathlib,json,csv,collections,gzip,sys,re
from lib_native import blocks,vec
P=pathlib.Path(__file__).parent;O=pathlib.Path(sys.argv[1]);C=O/'census';A=json.load(open(P/'allowlist.json'))
raw=json.load(open(O/'native/raw.json'));m=next(iter(raw['modules'].values()));cells=m['cells'];drivers=collections.defaultdict(list)
for n,c in cells.items():
 for p,b in c['connections'].items():
  if b and c['port_directions'][p]=='output':drivers[b[0]].append((n,c['type'],p))
inv=list(csv.DictReader(open(C/'inventory_FF.tsv'),delimiter='\t'));assert len(inv)==3186
classes={};paths={};evidence=collections.defaultdict(list);issues=[];allrecords=[]
for co in ['TT','FF']:
 for role in ['data','async']:
  for cls in ['internal','rootIO']:
   for delay in ['min','max']:
    for edge in ['rise','fall']:
     label=f'{co}_{role}_{cls}_{delay}_{edge}'
     rr=list(csv.DictReader(open(C/(label+'.tsv')),delimiter='\t'));d={r['endpoint']:r for r in rr};assert len(d)==len(rr)
     paths[label]=d;vv=[float(r['slack_ps']) for r in rr]
     classes[label]=dict(endpoints=len(d),below30=sum(v<30 for v in vv),minimum_ps=min(vv,default=None),parent_qualified=False if cls=='rootIO' else None)
     if cls=='internal' and any(v<30 for v in vv):issues.append(label+' margin<30ps')
     jj=json.load(open(C/(label+'.json')))
     assert len(jj['checks'])==len(rr)
     for r in jj['checks']:
      allrecords.append((co,r))
      for v in r['source_path']:
       if 'instance' in v and 'pin' in v and 'capacitance' in v:
        evidence[(co,v['instance'],v['pin'].rsplit('/',1)[-1])].append(v)
coverage=[]
for i in inv:
 ep=i['pin'];n,p=ep.rsplit('/',1);bits=cells[n]['connections'][p];ds=[z for b in bits for z in drivers[b]]
 for co in ['TT','FF']:
  for delay in ['min','max']:
   for edge in ['rise','fall']:
    rr=[paths[f'{co}_{i["role"]}_{cl}_{delay}_{edge}'].get(ep) for cl in ['internal','rootIO']];rr=[r for r in rr if r]
    if rr:status='TIMED'
    elif ds and all(d[1].startswith(('TIELO','TIEHI')) for d in ds):status='CONSTANT_NATIVE_TIE'
    elif p in ['RESETN','SETN'] and edge=='fall':status='NO_NATIVE_FALLING_CHECK'
    else:status='UNEXPLAINED_UNTIMED';issues.append(ep+' '+co+' '+delay+' '+edge)
    coverage.append(dict(endpoint=ep,corner=co,delay=delay,edge=edge,status=status))
# Exact actual cap per polarity/path, source loads are never distance-derived.
source=json.load(gzip.open(P/'inputs/source_electrical_model.json.gz','rt'));caps=[]
for co,rs in source['corners'].items():
 for r in rs:
  d=r['driver'];vs=evidence.get((co,d['cell'],d['pin']),[])
  cc=[v['capacitance']*1e15 for v in vs];ss=[v['slew']*1e12 for v in vs]
  required=.72 if r['requires_new_actual_wire_cap_ge_ff']>0 else 0
  ok=bool(cc) and min(cc)>=required
  if not ok:issues.append(f'{co} source cap/missing {d["cell"]}/{d["pin"]} required{required}')
  if ss and max(ss)>120:issues.append(f'{co} firstHB source waveform>120ps '+d['cell'])
  caps.append(dict(corner=co,driver=d,observed_loads_ff=sorted(set(cc)),observed_slews_ps=sorted(set(ss)),required_minimum_load_ff=required,PASS=ok))
# Actual native min/max arc domains for every added HB4/INV and every
# changed combinational driver observed in the COMPLETE endpoint census.
# No table-edge clamp/extrapolation; absent observations remain explicit OPEN.
lib={};domains=[]
for co in ['TT','FF']:
 lib[co]={}
 for f in (P/'inputs/native_libs').glob('*'+co+'*'):
  text=gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()
  for master,body in blocks(text,'cell'):
   aa=[]
   for output,pbody in blocks(body,'pin'):
    for _,arc in blocks(pbody,'timing'):
     related=re.search(r'related_pin\s*:\s*"([^"]+)"',arc)
     if not related:continue
     for table in ['cell_rise','cell_fall','rise_transition','fall_transition']:
      for _,t in blocks(arc,table):
       aa.append(dict(input=related[1],output=output,table=table,x=vec(t,'index_1'),y=vec(t,'index_2')))
   lib[co][master]=aa
seen=set()
for co,r in allrecords:
 seq=r['source_path']
 for a,b in zip(seq,seq[1:]):
  n=b.get('instance');master=b.get('cell')
  if n not in A['added_cells'] and n not in A['replacement_cells']:continue
  if a.get('instance')!=n or 'capacitance' not in b:continue
  pin=a['pin'].rsplit('/',1)[-1];output=b['pin'].rsplit('/',1)[-1]
  slew=a['slew']*1e12;cap=b['capacitance']*1e15
  key=(co,n,pin,output,slew,cap)
  if key in seen:continue
  seen.add(key);arcs=[t for t in lib[co][master] if t['input']==pin and t['output']==output]
  ok=bool(arcs) and all(t['x'][0]<=slew<=t['x'][-1] and t['y'][0]<=cap<=t['y'][-1] for t in arcs)
  if not ok:issues.append('NATIVE_TABLE_DOMAIN '+str(key))
  domains.append(dict(corner=co,cell=n,master=master,input=pin,output=output,input_slew_ps=slew,output_load_ff=cap,all_native_arc_tables=len(arcs),PASS=ok))
for co in ['TT','FF']:
 for n in A['added_cells']:
  if not any(d['corner']==co and d['cell']==n for d in domains):issues.append('MISSING_NEW_CELL_NATIVE_DOMAIN '+co+' '+n)

clock={}
for co in ['TT','FF']:
 rr=list(csv.DictReader(open(C/f'clock_all_{co}.tsv'),delimiter='\t'))
 for mode in ['min','max']:
  vs=[r for r in rr if r['mode']==mode];assert len(vs)==2782 and len({r['pin'] for r in vs})==2782
  aa=[float(r['arrival_ps']) for r in vs];span=max(aa)-min(aa)
  clock[co+'_'+mode]=dict(minimum_ps=min(aa),maximum_ps=max(aa),spread_ps=span)
  if span>80:issues.append('CLOCK_SPREAD '+co+' '+mode)

# Further native table domains, pulse margins and wire budgets require explicit
# reviewed full native reports. They are never silently promoted by this parser.
required=['native_complete_pg_binding','metal_conductor_contact_short_proof','strict_all_native_transparent_max32','electrical_all_pin_domains_and_30ps_margin','all_native_pulse_conditions_and_30ps_margin','all_new_wire_caps_and_original_source_delta_budgets','actual_RTL_truth_reset_and_causal_fixture_replay','clock_TT_FF_spread80','root_personal_native_PNG_review']
result=dict(status='DIAGNOSTIC_PARSER_PASS_REVIEW_REQUIRED' if not issues else 'NATIVE_SUCCESSOR_REFUSED',classes=classes,coverage_entries=len(coverage),coverage_counts=collections.Counter(r['status'] for r in coverage),issues=issues,source_caps=caps,native_table_domains=domains,clock_native_all_pins=clock,mandatory_independent_evidence=required,parent_IO='DIAGNOSTIC_ROOT_REFERENCE_ONLY_NO_PADDING',publication=False)
with gzip.open(O/'complete_endpoint_coverage.json.gz','wt') as f:json.dump(coverage,f)
(O/'native_acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],'issues',len(issues))
if issues:raise SystemExit(1)
