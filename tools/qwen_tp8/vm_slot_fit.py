#!/usr/bin/env python3
"""Reserve eight real-sized VM groups in the existing TP8 die; reject unsafe IO concentration.
Geometry feasibility alone is not a die netlist or a closure result. Existing relays must
be rebuilt around selected reservations, and the ninth glue reservation needs synthesis.
"""
import argparse, hashlib, json, math
from pathlib import Path

def ceil_grid(x):
    return round(math.ceil((x-1e-7)/2.16)*2.16, 6)

def overlap(a,b,gap=20):
    return (a['x'] < b['x']+b['w']+gap and a['x']+a['w']+gap > b['x']
            and a['y'] < b['y']+b['h']+gap and a['y']+a['h']+gap > b['y'])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('net');ap.add_argument('out');a=ap.parse_args()
    p=Path(a.net);d=json.loads(p.read_text());w=1149.12
    # Current TP8 geometry from the generated actual it2 case, unchanged die outline.
    die=[31785.696,25870.32];bounds=[13214.448,1600,18487,die[1]-20]
    obstacles=[i for i in d['insts'] if not i['m'].startswith(('qfd_rly','qkd_rly'))
               and i['n']!='sp_vector_memory']
    near=[i for i in obstacles if i['x']<bounds[2] and i['x']+i['w']>bounds[0]]
    xs={ceil_grid(bounds[0]+20),ceil_grid(bounds[2]-20-w)}
    ys={ceil_grid(bounds[1]),ceil_grid(bounds[3]-w)}
    for i in near:
        xs.update((ceil_grid(i['x']+i['w']+20),ceil_grid(i['x']-w-20)))
        ys.update((ceil_grid(i['y']+i['h']+20),ceil_grid(i['y']-w-20)))
    candidates=[]
    for x in xs:
        for y in ys:
            r=dict(x=x,y=y,w=w,h=w)
            if x<bounds[0]+20 or x+w>bounds[2]-20 or y<bounds[1] or y+w>bounds[3]:continue
            if any(overlap(r,i) for i in obstacles):continue
            candidates.append((abs(x+w/2-15236)+abs(y+w/2-11981),r))
    chosen=[]
    for _,r in sorted(candidates,key=lambda q:(q[0],q[1]['x'],q[1]['y'])):
        if any(overlap(r,i) for i in chosen):continue
        chosen.append(r)
        if len(chosen)==9:break
    assert len(chosen)==9,'no eight-group plus glue geometric reservation'
    for j,r in enumerate(chosen):
        assert not any(overlap(r,i) for i in obstacles)
        assert not any(overlap(r,i) for i in chosen[:j])
        r.update(n=f'vm_grp_{j}' if j<8 else 'vm_glue_reservation',
                 m='ot_qfd_vm_grp' if j<8 else 'UNSIZED_GLUE',pg_layer='M7',signal_max_layer='M7')
    # Production NBK8/LAW8/NSB2/NSU3/LAWS10 exact group port widths, excluding clock/reset.
    west=8+64+8+64+128+4096+6+60+2+20+32+1024
    east=4096+512+3072+1
    cap=.75*w/.080 # M8 horizontal die signal capacity above a M7 cluster.
    out=dict(source=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()),
             die_um=die,reservations=chosen,geometry=dict(verdict='PASS',group_count=8,
             group_area_mm2=8*w*w/1e6,minimum_gap_um=20,origin_grid_um=2.16,
             outside=0,hard_overlaps=0,group_overlaps=0,existing_hard_views_changed=0),
             io_cut=dict(verdict='REJECT_UNCHANGED_CENTRALIZED_INTERFACE',
             west_payload_bits=west,east_payload_bits=east,usable_horizontal_tracks=cap,
             west_payload_util=west/cap,east_payload_util=east/cap,target=.60,
             note='Full-face lower bound only. Fine-window, control, existing die nets and routing add demand.',
             proposed_group_port_change='Move so[3071:0] to N: E xo+ro+ovf4609bits becomes0.428; N so3072bits becomes0.285 of M9 full-face capacity. Requires a new group view; current r6c route is preserved.'),
             adoption=dict(status='NOT ADOPTED: geometric reservation only; interface cut fails',
             required=['Distribute aggregation/rotation/descriptor glue beside groups; never pool all eight raw ports at one glue pin bank',
                       'Harden/synthesize real glue and prove it fits reserved region; ninth square is capacity reservation only',
                       'Registered <=500um seams and matched relay counts; updated exact latency benches',
                       'Rebuild affected relay chains and functional port netlist, then full cut scan with existing die demand',
                       'Real group timing/pin/OBS views and local clock insertion, child_lint, die GRT/STA/IR',
                       'Maintain golden rotation/order; no area-based claim of functional integration']))
    Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['geometry']));print(json.dumps(out['io_cut']))
if __name__=='__main__':main()
