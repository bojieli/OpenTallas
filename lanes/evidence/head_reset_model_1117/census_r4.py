from pathlib import Path
import json,re,sys,collections,hashlib
L=Path('/srv/opentallas-scratch2/claude/head-die-r');H=L/'nf15c_real4';O=L/'reset_feasibility_r4_1117';O.mkdir(exist_ok=True)
P=json.load(open(L/'prep21z20NF15c/prep/source_plan.json'));J=json.load(open(H/'run/die_sta.json'));M=json.load(open(H/'manifest.json'));S={c:json.load(open(H/f'spine_{c}.json'))['parts'] for c in ['TT','FF']};pt={x['name']:x['type'] for x in P['partitions']}
rows=[];need=collections.defaultdict(set);netseams=json.load(open(H/'run/seams.json'))['seams'];nmap={(x['src'],x['dst'],x['dst_bus']):x for x in netseams}
for k,v in J['corners']['TT']['seams'].items():
 src,rest=k.split('->');dst,bus=rest.split('/',1)
 if bus not in ('arst_n','start_i'):continue
 ff=J['corners']['FF']['seams'].get(k,{})
 if not all(x.get('paths') for x in [v.get('min',{}),v.get('max',{}),ff.get('min',{})]):continue
 d=dict(seam=k,src=src,dst=dst,bus=bus,src_type=pt[src],dst_type=pt[dst],tt_setup=v['max']['worst'],tt_hold=v['min']['worst'],ff_hold=ff['min']['worst'],tt_launch=float(v['min']['launch']),tt_capture=float(v['min']['capture']))
 for side,part,path in [('src',src,v['min']['start']),('dst',dst,v['min']['end'])]:
  cell=path.removeprefix(part+'/').rsplit('/',1)[0];d[side+'_cell']=cell;need[pt[part]].add(cell)
 ns=nmap.get((src,dst,bus));d['source_port']=ns['src_pin'] if ns else None;rows.append(d)
clocks={};cellstart=re.compile(r'^\s*([A-Za-z_]\w*)\s+(\\\S+|\S+)\s+\(');clk=re.compile(r'\.CLK\(\s*(\\\S+|[^)\s]+)\s*\)')
for tn,cells in need.items():
 f=H/'parts'/M[tn]['module']/'6_final.v';got={};active=None;buf=''
 with f.open() as h:
  for ln in h:
   m=cellstart.match(ln)
   if m:
    name=m.group(2).lstrip('\\');active=name if name in cells else None;buf=''
   if active:
    buf+=ln
    if ');' in ln:
     cm=clk.search(buf)
     if cm:
      net=cm.group(1).lstrip('\\');rm=re.search(r'(clk_t\d+|clk)(?:_regs)?$',net);got[active]=dict(net=net,root=rm.group(1) if rm else None)
     active=None
 clocks[tn]=got
# Resolve non-tagged clock-buffer leaves from actual routed netlist, not names alone.
for tn,got in clocks.items():
 unresolved=[v for v in got.values() if not v['root']]
 if not unresolved:continue
 text=(H/'parts'/M[tn]['module']/'6_final.v').read_text();drivers={}
 for m in re.finditer(r'^\s*((?:BUF|HB|INV)\w+)\s+\S+\s+\((.*?)\);',text,re.M|re.S):
  pins=dict((a,b.strip().lstrip('\\')) for a,b in re.findall(r'\.(A|Y)\(\s*([^)]*?)\s*\)',m.group(2)))
  if set(pins)=={'A','Y'}:drivers[pins['Y']]=pins['A']
 for v in unresolved:
  n=v['net'];seen=[]
  while n not in seen:
   seen.append(n);rm=re.search(r'(clk_t\d+|clk)(?:_regs)?$',n)
   if rm:v['root']=rm.group(1);break
   if n not in drivers:break
   n=drivers[n]
  v['actual_buffer_trace']=seen

# Candidate root changes preserve measured local tree delay optimistically; no physical/pass claim.
for d in rows:
 for side in ['src','dst']:
  d[side+'_clock']=clocks[d[side+'_type']].get(d[side+'_cell'])
 sc=d['src_clock'];dc=d['dst_clock'];opts=[]
 if sc and dc and sc['root'] and dc['root']:
  for a,av in S['TT'].get(d['src'],{}).get('taps',{}).items():
   for b,bv in S['TT'].get(d['dst'],{}).get('taps',{}).items():
    try:
     dt=(av['offset_ps']-S['TT'][d['src']]['taps'][sc['root']]['offset_ps'])-(bv['offset_ps']-S['TT'][d['dst']]['taps'][dc['root']]['offset_ps'])
     df=(S['FF'][d['src']]['taps'][a]['offset_ps']-S['FF'][d['src']]['taps'][sc['root']]['offset_ps'])-(S['FF'][d['dst']]['taps'][b]['offset_ps']-S['FF'][d['dst']]['taps'][dc['root']]['offset_ps'])
    except KeyError:continue
    if d['tt_setup']-dt>=-42 and d['ff_hold']+df>=0:opts.append(dict(src_tap=a,dst_tap=b,tt_delta=dt,ff_delta=df,tt_setup=d['tt_setup']-dt,ff_hold=d['ff_hold']+df))
 d['unrestricted_same_edge_tap_candidates']=len(opts);d['best_optimistic_candidate']=max(opts,key=lambda x:min(x['tt_setup']+42,x['ff_hold'])) if opts else None
 d['classification']='BASELINE_HOLD_PASS' if d['ff_hold']>=0 else ('LOCAL_TAP_OPTIMISTIC_CANDIDATE' if opts else 'NO_LOCAL_TAP_SOLUTION_OPTIMISTIC' if sc and dc and sc['root'] and dc['root'] else 'ROOT_UNRESOLVED')
res=dict(schema='opentallas.head_reset_feasibility.v1',note='Necessary condition only: uses measured die root TT/FF arrival differences, retains old local tree and data delays, permits ALL type taps without geometry restriction. Thus NO_LOCAL_TAP_SOLUTION is decisive for this model; a candidate is NOT implementable until geometry/local CTS measured. No plan/RTL/clock constraints changed.',source_sha256=hashlib.sha256((H/'run/die_sta.json').read_bytes()).hexdigest(),summary=dict(total=len(rows),classes=dict(collections.Counter(x['classification'] for x in rows)),tt_negative=sum(x['tt_hold']<0 for x in rows),ff_negative=sum(x['ff_hold']<0 for x in rows)),rows=rows)
(O/'feasibility.json').write_text(json.dumps(res,indent=1)+'\n');print(json.dumps(res['summary']));print('WORST',json.dumps(sorted(rows,key=lambda x:x['ff_hold'])[:4],indent=1))
