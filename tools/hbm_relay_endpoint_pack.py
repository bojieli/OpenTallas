"""Candidate endpoint packing, not hardened-station or full-die qualification."""
import argparse, json, math, hashlib, sys
from pathlib import Path
from hbm_relay_channel_model import spatial_slices


def pack(groups, pins, endpoint, shape=(20.,20.), gap=2.16, reach=100.):
    """Reserve all boxes together; conservatively reach every possible station pin.

    Pins lie on one outer macro edge. Geometry is local: surrounding macros,
    die boundary, PDN and clock reservations must be checked by the die owner.
    No assertion that an assumed box implements the required station.
    """
    if min(*shape,gap,reach)<=0:
        raise ValueError("station dimensions, gap and reach must be positive")
    chosen=[]
    for group in groups:
        bitids=group['bit_indices']; pp=[pins[i] for i in bitids]
        face=group[endpoint+'_face']; portal=group[endpoint+'_portal_um']
        axis=1 if face in 'WE' else 0
        candidates=[]
        radius=math.ceil(reach/2.16)
        min_away=math.ceil((shape[1-axis]/2+gap-25)/2.16)
        for along in range(-radius,radius+1):
            for away in range(min_away,radius+1):
                p=list(portal)
                p[axis]+=along*2.16
                p[1-axis]+=away*2.16*(-1 if face in 'WS' else 1)
                w,h=shape; b=[p[0]-w/2,p[1]-h/2,p[0]+w/2,p[1]+h/2]
                worst=max(abs(x-u)+abs(y-v) for x,y in pp for u,v in
                          [(b[0],b[1]),(b[0],b[3]),(b[2],b[1]),(b[2],b[3])])
                if worst>reach: continue
                if any(b[0]<q['box_um'][2]+gap and q['box_um'][0]<b[2]+gap and
                       b[1]<q['box_um'][3]+gap and q['box_um'][1]<b[3]+gap for q in chosen): continue
                candidates.append((worst,abs(along)+abs(away),b))
        if not candidates: raise ValueError(f'no jointly legal {endpoint} box for bits {bitids}')
        worst,_,b=min(candidates)
        chosen.append(dict(bit_indices=bitids,box_um=b,worst_pin_to_any_box_point_um=worst))
    return chosen


def main():
    root=Path(__file__).resolve().parents[1]
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    plan=root/'results/uarch/hbm_relay_endpoint_pack_20261007/sm_successor_planned_pins.json'
    oldpath=root/'results/uarch/hbm_relay_channel_20261007/rl_sm0_spatial_slices.json'
    sm=json.loads(plan.read_text()); old=json.loads(oldpath.read_text())
    names=['rv']+[f'rrow[{i}]' for i in range(12)]+[f'rdata[{i}]' for i in range(256)]+['fault']
    lookup={p['pin']:p['xy'] for p in sm['pins']}
    source=[lookup[n] for n in names]
    e=old['endpoints'][1]; x,y,x1,y1=e['physical_box_um']
    sink=[(a-x,b-y) for a,b in e['physical_pins_um']]
    groups=spatial_slices(source,sink,(0,0,3075.84,1131.84),(0,0,x1-x,y1-y),max_bits=64)
    result=dict(status='candidate-local-endpoint-packing-only',data_bits=270,
      bit_order=names,source_pin_plan=sm['scope'],group_count=len(groups),groups=groups,
      source_boxes=pack(groups,source,'source'),sink_boxes=pack(groups,sink,'sink'),
      assumed_station_width_um=20,assumed_station_height_um=20,station_gap_um=2.16,
      source_inputs={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [plan,oldpath,Path(__file__).resolve()]},
      endpoint_area_um2=2*len(groups)*400,
      boundary_bits_per_cycle=270,memory_bytes_per_cycle=0,MACs_per_cycle=0,
      selected=False,remaining_gates=['harden station matching dimensions and real d/q pins',
       'new SM footprint placed legally in full die and reserve these boxes against all other instances/PDN/clock',
       'route all intermediate stages and balancing registers with shared occupancy',
       'latency and token traversal composition for changed die geometry',
       'same-clock fixed-stream identity/valid/fault alignment exactness and negative controls',
       'real routed SS/FF with >=15ps and DRC0; source planned pins match actual LEF'])
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(groups=len(groups),endpoint_boxes=2*len(groups),max_source_reach=max(q['worst_pin_to_any_box_point_um'] for q in result['source_boxes']),max_sink_reach=max(q['worst_pin_to_any_box_point_um'] for q in result['sink_boxes']),out=str(out))))
if __name__=='__main__': main()
