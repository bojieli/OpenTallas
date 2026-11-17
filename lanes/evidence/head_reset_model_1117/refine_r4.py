from pathlib import Path
import json,sys,collections,hashlib
L=Path('/srv/opentallas-scratch2/claude/head-die-r');O=L/'reset_feasibility_r4_1117';f=L/'prep21z20NF15c/prep/source_plan.json';P=json.load(f.open());R=json.load((O/'feasibility.json').open());S={c:json.load(open(L/'nf15c_real4'/f'spine_{c}.json'))['parts'] for c in ['TT','FF']}
sys.path.insert(0,str(L/'nf15e_e7/code/tools/die_plan'));import schema as SC,reset_tree as RT
p=SC.Plan(P,str(f));needed={d[t] for d in R['rows'] if d['classification']=='LOCAL_TAP_OPTIMISTIC_CANDIDATE' for t in ['src_type','dst_type']};g={}
for tn in sorted(needed):
 taps={name:[x,y] for name,x,y in RT._taps(p,tn)};outs={name:[x,y] for name,x,y in RT.out_pins(p,tn)}
 g[tn]=dict(taps=taps,outs=outs,reset_in=list(RT.in_pin(p,tn)),start_in=list(RT.start_in_pin(p,tn)),radius=P['partition_types'][tn]['clock'].get('tap_radius_um',250))
cands=[]
for d in R['rows']:
 if d['classification']!='LOCAL_TAP_OPTIMISTIC_CANDIDATE':continue
 a=g[d['src_type']];b=g[d['dst_type']];sp=(d['source_port'] or '').replace('start_o_','rst_o_');xy=a['outs'].get(sp);z=b['reset_in' if d['bus']=='arst_n' else 'start_in'];opts=[]
 if xy:
  for sn,sxy in a['taps'].items():
   sd=sum(abs(x-y) for x,y in zip(sxy,xy))
   if sd>a['radius']:continue
   for dn,dxy in b['taps'].items():
    dd=sum(abs(x-y) for x,y in zip(dxy,z))
    if dd>b['radius']:continue
    try:
     dt=(S['TT'][d['src']]['taps'][sn]['offset_ps']-S['TT'][d['src']]['taps'][d['src_clock']['root']]['offset_ps'])-(S['TT'][d['dst']]['taps'][dn]['offset_ps']-S['TT'][d['dst']]['taps'][d['dst_clock']['root']]['offset_ps'])
     df=(S['FF'][d['src']]['taps'][sn]['offset_ps']-S['FF'][d['src']]['taps'][d['src_clock']['root']]['offset_ps'])-(S['FF'][d['dst']]['taps'][dn]['offset_ps']-S['FF'][d['dst']]['taps'][d['dst_clock']['root']]['offset_ps'])
    except KeyError:continue
    if d['tt_setup']-dt>=-42 and d['ff_hold']+df>=0:opts.append(dict(source_tap=sn,receiver_tap=dn,source_branch_um=sd,receiver_branch_um=dd,tt_setup=d['tt_setup']-dt,ff_hold=d['ff_hold']+df))
 cands.append(dict(seam=d['seam'],source_type=d['src_type'],receiver_type=d['dst_type'],source_cell=d['src_cell'],receiver_cell=d['dst_cell'],source_xy=xy,receiver_xy=z,candidates=opts,verdict='GEOMETRY_RADIUS_CANDIDATE' if opts else 'NO_RADIUS_FEASIBLE_TAP'))
groups=collections.defaultdict(list)
for d in R['rows']:groups[(d['src'],d['source_port'])].append(d)
ints=[]
for (src,port),rows in sorted(groups.items()):
 lo=max(0,max(-x['ff_hold'] for x in rows));hi=min(x['tt_setup']+42 for x in rows)
 ints.append(dict(source=src,port=port,receivers=[x['seam'] for x in rows],required_ff_delay_ps=lo,available_tt_delay_ps=hi,max_tt_to_ff_delay_ratio=hi/lo if lo else None,verdict='NEEDS_CHARACTERIZED_DELAY' if lo else 'BASELINE_HOLD_PASS'))
neg=[x for x in ints if x['required_ff_delay_ps']];out=dict(schema='opentallas.head_reset_draft_rows.v1',notice='Draft necessary conditions only, no active plan changes. No arbitrary delay implemented. Clock candidates preserve old localtree delays; radius feasibility alone does not establish actual routing/macro clearance or per-type uniform feasibility. A proposed tap reparent must satisfy ALL instances of its type/cell before adoption.',summary=dict(optimistic_rows=len(cands),radius_feasible=sum(bool(x['candidates']) for x in cands),source_nets=len(ints),source_nets_need_delay=len(neg),min_shared_net_ratio=min(x['max_tt_to_ff_delay_ratio'] for x in neg)),geometry_draft=cands,delay_intervals=ints)
(O/'draft_rows.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out['summary']));print('WORST_INTERVAL',json.dumps(min(neg,key=lambda x:x['max_tt_to_ff_delay_ratio'])));
