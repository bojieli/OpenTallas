#!/usr/bin/env python3
"""Conservative one-row R0 selector sizing; no over-macro routing credit.

The contract pin lattice gives an optimistic track lower bound, not a routed
layer-capacity claim. All seams detour in a dedicated north channel, so no data
edge passes through a solid quarter/control macro. Only actual hardened station
size is used; their clocks/port direction contracts still require qualification.
"""
import json
import math
from pathlib import Path
try:
    from . import selector_square as S
except ImportError:
    import selector_square as S


def build(root=S.ROOT):
    q=json.loads((root/S.QUARTER).read_text())
    c=json.loads((root/S.CONTROL).read_text())
    sw,sh=17.256,30.216  # actual dsfd_stnh_512x1 LEF SIZE
    gap=43.2
    xs=[6.544+g*(432+gap) for g in range(4)]
    cx=xs[-1]+432+gap
    # A dedicated single-direction-layer channel, leaving 40% for PG/clock/vias.
    # M8 actual ASAP7 horizontal pitch is0.08um (retained technology excerpt).
    # M9 is vertical and cannot be counted as another horizontal layer.
    bits=4*(865+354+66+1)
    channel=math.ceil((bits*0.08/0.60)/2.16)*2.16
    channel_y=max(q['h_um'],c['h_um'])
    trunk_y=channel_y+channel/2
    bundles=[]
    for g in range(4):
        for qp,cp,n in [('t_s','f_s',865),('t_o','f_o',354),('f_c','t_c',66),('f_cr','t_cr',1)]:
            lengths=[]
            for b in range(n):
                a=S.center(q['ports'][qp]['pins'][b],xs[g],0)
                z=S.center(c['ports'][cp]['pins'][g*n+b],cx,0)
                # Escape in the per-tile seam, travel north of ALL macros,
                # descend in the control seam. This prices the whole detour.
                lengths.append((trunk_y-a[1])+abs(a[0]-z[0])+(trunk_y-z[1]))
            length=max(lengths)
            # One 100um final pin segment on each end, then <=430.56um trunks.
            stages=2+max(0,math.ceil(max(0,length-200)/430.56)-1)
            chunks=math.ceil(n/512)
            bundles.append(dict(quarter=g,quarter_port=qp,control_port=cp,bits=n,
                detour_length_um_max=round(length,3),stations_per_chunk=stages,
                chunks_512=chunks,station_instances=stages*chunks,
                final_segments_um=100,credit_initial=4))
    count=sum(b['station_instances'] for b in bundles)
    return dict(schema='opentallas.s81.selector-one-row.v1',qualified=False,
        orient='R0',source_commit=S.SOURCE,quarters=4,control=1,
        tile_positions=[dict(inst=f'u_q{g}',x=x,y=0) for g,x in enumerate(xs)]+[dict(inst='u_c',x=cx,y=0)],
        outline_um=[cx+c['w_um'],channel_y+channel],old_outline_um=[5270.376,321.816],
        dedicated_channel_um=channel,channel_bits=bits,track_pitch_um=.08,
        routing_signal_fraction=.60,tracks_capacity_lower_bound=math.floor(channel/.08*.60),
        channel_basis='actual ASAP7 M8 horizontal0.08um pitch; M9 vertical0.08um pitch; 60% signal allocation requires PG/via qualification',
        station_master='dsfd_stnh_512x1',station_actual_size_um=[sw,sh],
        station_instances=count,station_area_um2=count*sw*sh,
        available_channel_area_um2=(cx+c['w_um'])*channel,
        bundles=bundles,
        latency=dict(source_measured_mean=174,source_measured_max=310,
            maximum_forward_stages=max(b['stations_per_chunk'] for b in bundles if b['quarter_port'] in ('t_s','t_o')),
            credits=4,credit_round_trip_and_command_status_alignment='exact mechanism gate required; no throughput gain claimed'),
        problems=['actual station placements and clocks/lockups not implemented',
            'same-root common-clock primitive required: retained station fi0 is forwarded clock, not assumed interchangeable',
            'actual M8 signal-layer PG/via blockage and station pin-access capacity pending',
            'full-width finite-credit command/status transaction gate pending',
            'matching control SLAT=4 XDX=1 hardview pending',
            'die slot outline must be changed; no old-slab adoption'])


if __name__=='__main__':
    print(json.dumps(build(),indent=1))
