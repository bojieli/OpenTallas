import sys,json,gzip,hashlib,collections
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-qc-1101/tools/die_plan')
import schema as S
R=Path('/home/ubuntu/coord/tmp/stm-parent-review1131')
B=Path('/srv/opentallas-scratch/claude/wt/codex-qc-tload-protocol-1131/results/qc_stm_geometry_1131')
d=json.loads((R/'plan.json').read_text());P=S.Plan(d,R/'plan.json')
q=json.loads(gzip.decompress((B/'private_proposal_v2.json.gz').read_bytes()));g=json.loads(gzip.decompress((B/'native_graph_r5.json.gz').read_bytes()))
q['pins']=json.loads((B/'overlay/named_pin_locations.json').read_text())
native=json.loads((R/'native_port_inventory_review1500.json').read_text())
target='sl_W5_stm';part=P.parts[target];old=list(P.rect(target));w,h=q['outline_um'];origin=[old[0]+(old[2]-old[0]-w)/2,old[1]+(old[3]-old[1]-h)/2];new=[origin[0],origin[1],origin[0]+w,origin[1]+h]
proposed=[p['name'] for p in q['pins']]; actual={b.removesuffix('[0]') if len(row['bits'])==1 and b not in proposed and b.removesuffix('[0]') in proposed else b for row in native['ports'].values() for b in row['bits']}
pincheck=dict(native_bits=len(actual),proposed_bits=len(proposed),unique_proposed_bits=len(set(proposed)),missing=sorted(actual-set(proposed)),extra=sorted(set(proposed)-actual),status='PASS' if actual==set(proposed) and len(proposed)==len(actual) else 'FAIL')
assigned=[c for row in q['clock_assignments'].values() for c in row['actual_named_local_FFs']]
clockcheck=dict(status='NATIVE_CONSUMER_IDENTITY_ONLY',native_local_FFs=len(g['local_clock_cells']),advisory_named_FFs=len(assigned),unique_advisory_FFs=len(set(assigned)),missing=len(set(g['local_clock_cells'])-set(assigned)),extra=len(set(assigned)-set(g['local_clock_cells'])),forwarded_FFs={k:v for k,v in g['clock_ff_counts'].items() if k!='clk'},ROM_clock_roots=g['ROM_clock_roots'],export_roots=g['clock_export_roots'],qualified_estimated_clock_groups=False,physical_clock_source_assignment='NOT ASSERTED',timing='NOT RUN')
linked=[p for p in d['ports'] if any(p[s]['part']==target for s in ('src','dst'))]
def point(pt,bus):
 geom=P._type_geom(pt,bus)
 if geom is None:return None
 f,window,_,_=geom;pw,ph=P.ptype(pt)['outline_um'];c=sum(window)/2
 local={'N':[c,ph],'S':[c,0],'W':[0,c],'E':[pw,c]}[f]
 return list(P.to_die(pt,local))
rows=[]
for link in linked:
 side='src' if link['src']['part']==target else 'dst';other='dst' if side=='src' else 'src';bus=link[side]['bus'];peer=link[other]
 ps=[p for p in q['pins'] if p['name']==bus or p['name'].startswith(bus+'[')]
 if not ps:raise ValueError('proposal missing linked bus '+bus)
 cp=[sum(p[k] for p in ps)/len(ps)+origin[j] for j,k in enumerate(('x','y'))]
 oldp=point(target,bus);peerp=point(peer['part'],peer['bus']);
 if peerp is None: print('MISSING_PEER_GEOM',link['id'],peer)
 face=ps[0]['face'];axis=1 if face in 'NS' else 0
 rows.append(dict(id=link['id'],bus=bus,side=side,face=face,peer=peer,old_contact_center=oldp,proposed_contact_centroid=cp,peer_current_contact_center=peerp,normal_seam_gap_um=abs(cp[axis]-peerp[axis]) if peerp else None,centroid_L1_um=sum(abs(a-b) for a,b in zip(cp,peerp)) if peerp else None,width=link['width'],qualification='CONTEXT ONLY; no external pin/FF route or timing qualification'))
inside=new[0]>=old[0] and new[1]>=old[1] and new[2]<=old[2] and new[3]<=old[3]
collisions=[]
for n in P.parts:
 if n==target:continue
 r=P.rect(n)
 if max(new[0],r[0])<min(new[2],r[2])-1e-8 and max(new[1],r[1])<min(new[3],r[3])-1e-8:collisions.append(n)
report=dict(scope='PRIVATE centered candidate inside existing allocation; no canonical parent modification or CAD',part=target,source_type=part['type'],old_rect=old,private_centered_rect=new,private_origin=origin,inside_existing_allocation=inside,other_partition_overlaps=collisions,pincheck=pincheck,clockcheck=clockcheck,collector_reset=dict(existing_vertices=len(q['existing_collector_reset_geometry']['relays']),depth=q['existing_collector_reset_geometry']['depth'],own_depth=q['existing_collector_reset_geometry']['own_depth'],max_planned_hop_um=q['existing_collector_reset_geometry']['max_planned_relay_hop_um'],actual_placement='NOT RUN'),parent_interfaces=rows,parent_integration='UNQUALIFIED: resized faces no longer abut unchanged neighbours; explicit channel/endpoint model required before canonical adoption',canonical_pin_generation='canonical supported data windows plus free-track scalar contacts; exact17874; density peaks67/10um retained as WARN')
(R/'context_review.json').write_text(json.dumps(report,indent=2)+'\n')
fig=plt.figure(figsize=(15,10));a=fig.add_axes([.04,.12,.32,.77]);b=fig.add_axes([.42,.12,.54,.77])
for n in P.parts:
 r=P.rect(n);color='#e2e6e9' if n!=target else '#d48732'
 a.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc=color,ec='white',lw=.15))
 if r[2]>old[0]-1100 and r[0]<old[2]+1800 and r[3]>old[1]-1700 and r[1]<old[3]+1700:
  b.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc='#edf0f2',ec='#818a91',lw=.7));b.text((r[0]+r[2])/2,(r[1]+r[3])/2,n,ha='center',va='center',fontsize=7)
for ax in (a,b):
 ax.add_patch(Rectangle((old[0],old[1]),old[2]-old[0],old[3]-old[1],fill=False,ec='#ce7024',lw=2))
 ax.add_patch(Rectangle((new[0],new[1]),w,h,fc='#b7dfc4',ec='#087644',lw=1.5,alpha=.8));ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_xlabel('die x / um');ax.set_ylabel('die y / um')
for row in rows:
 p=row['proposed_contact_centroid'];v=row['peer_current_contact_center'];
 if v is None:continue
 b.plot([p[0],v[0]],[p[1],v[1]],color='#9d4d75',lw=.55,alpha=.6)
b.set_xlim(old[0]-1100,old[2]+1800);b.set_ylim(old[1]-1700,old[3]+1700);a.set_xlim(0,P.W);a.set_ylim(0,P.H)
a.set_title('Full frozen qwen_compute allocation\n377 existing parts; one private candidate',fontsize=10);b.set_title('Unchanged neighbour allocation +38 contact-centroid links\nOrange: original slot; green: centered PRIVATE frame',fontsize=10)
fig.suptitle('Measured native slw_stm_v3: parent context review — no canonical adoption / CAD',fontsize=14)
fig.text(.04,.035,'311.04 x613.44 fits inside the613.44 x1339.2 allocation without overlap.\nAll17874 actual port bits match. Estimated clock groups are not clock qualification.\nFreed interface corridors and upstream clock/reset/strap delivery remain an explicit parent model event.',fontsize=10)
fig.savefig(R/'parent_context.png',dpi=150);plt.close(fig)
print(json.dumps({'pincheck':pincheck,'inside':inside,'collisions':collisions,'interfaces':len(rows),'normal_gap_values':sorted(set(round(x['normal_seam_gap_um'],3) for x in rows if x['normal_seam_gap_um'] is not None)),'max_contact_centroid_distance':max(x['centroid_L1_um'] for x in rows if x['centroid_L1_um'] is not None),'clock_actual_vs_proposed':[len(g['local_clock_cells']),len(assigned),len(set(assigned))],'reset_vertices':report['collector_reset']['existing_vertices']},indent=2))
