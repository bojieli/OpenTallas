import json,math
from pathlib import Path
p=json.load(open('/tmp/qcclock0336/plan_qc45.json'));out={'scope':'Paired geometry PREP impact only. Actual hard_cores distinguished from planned contents reworkenvelopes; no plan edit or cellcapacity claim.','types':{}}
for typ,newh in [('coll_s',665.28),('coll_n',717.12)]:
 t=p['partition_types'][typ];hs=t.get('hard_cores',[]);proposed=[]
 for i,h in enumerate(hs):
  # Actual 12native memories in4columns,3rows; preserves LEF+trackoffset but explicitly relocates.
  col=i%2+(i//6)*2;row=(i%6)//2;xy=[17.28+194.4*col,17.28+103.68*row];w,ht=h['outline_um'];proposed.append({'inst':h['inst'],'lef':h['lef'],'old_origin_um':h['origin_um'],'candidate_origin_um':xy,'outline_um':[w,ht],'track_offset_um':h.get('track_offset_um'),'old_to_new_manhattan_um':sum(abs(a-b) for a,b in zip(xy,h['origin_um']))})
 box_bad=[h['inst'] for h in proposed if h['candidate_origin_um'][0]+h['outline_um'][0]+4.32>t['outline_um'][0] or h['candidate_origin_um'][1]+h['outline_um'][1]+4.32>newh]
 overlaps=[]
 for i,a in enumerate(proposed):
  ax,ay=a['candidate_origin_um'];aw,ah=a['outline_um']
  for b in proposed[i+1:]:
   bx,by=b['candidate_origin_um'];bw,bh=b['outline_um']
   if ax-4.32<bx+bw+4.32 and bx-4.32<ax+aw+4.32 and ay-4.32<by+bh+4.32 and by-4.32<ay+ah+4.32:overlaps.append([a['inst'],b['inst']])
 out['types'][typ]={'outline_before_um':t['outline_um'],'outline_proposal_um':[t['outline_um'][0],newh],'actual_memory_area_um2':sum(h['outline_um'][0]*h['outline_um'][1] for h in hs),'native_hardcore_count':len(hs),'planned_contents_envelopes_not_sealed_hardmacros':[h for h in t['contents'] if h.get('status')=='rework'],'candidate_macro_only_repack':proposed,'halo_um':4.32,'out_of_outline':box_bad,'halo_overlap_pairs':overlaps,'capacity_verdict':'MACRO_ONLY_FIT' if not box_bad and not overlaps else 'FAIL','unresolved':['all codec/datapath related FF timing/reach', 'forwarded clocks/CA and reset topology', 'sourcecell/40pctreserve from existing kit area report', 'FTstations and boundaryFF footprint', 'PG/IR and islandOBS', 'full-bit seam pin alignment and added cycles']}
Path('/tmp/qcclock0336/collar_neighbor_impact.json').write_text(json.dumps(out,indent=2)+'\n')
print({k:(v['capacity_verdict'],v['actual_memory_area_um2']) for k,v in out['types'].items()})
