#!/usr/bin/env python3
"""Source-pinned capture face/cut screen; proposals are not physical grants."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

PITCH = {'M3': .036, 'M4': .048, 'M5': .048, 'M6': .064}


def review(path):
    record = json.loads(path.read_text())
    bits = record['ports']['t_vm']['bits']
    def cut(length, layers):
        raw = sum(length/PITCH[layer] for layer in layers)
        return dict(face_length_um=length, layers=layers, raw_track_capacity=raw,
                    demand_bits=bits, utilization=bits/raw)
    faces = {}
    for port, spec in record['ports'].items():
        counts = Counter((row[0], row[1]) for row in spec['per_bit'])
        faces[port] = [dict(face=face, layer=layer, bits=count)
                       for (face, layer), count in sorted(counts.items())]
    x = [row[2] for row in record['ports']['t_vm']['per_bit']]
    return dict(schema='opentallas.s81.capture-face-review.v1',
        status='HELD_ALTERNATIVE_SCREEN_NO_QUALIFIED_PARENT',
        input=str(path), input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        outline_um=record['outline_um'], actual_port_faces=faces,
        pitch_um=PITCH, pitch_source='tools/qwen_rom_fulldie.py Q.TRK',
        frozen_south_escape=cut(21.624, ['M4', 'M6']),
        alternatives=[
            dict(rank=1, name='Taller west-facing capture parent',
                 outline_um=[1728.,691.2], west_cut=cut(691.2,['M4','M6']),
                 height_added_um=129.6,
                 gather_north_cut=dict(demand_bits=6947, raw_track_capacity=1728/.048,
                                       utilization=6947/(1728/.048)),
                 internal_routing='Must re-pack or add real relays; face capacity alone does not qualify the parent'),
            dict(rank=2, name='Single-layer taller west-facing capture parent',
                 outline_um=[1728.,1296.], west_cut=cut(1296.,['M4']),
                 height_added_um=734.4,
                 internal_routing='Requires complete child pack and all incident control/clock/reset routes'),
            dict(rank=3, name='Unchanged height west-facing parent',
                 outline_um=[1728.,561.6], west_cut=cut(561.6,['M4','M6']),
                 reject='West cut exceeds0.60 even before clocks/reset/PG; wires-only reface is not a feasible full solution')],
        unchanged_child_x_reface_lower_bound=dict(
            derivation='Preserving existing child x positions requires at least the existing output x displacement to reach W. Vertical travel and detours add distance.',
            maximum_horizontal_um=max(x), bits_over_500=sum(v>500 for v in x),
            bits_over_1000=sum(v>1000 for v in x), bits_over_1500=sum(v>1500 for v in x),
            warning='At least3 relay boundaries on the longest unchanged-x path under a provisional500um hop screen; exact native hop budgets and balanced fixed-cycle RTL remain unproved'),
        required=['Exact existing closed-child placement and per-bit pin joins',
                  'All incident faces including6947b gather input, status, clocks and resets',
                  'Child-local cut and reserved PG/clock capacity, not only outer-face track counts',
                  'Real relay master area/root count and compiler-visible fixed-cycle changes',
                  'Complete die reservation and all-incident path preflight',
                  'Source-current native/TT/FF/DRC0 and mapped program proof'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pins',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=review(a.pins);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
