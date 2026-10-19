"""One finite bottom-up real native clock-family comparison in frozen slots.
No padding, source implementation, EDA, or physical-phase credit.
"""
import json,gzip,pathlib,re,collections,math
P=pathlib.Path(__file__).parent;scope={'__file__':str(P/'path_budget.py'),'__name__':'native_budget_reuse'}
exec((P/'path_budget.py').read_text().split('by_source=')[0],scope)
plan=scope['plan'];native=scope['native'];stage=scope['stage']
from dft.liberty import read_liberty,parse_function,evaluate,expr_vars
L={c:read_liberty(sorted((P/'kit/inputs/native_libs').glob('*'+c+'*'))) for c in ('TT','FF')}
txt=(P/'input/cells.lef').read_text();lef={}
for z in re.finditer(r'^MACRO (\S+)\n(.*?)^END \1\s*$',txt,re.M|re.S):
 body=z[2];size=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',body);pins={}
 for q in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1\s*$',body,re.M|re.S):
  rs=[list(map(float,r)) for r in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',q[2])]
  if rs:
   b=max(rs,key=lambda v:(v[2]-v[0])*(v[3]-v[1]));pins[q[1]]=((b[0]+b[2])/2,(b[1]+b[3])/2)
 lef[z[1]]=dict(w=float(size[1]),h=float(size[2]),pins=pins)
def cap(c,n,p):
 v=native[c][plan[n]['master']][p]['cap'];assert v;return [min(v),max(v)]
def point(n,p):
 x,y=lef[plan[n]['master']]['pins'][p];b=plan[n]['bbox'];return b[0]+x,b[1]+(y if plan[n]['orient']=='R0' else .27-y)
def rmst(ps):
 seen={0};edges=[]
 while len(seen)<len(ps):
  d,a,b=min((abs(ps[a][0]-ps[b][0])+abs(ps[a][1]-ps[b][1]),a,b) for a in seen for b in range(len(ps)) if b not in seen);seen.add(b);edges.append([a,b,d])
 return edges
families=[]
for m,c in L['TT'].items():
 if not m.startswith('BUFx') or m not in lef or lef[m]['w']>lef['BUFx24_ASAP7_75t_R']['w']+1e-10:continue
 if c['ff'] or c['latch']:continue
 for co in ('TT','FF'):
  f=parse_function(L[co][m]['pins']['Y']['function']);assert expr_vars(f)=={'A'} and all(evaluate(f,{'A':v})==v for v in (False,True))
 families.append(m)
families.sort(key=lambda m:(L['TT'][m]['area'],m))
ffs=[n for n,v in plan.items() if L['TT'][v['master']]['ff']];clkcost=json.load(open(P/'kit/inputs/clock_cost.json'));opens=[r['instance'] for r in clkcost['rows'] if r['open_output_clock_load']]
assert len(ffs)==2782 and len(opens)==110
leaves=[[] for _ in range(128)]
for i,n in enumerate(sorted(ffs+opens,key=lambda n:plan[n]['bbox'])):leaves[min(127,i*128//2892)].append(n)
children={f'MODEL_clock_l2_{i}':[(n,next(p for p,z in L['TT'][plan[n]['master']]['pins'].items() if z['clock']) if n in ffs else 'A') for n in ns] for i,ns in enumerate(leaves)}
children.update({f'MODEL_clock_l1_{i}':[(f'MODEL_clock_l2_{i*8+j}','A') for j in range(8)] for i in range(16)})
children['MODEL_clock_l0_0']=[(f'MODEL_clock_l1_{i}','A') for i in range(16)]
rows=[];refused=[]
for root,cs in children.items():
 assert len(cs)<=32;oldmaster=plan[root]['master'];trials=[];chosen=None
 for master in families:
  plan[root]['master']=master;points=[point(root,'Y')]+[point(n,p) for n,p in cs];tree=rmst(points);length=sum(e[2] for e in tree);bycorner={};bad=[]
  for co in ('TT','FF'):
   v=[cap(co,n,p) for n,p in cs];load=[sum(q[k] for q in v)+length*.145426 for k in (0,1)];s=stage(co,root,'Y',load)
   # Every receiver's native input-slew domain must contain the source waveform
   # interval. Actual wire waveform remains a separate positive obligation.
   if s['status'].startswith('REFUSE'):bad.append(co+':LOAD_DOMAIN')
   elif not s.get('output_wave_ps'):bad.append(co+':NO_WAVE')
   else:
    for n,p in cs:
     if p=='A':domains=[(t['x'][0],t['x'][-1]) for t in native[co][plan[n]['master']]['Y']['tables'] if t['related']=='A']
     else:domains=[(t['x'][0],t['x'][-1]) for out,vv in native[co][plan[n]['master']].items() for t in vv['tables'] if t['related']==p]
     assert domains,(co,n,p)
     lo=max(q[0] for q in domains);hi=min(q[1] for q in domains)
     if not(lo<=s['output_wave_ps'][0]<=s['output_wave_ps'][1]<=hi):bad.append(co+':RECEIVER_WAVE_DOMAIN');break
   maxcap=native[co][master]['Y']['cap'];bycorner[co]=dict(native_cell=s,nominal_total_load_fF=load)
  trials.append(dict(master=master,refusals=bad))
  if not bad:chosen=dict(driver=root,master=master,old_master=oldmaster,children=[dict(cell=n,pin=p) for n,p in cs],native_RMST_um=length,nominal_clock_wire_fF=length*.145426,corners=bycorner,rejected_smaller_native_trials=trials[:-1]);break
 if chosen is None:
  plan[root]['master']=oldmaster;refused.append(dict(driver=root,all_trials=trials));continue
 rows.append(chosen)
functional=sum(L['TT'][r['master']]['area'] for r in rows);inventory=collections.Counter(r['master'] for r in rows)
oldtotal=json.load(open(P/'model.json'))['native_area_um2'];summary=dict(schema='int8.source_owned.finite_clock_family.v1',status='NOMINAL_TABLE_COMPARISON_ONLY_ACTUAL_RC_PHASE_PG_OPEN' if not refused else 'FINITE_NATIVE_FAMILY_REFUSAL',families_considered=families,native_function_TT_FF=True,selected_trees=len(rows),refused_trees=len(refused),inventory=dict(inventory),all_real_sink_inputs=2892,genuine_unary_open_loads=110,functional_clock_area_um2=functional,total_clock_area_including_retained_loads_um2=functional+13.31154,total_model_area_um2=oldtotal-63.423+functional,all_cells=12491,native_PG_terms=24982,RMST_clock_wire_um=sum(r['native_RMST_um'] for r in rows),clock_root_native_input_cap_fF={c:cap(c,'MODEL_clock_l0_0','A') for c in ('TT','FF')},actual_root_waveform=None,allFF_early_late_arrivals=None,allFF_TT_FF_spread=None,actual_wire_minmax_delay=None,actual_wire_waveform=None,joint_clock_signal_PG_tracks=None,all_native_pulse_checks=None,qualification=False)
(P/'clock_family_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(P/'clock_family_compare.json.gz','wt') as f:json.dump(dict(summary=summary,selected=rows,refused=refused),f)
print(json.dumps(summary,indent=2))
