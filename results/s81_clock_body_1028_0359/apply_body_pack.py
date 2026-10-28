import json,re,shutil,math
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-s81-owner-0359/clock_body')
S=Path('/srv/opentallas-scratch2/claude/die-s81-7/kit_G/clock')
O=R/'clock_G_body';O.mkdir(exist_ok=False)
for p in S.iterdir():
 if p.is_file():shutil.copy2(p,O/p.name)
t=json.load(open(S/'tree.json')); old=t['sites']; new=json.load(open(R/'packed_G/base_body_sites.json'))['sites'];assert set(old)==set(new)
t['sites']=new
for k,b in t['node_buf'].items(): t['nodes'][k]['x'],t['nodes'][k]['y']=new[b]
t['meta']['body_pack']={'source':'packed_G/base_body_sites.json','max_move_um':2.222,'topology_and_tap_locations_unchanged':True,'old_routed_receipt_transfers':False}
(O/'tree.json').write_text(json.dumps(t))
text=(S/'ctree.tcl').read_text(); seen=[]
def sub(m):
 n=m[1];seen.append(n);x,y=new[n];return f'place_inst -name {n} -location {{{x:.3f} {y:.3f}}} -status PLACED'
text=re.sub(r'place_inst -name (\S+) -location \{[^}]+\} -status PLACED',sub,text);assert set(seen)==set(new) and len(seen)==len(new)
(O/'ctree.tcl').write_text(text)
# Same cell count/load and topology: calibrated per-wire length sensitivity,
# with absolute edge perturbations retained as a model-error allowance.
k1=.11381820833198633;k2=.00009322313191757747
pa=t['parent_of'];delta={};bound={};edges=[]
for n,p in pa.items():
 a=sum(abs(x-y) for x,y in zip(old[n],old[p]));b=sum(abs(x-y) for x,y in zip(new[n],new[p])); d=k1*(b-a)+k2*(b*b-a*a)
 delta[n]=d;bound[n]=abs(d);edges.append({'sink':n,'source':p,'old_l1_um':a,'new_l1_um':b,'delta_ps_model':d})
root=next(n for n in old if n not in pa);c={root:0};ab={root:0}
def accum(n):
 if n not in c:accum(pa[n]);c[n]=c[pa[n]]+delta[n];ab[n]=ab[pa[n]]+bound[n]
for n in old:accum(n)
regions={};tap=[]
for a in t['taps']:
 n=t['node_buf'][str(a['node'])];x={'port':a['port'],'part':a['part'],'delta_ps_model':c[n],'absolute_edge_allowance_ps':ab[n]};tap.append(x);regions.setdefault(a['part'],[]).append(c[n])
report={'scope':'PREBUILD_ANALYTIC_PERTURBATION_ONLY_NOT_ROUTED','buffers':len(new),'max_move_um':max(math.dist(old[n],new[n]) for n in old),'wire_length_old_um':sum(x['old_l1_um'] for x in edges),'wire_length_new_um':sum(x['new_l1_um'] for x in edges),'max_edge_ps_delta':max(abs(x) for x in delta.values()),'tap_delta_range_ps':[min(x['delta_ps_model'] for x in tap),max(x['delta_ps_model'] for x in tap)],'max_root_path_absolute_allowance_ps':max(ab.values()),'max_region_delta_spread_ps':max(max(v)-min(v) for v in regions.values()),'calibration':[k1,k2],'unchanged':['RTL','tap coordinates','buffer count','topology','stage count'],'adoption':'HOLD_FOR_REVIEW_AND_FRESH_ROUTED_CA'}
(R/'body_price.json').write_text(json.dumps(report,indent=2));(R/'body_edge_price.json').write_text(json.dumps(edges));(R/'body_tap_price.json').write_text(json.dumps(tap));print(json.dumps(report,indent=2))
