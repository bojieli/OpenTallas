"""Disabled source/geometry exploration. No GEN or physical-flow invocation."""
import copy, json, re, sys
from pathlib import Path

B=Path(__file__).resolve().parent
src=Path(sys.argv[1]); p=json.loads(src.read_text()); q=copy.deepcopy(p)
t=p['partition_types']['coll_core']; hs=copy.deepcopy(t['hard_cores'])
groups={}
for h in hs:
    n=h['module']; groups.setdefault(n,[]).append(h)
codec=groups['ot_sram_1r1w_64x512_m1_r2c2']
others=groups['ot_sram_1r1w2c_64x546_m1']+groups['ot_sram_1r1w_32x546_m1']+groups['ot_sram_1r1w_512x128_m4_r2c2']
placed=[]
for j in range(4):
    for col,kind in [(17.28,'pf'),(240.48,'xf')]:
        placed.append(dict(inst=f'u_bound.u_io_collective_u_io_u_collective.u_coll.g_{kind}[{j}].u_fs',module='ot_coll_fold_slice',origin_um=[col,17.28+j*198.72],outline_um=[180,180],orient='R0',halo_um=4.32,view_status='CURRENT_VIEW_UNQUALIFIED; old180square footprint/ABI only'))
for j,h in enumerate(codec[:4]):
    h['origin_um']=[17.28 if j<2 else 240.48,829.44+(j%2)*95.04]; placed.append(h)
for j,h in enumerate(codec[4:]):
    # Actual selected SRAM LEF declares SYMMETRY X Y R90. Explicit rotated body.
    h['origin_um']=[677.376,17.28+j*207.36];h['orient']='R90';h['unrotated_outline_um']=h['outline_um'];h['outline_um']=list(reversed(h['outline_um']));placed.append(h)
y=17.28
for h in others:
    h['origin_um']=[463.68,round(y,6)]; placed.append(h);y+=h['outline_um'][1]+12.96
def rect(h):
    x,y=h['origin_um'];w,z=h['outline_um'];a=h['halo_um'];return [x-a,y-a,x+w+a,y+z+a]
errors=[]
for i,a in enumerate(placed):
    ar=rect(a)
    if not(0<=ar[0]<ar[2]<=760.32 and 0<=ar[1]<ar[3]<=1032.48):errors.append(dict(kind='HALO_OUTSIDE_ACTUAL_CORE',inst=a['inst'],rect=ar))
    for b in placed[:i]:
        br=rect(b)
        if min(ar[2],br[2])-max(ar[0],br[0])>1e-7 and min(ar[3],br[3])-max(ar[1],br[1])>1e-7:errors.append(dict(kind='HALO_OVERLAP',a=a['inst'],b=b['inst']))
assert len(placed)==29 and not errors,errors
for part in q['partitions']:
    if part['name']=='coll_core':part['origin_um']=[803.52,8985.6]
    if part['name']=='coll_f2':part['origin_um']=[803.52,7715.52]
    if part['name']=='coll_ucie':part['origin_um']=[0,8156.16]
q['partition_types']['coll_core']['outline_um']=[760.32,1036.8]
q['partition_types']['coll_core']['hard_cores']=placed
q['partition_types']['coll_ucie']['outline_um']=[803.52,1347.84]
shared=q['partition_types']['coll_ft__cla4a25d77'];shared['outline_um']=[760.32,1270.08]
for slot in shared['ft_slots']:slot['stations']=4
# Do not relabel stale physical and source-derived contracts as current.
(B/'DISABLED_PARENT_PLAN_UNRELEASED.json').write_text(json.dumps(q,separators=(',',':'))+'\n')
regions=[]
for j in range(4):
    y=17.28+j*198.72
    for name,box in [('PF_lo_hi_capture',[4.32,y,12.96,y+180]),('PF_sum_and_XF_rank_capture',[205.92,y,231.84,y+180]),('XF_sum_capture',[429.12,y,455.04,y+180])]:
        regions.append(dict(name=f'{name}_{j}',box_um=box,source_only=True,added_registers=0,meaning='Homes for existing named slice registers only; no added stage; complete SRAM/reader predecessor graph still must satisfy reach.'))
def gap(a,b):return max(0,a[0]-b[2],b[0]-a[2])+max(0,a[1]-b[3],b[1]-a[3])
graph=[]
# Conservative box-to-box LOWER BOUNDS; useful failures without pretending to place FFs.
for j in range(4):
    cap=regions[j*3]['box_um']
    for h in placed:
        if 'u_pring.' in h['inst']:
            x,y=h['origin_um'];w,z=h['outline_um'];lb=gap([x,y,x+w,y+z],cap)
            graph.append(dict(bus=f'P_ring_to_lohi_slice{j}',source=h['inst'],capture_region=regions[j*3]['name'],bits=256,box_lower_bound_um=round(lb,6),pass_necessary_405=lb<=405,note='All four depth banks can supply each128-bit slice; no invented output register. Pin-aware Manhattan can only be longer.'))
report=dict(status='DISABLED_GEOMETRY_CANDIDATE_FAIL_SOURCE_REACH',macro_count=29,body_and_halo_errors=errors,outline_um=[760.32,1036.8],actual_core_box_um=[0,0,760.32,1032.48],macros=placed,existing_register_region_proposals=regions,per_bus_lower_bounds=graph,failed_lower_bounds=sum(not a['pass_necessary_405']for a in graph),channels=[dict(box_um=[201.6,0,236.16,1032.48],width_um=34.56),dict(box_um=[424.8,0,459.36,1032.48],width_um=34.56),dict(box_um=[646.632,0,673.056,1032.48],width_um=26.424)],coupled_parent=dict(core_origin_um=[803.52,8985.6],core_north_unchanged=10022.4,both_shared_FT_outline_um=[760.32,1270.08],F1_origin_um=[803.52,6445.44],F2_origin_um=[803.52,7715.52],F0_F3_and_public_faces_unchanged=True,ucie_origin_um=[0,8156.16],ucie_outline_um=[803.52,1347.84],ucie_core_W_E_window_offset_um=829.44,die_edge_unchanged=True,partition_types_added=0),station_price=dict(old_stations=3,new_stations=4,each_shared_copy_straight_lower_bound_old_um=423.36,new_um=317.52,extra_cycles_each_copy=1,extra_cycles_path_crossing_both=2,cycle_ps=833,zero_new_edge_core_height_lower_bound_um=1146.96,note='Exact<=405 hop criterion proves existing3stations insufficient. Actual paired bit sites, padding, clocks/reset/boot and programme not rederived; no release or latency-model update claimed.'),unresolved=['P-ring-to-PF lower bounds fail: revise lane/bank/capture grouping; no blind origin insertion','All other SRAM->reader and reader->macro pin-aware pairs still require complete source graph','Clock/reset/START contracts and public clocks stale in disabled plan: rederive matched current-tool source event before any GEN','Proposed4station copies require true calendar/programme/model+2edge price, not only JSON edit','UCIe PHY/PG/native-clock/current-view qualification unchanged HOLD','Fold180square source/function/clock/reset/view qualification absent; old view footprint-only','Channel track occupancy and per-bit pin capacity not measured; no fake PASS'])
(B/'CANDIDATE_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(9,12))
for ch in report['channels']:
    x,y,z,v=ch['box_um'];ax.add_patch(Rectangle((x,y),z-x,v-y,color='#eef6fa'))
for h in placed:
    x,y=h['origin_um'];w,z=h['outline_um'];r=rect(h);fold=h['module']=='ot_coll_fold_slice'
    ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,edgecolor='#888',linewidth=.5))
    ax.add_patch(Rectangle((x,y),w,z,color='#89b4d8'if fold else'#d9bf8d',ec='black',lw=.6))
    label=h['inst'].split('.u_coll.')[-1]if fold else h['inst'].split('.')[-2]
    ax.text(x+w/2,y+z/2,label,ha='center',va='center',fontsize=6,rotation=90 if h['orient']=='R90'else 0)
for r in regions:
    x,y,z,v=r['box_um'];ax.add_patch(Rectangle((x,y),z-x,v-y,color='#e69483',alpha=.65))
ax.set(xlim=(0,760.32),ylim=(0,1036.8),aspect='equal',xlabel='CORE local x (um)',ylabel='CORE local y (um)',title='DISABLED CORE source candidate: 29 actual/reference rectangles\nHalo/body fit only; P-ring→PF reach FAIL; no GEN/P&R')
fig.tight_layout();fig.savefig(B/'candidate_macro_regions.png',dpi=140);plt.close(fig)
print(json.dumps({'macros':len(placed),'halo_errors':len(errors),'source_lower_bound_fails':report['failed_lower_bounds'],'max_lower_bound_um':max(a['box_lower_bound_um']for a in graph)}))
