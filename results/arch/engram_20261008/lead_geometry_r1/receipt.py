#!/usr/bin/env python3
import hashlib,json,math
from pathlib import Path
W=Path('/srv/opentallas-scratch/engram-lead-geometry-r1')
O=Path('/srv/opentallas-scratch/claude/closure-loop/engram-lead-765470589-tt/routes/engram_lead_765470589_tt_cal/work/orfs/results/asap7/opentallas_ot_dsrom_engram_lead_producer_asap7_s81ph_engram_lead_765470589_tt_cal/base/3_2_place_iop.odb')
d=json.loads((W/'repaired_dump.json').read_text());points={}
for name,net,sig,io,boxes in d['bterms']:
 for layer,b in boxes:points.setdefault(net,[]).append((name,(b[0]+b[2])/2,(b[1]+b[3])/2))
rows=[]
for m in d['macros']:
 pts=[p for net,x,y,io,cap in m['pins'] for p in points.get(net,[])];cx=sum(p[1] for p in pts)/len(pts);cy=sum(p[2] for p in pts)/len(pts);b=m['bbox'];dist=math.hypot(max(b[0]-cx,0,cx-b[2]),max(b[1]-cy,0,cy-b[3]));rows.append(dict(name=m['name'],bbox_um=b,direct_block_pins=len(pts),pin_centroid_um=[cx,cy],pin_to_bank_distance_um=dist))
r=dict(schema='opentallas.engram-lead-geometry-probe.v1',source_commit='765470589',original_job='engram-lead-765470589-tt',rtl_change=False,added_cycles=0,outline_um=[324,216],outline_mm2=.069984,outline_area_delta_mm2=0,macro_count=8,macro_mm2=8*38.016*62.910/1e6,macro_area_delta_mm2=0,placement='4columns2rows;x70+50.1*c,y68+75*r; R0; LOCKED',gap_x_um=12.084,gap_y_um=12.090,residual_sliver_policy='block every residual positive gap<12um; none in selected geometry',macro_geometry=rows,original_odb=str(O),original_odb_sha256=hashlib.sha256(O.read_bytes()).hexdigest(),repaired_dump_sha256=hashlib.sha256((W/'repaired_dump.json').read_bytes()).hexdigest(),repaired_odb_sha256=hashlib.sha256((W/'repaired.odb').read_bytes()).hexdigest(),lint=json.loads((W/'lint.json').read_text()),remote_host='ot-agidock128',remote_objects=str(W),admission_reserved_gib=2,qualification='offline actual3_2ODB geometry only; unchanged source; no timing/routing/adoption claim; new physical intake requires Claude review',probe_failures_preserved=['probe.log (binary PATH)','probe-r2.log (LOCKED relocation)','probe-r3.log (Tcl stringcompare)'])
(W/'receipt.json').write_text(json.dumps(r,indent=1)+'\n')
