#!/usr/bin/env python3
"""Read-only receipt for a prospective soft L2: exact placed FFs, identities and external bits."""
import collections,json,re,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/autopilot'));import geom_rules as G
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
D=G.Design(src/'geom.tsv');origin=[1149.12,613.44];prefix='u_gunit.u_l2';rows=[];ff={};terms=collections.defaultdict(list)
def unescape(s):return s.replace('\\','')
def state_alias(n):
 n=unescape(n).split('$_')[0]
 m=re.fullmatch(r'(cwn|cws)_(a|d)\[(\d+)\]',n)
 if m:return f'{m[1]}_q[{int(m[3])+(8 if m[2]=="d" else 0)}]','explicit RTL continuous assignment'
 if n in ('cwn_v','cws_v'):return n+'q','explicit RTL continuous assignment'
 m=re.fullmatch(r'(sidn|sids)\[(\d+)\]',n)
 if m:return ('sn_q' if m[1]=='sidn' else 'ss_q')+'['+m[2]+']','explicit RTL continuous assignment'
 if n.startswith('u_vs.ra_n'):return n.replace('u_vs.ra_n','u_vs.in_'),'explicit RTL continuous assignment'
 if n.startswith('u_vs.ra_s'):return n.replace('u_vs.ra_s','u_vs.is_'),'explicit RTL continuous assignment'
 if n.startswith('u_rr.rst_n'):return n,'synth alias of reset relay output; source bit identity requires parent binding'
 return n,'synthesized state name matches source declaration/array; candidate parent prefix only'
for line in (src/'homes.tsv').read_text().splitlines():
 q=line.split('\t')
 if q[0]=='R':rows.append(dict(x=float(q[1]),y=float(q[2]),orient=q[3],site_width_um=float(q[4]),row_height_um=float(q[5]),sites=int(q[6])))
 elif q[0]=='F':
  ident=int(q[1]);name=q[2];bb=list(map(float,q[8:12]));alias,reason=state_alias(name)
  ff[ident]=dict(id=ident,actual_kit_instance=name,actual_master=q[3],orient=q[4],status=q[5],local_lower_left_um=list(map(float,q[6:8])),local_bbox_um=bb,parent_lower_left_um=[float(q[6])+origin[0],float(q[7])+origin[1]],parent_bbox_um=[bb[0]+origin[0],bb[1]+origin[1],bb[2]+origin[0],bb[3]+origin[1]],parent_instance_candidate=prefix+'.'+unescape(name),source_state_candidate=prefix+'.'+alias,identity_basis=reason)
 elif q[0]=='I':terms[int(q[1])].append(dict(pin=q[2],direction=q[3],sig_type=q[4],net=q[5]))
byrow={round(r['y'],6):r for r in rows};bad=[]
for k,v in ff.items():
 x,y=v['local_lower_left_um'];rw=byrow.get(round(y,6));v['iterms']=terms[k];v['row_orient']=rw['orient'] if rw else None
 ok=rw is not None and abs((x-rw['x'])/rw['site_width_um']-round((x-rw['x'])/rw['site_width_um']))<1e-5
 allowed={'R0':{'R0','MY'},'MX':{'MX','R180'}};ok=ok and v['orient'] in allowed.get(v['row_orient'],set())
 v['site_and_row_orientation_ok']=ok
 if not ok:bad.append(k)
assert len(ff)==3567 and set(ff)=={k for k,v in D.cells.items() if v[0]=='S'} and not bad
# Exact first registered endpoints through transparent buffer/inverter cells;
# record every endpoint reached at the first registered boundary, not just nearest.
external=[];unresolved=[]
for p in D.pins:
 if p['sig'] in ('POWER','GROUND','CLOCK') or p['name']=='clk':continue
 n=D.pin_net.get(p['k']);todo=collections.deque([(n,0)]) if n is not None else collections.deque();seen=set();hits={}
 while todo:
  ni,depth=todo.popleft()
  if ni in seen:continue
  seen.add(ni);sig,dr,sk=D.nets[ni]
  for ref in ([dr] if p['io']=='OUTPUT' else sk):
   if not ref or ref[0]!='i' or ref[2]:continue
   k=ref[1];kind=D.kind(k)
   if kind=='S':hits[k]=min(depth,hits.get(k,999));continue
   if kind!='B':continue
   nxt=[x[0] for x in D.cell_in[k] if not x[1]] if p['io']=='OUTPUT' else D.drives.get(k,[])
   for nx in nxt:todo.append((nx,depth+1))
 if not hits:unresolved.append(p['name'])
 ends=[]
 for ident,depth in sorted(hits.items()):
  v=ff[ident];bb=v['local_bbox_um'];cx,cy=(bb[0]+bb[2])/2,(bb[1]+bb[3])/2
  ends.append(dict(ff_id=ident,actual_instance=v['actual_kit_instance'],source_state_candidate=v['source_state_candidate'],transparent_cells=depth,pin_to_ff_manhattan_um=round(abs(cx-p['x'])+abs(cy-p['y']),6)))
 external.append(dict(port=p['name'],direction=p['io'],pin_local_um=[p['x'],p['y']],pin_parent_um=[p['x']+origin[0],p['y']+origin[1]],registered_endpoints=ends))
assert len(external)==3143 and not unresolved
lec=json.load(open(src/'lec.json'));assert lec['verdict']=='EQUIVALENT'
receipt=dict(scope='READ ONLY PROPOSAL, no plan/RTL adoption, no parent synthesis/clock/placement proof. Exact kit instance prefixes are candidate parent bindings; source aliases are labeled. No LEC rerun.',source='codex/s81-cores-1028@654415ba4',checkpoint='intel2:/srv/opentallas-scratch2/claude/codex-s81-cores-1028/kits/dsdv_gunit_l2_compact_links216/run/results/asap7/kl_dsdv_gunit_l2_compact_links216/base/3_place.odb',parent_origin_um=origin,parent_prefix=prefix,ff_count=len(ff),orientations=dict(collections.Counter(v['orient'] for v in ff.values())),row_site_failures=bad,external_bits=len(external),unresolved_ports=unresolved,clock_sinks=len(ff),clock_contract='all source sequential blocks use posedge clk; receipt records actual CLK/CK iterms. Parent must regenerate full soft-sink clock tree; no old tree.',waveform_contract=dict(added_cycles=0,condition='Only remove hard binding, retain exact RTL and every state transition; parent integration still requires exact binding and normal gates.',rung='vi_s/vi_n -> is_/in_ first edge; classified forward/deliver outputs second edge. Injector CTL pin capture then JREG0 direct registered injection; unchanged.',cw='cw input -> u_cwi N1 first edge; cwn/cws output copies second edge.',sid='sid_q first edge; sn_q/ss_q second edge.',hp='rung input capture, hc kind7 copy, hp output copy; valid pipeline unchanged.',reset='same ot_rst_relay REGIONS3/SYNC_STAGES2/TREE_STAGES1; no reset or clock alteration'),existing_lec=dict(verdict=lec['verdict'],generated=lec['generated'],top=lec['top'],ports=lec.get('ports'),source_unchanged=True),geometry=dict(actual_verdict='FAIL: aspect5 and empty.575; not a hardened view',fill=.1762,r2r_max_um=221.35,external_max_um=404.988,unit_i0_station_max_um=401.246),rows=rows,flops=list(ff.values()),external=external)
(out/'soft_l2_homes.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['rows','flops','external']},indent=2))
