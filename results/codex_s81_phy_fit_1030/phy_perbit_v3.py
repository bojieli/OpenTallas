"""Place the ES0 FT0 candidate bit stations on actual ASAP7 sites (estimate)."""
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
pins=json.loads((ROOT/'ft0_native_pins.json').read_text())
W=2885.76
PW=.054
PH=.270
ROWS=12
Y0=round((70-ROWS*PH/2)/PH)*PH
MAXY=max(q[2] for q in pins)
FACE=4.32+1.080/2
HIGH_LENGTH=W-2*FACE+2*(MAXY-70)

def snap_center(x,width):
    return round((x-width/2)/PW)*PW+width/2

def boxes_overlap(a,b):
    return min(a[2],b[2])>max(a[0],b[0])+1e-7 and min(a[3],b[3])>max(a[1],b[1])+1e-7

stages={j:[] for j in range(9)}
chains=[]
endpoint_rows={}
for bit,layer,piny in pins:
    width=1.404 if bit==512 else 1.080
    y_edge=round((piny-PH/2)/PH)*PH+PH/2
    # Native PG pin avoidance can place >2 bits within a .270um row.
    # Allocate a distinct legal boundary column for every such capture.
    row_key=round(y_edge/PH)
    column=endpoint_rows.get(row_key,0)
    endpoint_rows[row_key]=column+1
    edge=4.32+width/2+column*1.62
    chain=[]
    for j in range(9):
        if j==0:
            x,y=W-edge,y_edge
        elif j==8:
            x,y=edge,y_edge
        else:
            high_x=FACE+HIGH_LENGTH*j/8-(MAXY-70)
            # A monotone bank of ~82um at every station. The middle bank changes
            # handedness, shortening the central hop for the lower pin rows;
            # equal centreline interpolation would collapse every bit at j=4.
            coefficient=.75 if j<=4 else -.75
            x=W-(high_x+coefficient*(MAXY-piny))
            x=snap_center(x,width)
            y=Y0+(bit%ROWS+.5)*PH
        box=[round(x-width/2,6),round(y-PH/2,6),round(x+width/2,6),round(y+PH/2,6)]
        rec=dict(bit=bit,layer=layer,centre_um=[round(x,6),round(y,6)],bbox_um=box,
                 master='DFFASRHQNx1_ASAP7_75t_R' if bit==512 else 'DFFHQNx1_ASAP7_75t_R')
        stages[j].append(rec);chain.append((x,y))
    hops=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(chain,chain[1:])]
    chains.append(dict(bit=bit,max_hop_um=max(hops),pin_y_um=piny,hops_um=hops))

overlaps=[]
all_boxes=[]
for j,rows in stages.items():
    for r in rows:
        for oldj,old in all_boxes:
            if boxes_overlap(r['bbox_um'],old['bbox_um']):overlaps.append([oldj,old['bit'],j,r['bit']])
        all_boxes.append((j,r))

pg_domains={'A':[52.84,75.6,2682.92,1021.68],'B':[127.44,75.6,2757.52,1021.68]}
clashes={n:[(j,r['bit']) for j,r in all_boxes if boxes_overlap(r['bbox_um'],d)] for n,d in pg_domains.items()}
interior=[r['bbox_um'] for j,r in all_boxes if j not in (0,8)]
max_hop=max(r['max_hop_um'] for r in chains)
report=dict(schema='opentallas.s81.phy_ft0_perbit_estimate.v3',status='ESTIMATE_ONLY_NOT_PLACED_NETLIST',
            source_pin_geometry='schema.pin_positions: actual512data+epoch, M6/M4, window119.04..228.444',
            mapped_masters_source='actual IQF FT station geom.tsv; DFFHQNx1 W1.080 H.270; epoch DFFASRHQNx1 W1.404',
            data_bits=512,epoch_bits=1,stages=9,source_and_capture_intervals=8,
            extra_fixed_cycles=1,affected_lane='coll__s_7S_LP__lk_ES1',lane_cycles=[57,58],reverse_cycles=[57,57],
            existing_8flop_straight_4p32_anchor_bound_um=(W-8.64)/7,
            old_bound_scope='conditional on existing4.32um face anchors; <=30um lawful endpoint inset can change old straight bound',
            new_shore_U_min_hop_8flops_even_with_30um_endpoint_inset=(W-60+2*(MAXY-70))/7,
            row_pitch_um=PH,site_pitch_um=PW,rows_per_stage=ROWS,
            maximum_boundary_columns=max(endpoint_rows.values()),
            max_hop_um=max_hop,over_405=[r['bit'] for r in chains if r['max_hop_um']>405],
            cell_overlaps=overlaps,pg_domain_clashes=clashes,
            interior_pg_bottom_clearance_um=75.6-max(r[3] for r in interior),
            bbox_and_hop_gate_pass=not overlaps and not any(clashes.values()) and max_hop<=405,
            limitations=['Native nine-flop RTL/LEC+lockstep/mutant not built',
                         'No DPL legality, tapcell collision or wire/CTS/STA qualification',
                         'Clock/reset analytical qualification and actualIR remain separate prerequisites',
                         '513FT0 bit cells only; FT1 ring and other digital logic use separate free areas'],
            bit_chains=chains,bit_stations={str(j):r for j,r in stages.items()})
(ROOT/'phy_perbit_v3.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({k:report[k] for k in ['max_hop_um','cell_overlaps','pg_domain_clashes','interior_pg_bottom_clearance_um','bbox_and_hop_gate_pass']}))
