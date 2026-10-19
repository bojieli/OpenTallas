#!/usr/bin/env python3
"""Read-only actual placed-net and exact payload-hop region report."""
import json,sys,hashlib
from pathlib import Path
p=Path(sys.argv[1]);rows=[ln.split('\t') for ln in p.read_text().splitlines() if ln]
dbu=float(next(r[1] for r in rows if r[0]=='DBU'))
odb=next((r[1] for r in rows if r[0]=='ODB'),'not_recorded')
placed=Path(odb).name in ['4_cts.odb','3_place.odb','3_3_place_gp.odb']
hop=[{'name':r[1],'box_um':[int(v)/dbu for v in r[2:6]]} for r in rows if r[0]=='HOPCELL']
box=[272.16,141.48,289.44,152.28]
viol=[c for c in hop if any(c['box_um'][i]<box[i]-.001 for i in [0,1]) or any(c['box_um'][i]>box[i]+.001 for i in [2,3])]
nets=[{'name':r[1],'terminals':int(r[2]),'unknown_term_positions':int(r[3]),'box_um':[int(x)/dbu for x in r[4:8]],'hpwl_um':int(r[8])/dbu} for r in rows if r[0]=='NETSPAN']
groups={}
for name,pat in [('hop_payload','sd_hop_payload['),('address_apx','apx_'),('address_apb','apb_'),('sd_other','u_sd.'),('reset','__ot_rlv')]:
 ns=[n for n in nets if pat in n['name']];groups[name]={'count':len(ns),'max_hpwl_um':max((n['hpwl_um'] for n in ns),default=None),'over405':sum(n['hpwl_um']>405 for n in ns),'top20':sorted(ns,key=lambda n:-n['hpwl_um'])[:20]}
out={'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'odb':odb,'placement_stage_present':placed,'hop_mapped_flops':len(hop),'hop_claimed_region_um':box,'hop_cells_outside_region':viol,'hop_region_qualified':placed and len(hop)==291 and not viol,'net_groups':groups,'qualification':'Actual HPWL only; not timing or routing/pin-access DRC proof. Reset and address controls are reported separately.'}
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n');print('SH_PLACED_SPANS',json.dumps({k:v for k,v in out.items() if k not in ['net_groups','hop_cells_outside_region']}))
