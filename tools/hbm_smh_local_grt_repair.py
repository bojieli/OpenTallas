#!/usr/bin/env python3
"""Bound a source-faithful GRT continuation to actual retained congestion boxes."""
import argparse, collections, hashlib, json, re
from pathlib import Path
from uarch_model import hbm_smh_local_grt_price

def prepare(report, out):
    raw=report.read_bytes(); text=raw.decode(); rows=[]; classes=collections.Counter()
    for chunk in text.split('violation type: ')[1:]:
        cap,usage,ov=map(int,re.search(r'capacity:(\d+) usage:(\d+) congestion:(\d+)',chunk).groups())
        box=list(map(float,re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\)',chunk).groups()))
        nets=re.search(r'srcs: (.*)',chunk).group(1).split()
        assert usage-cap==ov and cap>=0
        for n in nets:
            cls=('xwrite' if 'u_bld' in n or 'bout' in n or '.blk_' in n or '.bf_' in n else
                 'gather' if '.g_gl' in n else 'row_landing' if '.u_rl.' in n else
                 'clock' if 'clknet' in n else 'blockdot' if '.u_bd.' in n else
                 'BF16' if '.u_tc.' in n else 'mapped_buffer_or_logic_unattributed')
            classes[cls]+=1
        rows.append(dict(direction=chunk.splitlines()[0],capacity=cap,usage=usage,overflow=ov,bbox=box,nets=nets))
    assert rows
    # One measured 0.57um GCell halo. Merge overlaps so reservations do not stack.
    boxes=[[round(v-.57 if i<2 else v+.57,3) for i,v in enumerate(r['bbox'])] for r in rows]
    changed=True
    while changed:
        changed=False
        for i in range(len(boxes)):
            for j in range(i+1,len(boxes)):
                a,b=boxes[i],boxes[j]
                if a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]:
                    boxes[i]=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
                    boxes.pop(j);changed=True;break
            if changed:break
    model=hbm_smh_local_grt_price(boxes)
    assert model['added_physical_tracks']==0 and model['repair_area_fraction']<.002
    t=['# Actual congestion boxes + one GCell halo; reserve capacity, never invent tracks.',
       'if {$::env(ROUTING_LAYER_ADJUSTMENT) != 0.25} {error "Unexpected retained global routing reservation"}']
    for box in boxes:
        for layer in range(2,7):
            t.append('set_global_routing_region_adjustment {'+' '.join(map(str,box))+'} -layer M'+str(layer)+' -adjustment 0.5')
    out.mkdir(parents=True,exist_ok=False)
    (out/'local_channels.tcl').write_text('\n'.join(t)+'\n')
    (out/'localization.json').write_text(json.dumps(dict(report_sha256=hashlib.sha256(raw).hexdigest(),
        regions=len(rows),overflow=sum(r['overflow'] for r in rows),source_net_class_occurrences=classes,
        layer_attribution='Report serializes Layer -; final per-layer flow totals retained, no invented per-box layer.',
        macro_geometry=dict(x=[112.32,207.144],leaf1_y=[34.56,79.92,125.28,170.64],leaf0_y=[293.76,339.12,384.48,429.84],height=41.04,
            obstructions='LEF M1/M2/M3 full footprint; M4 x0.072..94.752; all unchanged'),
        model=model,rows=rows,adopt=False),indent=2)+'\n')
    (out/'congestion.rpt').write_bytes(raw)
    return model

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.report,a.out),indent=2))
