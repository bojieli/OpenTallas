"""Source-backed physical contract for the twelve native static CDC children.

The retained legacy die IO graph is not a native producer/calendar binding.
This contract keeps the exact child homes and actual parent pins reviewable
without inventing missing collective or compiler sources.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build(frame=None):
    from qwen_static_cdc.sites import build as build_sites
    sites = build_sites()
    if frame is not None:
        assert all(abs(getattr(frame, k) - sites['frame'][k]) < .001 for k in ('x', 'y', 'w', 'h'))
    leaf = json.loads((ROOT / 'physical/ref_tile/qfd_static_ch546/assigned_pins.json').read_text())
    rtl = (ROOT / sites['actual_rtl']).read_text()
    parent_ports, clock_entries, faces = {}, [], {}
    for child in sites['channels']:
        role = child['channel']
        for name, pin in leaf['ports'].items():
            if name == 'rst_n':
                continue  # real shared parent reset is assigned below
            q = child['ports'][name]
            port = q['parent_port']
            bits = child['data_bits'] if name in ('i_data', 'o_data') else pin['bits']
            # The narrower514/517 records are explicitly padded inside actual RTL.
            if name == 'i_data' and bits < 546:
                assert re.search(r"\.i_data\(\{" + str(546-bits) + r"'b0," + role + r"_i_data\}\)", rtl)
            clock = name in ('wck', 'rck')
            if clock:
                x, y = q['die_entry']
                position = round(x - sites['frame']['x'], 4)
                record = dict(face='N', layer='M5', bits=1, direction='input',
                              positions_um=[position], interior=True,
                              entry_die_um=[x, y], R_ps=None, phi_ps=None,
                              child=child['instance'] + '.' + name)
                clock_entries.append(dict(parent_port=port, **record))
            else:
                start = q['parent_y_range'][0]
                positions = [round(start + (p - pin['positions_um'][0]), 4)
                             for p in pin['positions_um'][:bits]]
                record = dict(face=q['face'], layer=pin['layer'], bits=bits,
                              direction=pin['direction'], positions_um=positions,
                              range_um=[positions[0], positions[-1]], bit0_at='lo',
                              child=child['instance'] + '.' + name,
                              child_reach_um=q['manhattan_um'])
                faces.setdefault(q['face'], []).append((positions[0], port))
            parent_ports[port] = record
    # A real reset route must reach every leaf reset; this pin is not tied.
    parent_ports['rst_n'] = dict(face='N', layer='M5', bits=1, direction='input',
                                positions_um=[350.028], range_um=[350.028,350.028], bit0_at='lo')
    faces.setdefault('N', []).append((350.028, 'rst_n'))
    assert len(clock_entries) == 24
    for face in ('W', 'E'):
        positions = [x for p in parent_ports.values() if p['face'] == face for x in p['positions_um']]
        assert len(positions) == len(set(positions)), (face, 'overlapping exact parent pins')
        assert min(positions) > 0 and max(positions) < sites['frame']['h']
    return dict(schema='opentallas.qwen.native-static-io-contract.v1',
                source_commits=['b53541400', '7494a6c90'], master='qfd_io_xfifo_static',
                outline={k: sites['frame'][k] for k in ('w','h')}, frame=sites['frame'],
                ports=parent_ports, pins={f:[n for _, n in sorted(items)] for f,items in faces.items()},
                children=sites['channels'], clock_entries=clock_entries,
                fixed_edges=sites['fixed_edges'], data_padding='RTL zero pad only:ur/dr514,cq517; all other roles546',
                endpoint_binding='OPEN: exact static collective/seq/cq producer and calendar ports required; legacy credit graph is not adopted',
                clock_binding='OPEN:24 actual root routes and per-clock measured R/phi; no common-phase substitution',
                physical_status='12 actual children fit retained frame; local pins assigned; actual RC/native timing pending')
