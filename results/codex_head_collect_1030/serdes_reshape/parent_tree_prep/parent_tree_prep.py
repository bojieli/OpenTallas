import json,math
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=Path('/srv/opentallas-scratch/claude/wt/codex-head-collect-1030/results/codex_head_collect_1030/serdes_reshape');out=b/'parent_tree_prep';out.mkdir(exist_ok=True)
prod=json.load(open('/tmp/head_collect_review/parent_kp4_producers.json'));census=json.load(open('/tmp/head_collect_review/domain_census.json'))
def leaves(name,n,xs,y,rect,root):
 q,r=divmod(n,len(xs));return [dict(name=f'{name}_{i}',planned_clock_center_um=[x,y],actual_ff_demand=q+(i<r),planned_ff_region_um=rect,source_clock_port=root) for i,x in enumerate(xs)]
rec=[]
rec+=leaves('kp4_producers',951,[951],147.312,[943,32,960,115],'pma_rck')
rec+=leaves('syn_remainder',4767,[744,786,828,870,912],147.312,[720,4.32,940,142.56],'pma_rck')
rec+=leaves('prx',2176,[600,690],147.312,[550,4.32,720,142.56],'pma_rck')
rec+=leaves('rm_write',4112,[1728,1836,1944,2052],147.312,[1675,70,2100,142.56],'pma_rck')
rec+=leaves('dec_out',1493,[1705,1775],147.312,[1675,4.32,1815,65],'pma_rck')
rec+=leaves('dec_dly',7,[1455],147.312,[1439,35,1477,110],'pma_rck')
rec+=leaves('rx_misc',3,[1455],147.312,[1439,120,1477,142.56],'pma_rck')
core=[]
core+=leaves('enc',5925,[2145,2235,2325,2415,2505,2595],148.608,[2100,4.32,2650,142.56],'clk')
core+=leaves('ptx',2176,[2710,2820],148.608,[2650,4.32,2881.44,142.56],'clk')
for nm,n,x,rect in [('ring_read',590,1927,[1824.88,17.28,2030.08,62.64]),('rm_read',529,1840,[1675,70,2100,142.56]),('bout',515,1705,[1675,4.32,1760,65]),('bin',513,1927,[1824.88,17.28,2030.08,62.64])]:core+=leaves(nm,n,[x],148.608,rect,'clk')
core+=leaves('core_misc_control',55,[1450],148.608,[1439,120,1477,142.56],'clk')
fwd=leaves('forwarded_ring',2086,[1875,1980],40,[1824.88,17.28,2030.08,62.64],'fclk_in_coll_i0')
assert sum(x['actual_ff_demand'] for x in rec)==13509
assert sum(x['actual_ff_demand'] for x in core)==10303
macros=[dict(name='KP4',rect=[967.68,4.32,1244.16,142.56],halo=[963.36,0,1248.48,146.88]),dict(name='SRAM32',rect=[1252.908,17.292,1430.676,98.292],halo=[1248.588,12.972,1434.996,102.612]),dict(name='SRAM64',rect=[1486.188,34.572,1664.82,115.572],halo=[1481.868,30.252,1669.14,119.892])]
roots={'clk':[1442.88,77.76],'pma_rck':[1106.04,149.904],'fclk_in_coll_i0':[1927.392,2.656]}
trunks={}
for root,y in [('clk',148.608),('pma_rck',147.312)]:
 special=sorted(set([roots[root][0]]+[q['planned_clock_center_um'][0] for q in (core if root=='clk' else rec)]));xs=sorted(special+[86.4+172.8*i for i in range(17) if all(abs(86.4+172.8*i-z)>=4.32 for z in special)])
 trunks[root]=dict(root_um=roots[root],layer='HELD pending actual PG-lane selection',planned_buffer_centers_um=[[x,y] for x in xs],max_chain_center_leg_um=max([abs(a-z) for a,z in zip(xs,xs[1:])]+[abs(roots[root][1]-y)]))
x=dict(status='GEOMETRY_PREP_ONLY_NOT_PLACED_NOT_TIMED_NOT_PG_QUALIFIED',outline_um=[2885.76,1226.88],digital_strip_um=[0,0,2885.76,150],macros=macros,domain_roots=roots,counts=dict(clk=10303,pma_rck=13509,fclk_in_coll_i0=2086,kp4_internal=3237),leaves=dict(clk=core,pma_rck=rec,fclk_in_coll_i0=fwd),trunk_geometry=trunks,kp4_producers=dict(unique_ff=951,root='pma_rck',planned_centers_rect_um=[943,32,960,115],actual_native_instances=[q['inst'] for q in prod['source_ff']],worst_box_to_any_child_W_pin_um=112.248,child_internal_worst_um=285.585,combined_conservative_um=397.833,margin_to405_um=7.167,leaf_center_um=[951,147.312],max_leaf_to_box_um=124.312),constraints=['No RX period or clock qualification invented; PMA typed pad contract held until reviewed authority.','Counts measured from native shell; rectangles/stations are proposed placement input, never measured bins.','Actual source boot/reset FF delta must bind to its own actual net.','All clock cell sites/nets require actual PG clearance, legal DPL and actual rooted-tree dump before route.','Parent actual real-child-view STA must time all320 inputs/0unconstrained and combined producer reach<=405.','Core misc control55 locations are provisional; actual raw reset/start anchors take priority.','Do not substitute old216x194.4 child LEF/lib for newshape.'])
(out/'recipe.json').write_text(json.dumps(x,indent=1)+'\n')
fig=plt.figure(figsize=(20,7));gs=fig.add_gridspec(3,1,height_ratios=[1,1,2.5]);colors={'clk':'#1768AC','pma_rck':'#B6465F','fclk_in_coll_i0':'#438A5E'}
for idx,root in enumerate(['clk','pma_rck']):
 ax=fig.add_subplot(gs[idx]);ax.set_xlim(0,2885.76);ax.set_ylim(0,160);ax.set_aspect('equal');ax.axhspan(150,160,color='.85');
 for m in macros:
  a,c,d,e=m['halo'];ax.add_patch(Rectangle((a,c),d-a,e-c,fill=False,edgecolor='.65',linestyle='--'));a,c,d,e=m['rect'];ax.add_patch(Rectangle((a,c),d-a,e-c,color='.8'));ax.text((a+d)/2,(c+e)/2,m['name'],ha='center',fontsize=8)
 pts=trunks[root]['planned_buffer_centers_um'];ax.plot([p[0] for p in pts],[p[1] for p in pts],'.-',color=colors[root],lw=1)
 for q in x['leaves'][root]:
  a,c,d,e=q['planned_ff_region_um'];xp,yp=q['planned_clock_center_um'];ax.plot([xp,xp],[yp,(c+e)/2],color=colors[root],lw=.6);ax.text(xp,9,str(q['actual_ff_demand']),ha='center',fontsize=6,color=colors[root])
 rx,ry=roots[root];ax.plot(rx,ry,'*',color=colors[root],ms=11);ax.set_title(f'{root}: {x["counts"][root]} measured shell FF demand; proposed separate tree, spatial placement unqualified',loc='left',fontsize=10);ax.tick_params(labelsize=7)
ax=fig.add_subplot(gs[2]);ax.set_xlim(900,1700);ax.set_ylim(0,165);ax.set_aspect('equal');ax.axhspan(150,165,color='.85')
for m in macros:
 a,c,d,e=m['halo'];ax.add_patch(Rectangle((a,c),d-a,e-c,fill=False,edgecolor='.5',linestyle='--'));a,c,d,e=m['rect'];ax.add_patch(Rectangle((a,c),d-a,e-c,color='.8'));ax.text((a+d)/2,(c+e)/2,m['name'],ha='center')
a,c,d,e=x['kp4_producers']['planned_centers_rect_um'];ax.add_patch(Rectangle((a,c),d-a,e-c,fill=False,edgecolor=colors['pma_rck'],lw=2));ax.text(a-4,70,'951 producer FF\nproposed box\nall pma_rck',ha='right',va='center',fontsize=9)
for root in ['clk','pma_rck']:
 rx,ry=roots[root];ax.plot(rx,ry,'*',color=colors[root],ms=13);ax.text(rx,ry+4,root,ha='center',fontsize=9,color=colors[root])
ax.text(1106.04,73.44,'KP4 own recovered clock\n3237 internal FF; not core-grid demand',ha='center',fontsize=8)
ax.set_title('Macro-free producer box: worst parent box→W pin112.248 + child285.585 =397.833um <405; actual placement/STA still required',fontsize=10)
fig.suptitle('HEAD SerDes parent physical-tree PREP — proposed geometry, no period/PG/timing qualification',fontsize=13);fig.tight_layout();fig.savefig(out/'preview.png',dpi=140)
print(out)
