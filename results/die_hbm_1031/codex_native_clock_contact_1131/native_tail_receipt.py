from pathlib import Path
import re,json,collections
r=Path(__file__).resolve().parent
forms={}
for form in ['narrow','wide']:
 o=r/f'native_tail_pin_{form}'
 s=(o/'route.spef').read_text();names=dict(re.findall(r'^\*(\d+) (\S+)$',s,re.M))
 def expand(n):
  return re.sub(r'\*(\d+)',lambda m:names.get(m[1],m[0]),n)
 sec=next(t for t in re.findall(r'\*D_NET .*?\*END',s,re.S) if expand(t.split()[1])=='native_clock')
 res=[];adj=collections.defaultdict(set)
 for line in sec.split('*RES\n')[1].split('*END')[0].splitlines():
  _,a,b,v=line.split();a,b=expand(a),expand(b);res.append((a,b,float(v)));adj[a].add(b);adj[b].add(a)
 seen={'b5607:Y'};todo=list(seen)
 for a in todo:
  for b in adj[a]:
   if b not in seen:seen.add(b);todo.append(b)
 assert 'native_tail:clk' in seen
 log=(o/'route.log').read_text();drc=int(re.findall(r'Number of violations = (\d+)',log)[-1]);assert drc==0
 arrivals={}
 for corner in ['TT','FF']:
  rows={line.split()[0]:list(map(float,line.split()[1:])) for line in (o/f'native_arr_{corner}.txt').read_text().splitlines()}
  src,clk=rows['b5607/Y'],rows['native_tail/clk']
  arrivals[corner]=dict(source_Y=src,native_clk=clk,rise_wire_delay_ps=clk[0]-src[0],fall_wire_delay_ps=clk[3]-src[3])
 forms[form]=dict(drc=drc,connected_terminals=['b5607:Y','native_tail:clk'],resistor_edges=len(res),Rsum_ohm=sum(z[2] for z in res),wire_cap_ff=float(sec.split()[2])*1000,arrivals=arrivals)
receipt=dict(verdict='ACTUAL_NATIVE_CLOCK_CONTACT_PHYSICAL_PASS',forms=forms,source='Actual C12e b5607 CKINVDCx16 at current C11E legal pose; no other source fanout',child='Current C11E NW_b103.u_hb_idx__s_Q_tail1 exact218.592x187.488 native f56 LEF, real M5 clk ITerm at1058.376,5607.36, Liberty clock:true',physical_scope='99.384um source-origin to nativeCLK; original M8/M9 PG retained. No native clock BTerm; real sourceY/nativeclk resistor-connected in extracted same net.',release_qualified=False,holds=['Native view protected SIGNED physical-only; outerface IO FF+1/+1 current-source qualification unestablished','Probe input40ps is local diagnostic, not global measured source-boundary calibration','Native internal TT/FF related-pair timing not closed by this contact measurement','Whole current event incl mesh/feed/new station taps/START/reset remains BLOCKED'],narrow_initial_violations='13 M5/V5 pin-access markers; DRT optimization repaired all without geometry/rule waiver')
(r/'native_tail_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
