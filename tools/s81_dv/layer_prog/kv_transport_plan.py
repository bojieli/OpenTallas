#!/usr/bin/env python3
"""Concrete native-pair KV moves over current XRT paths; dates fail closed.

One pair is in flight globally. Native producer ownership comes from the
actual-inventory capture map. This does not fabricate CAP completion dates,
missing inter-rank carriage, or a qualified end-to-end programme.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiler-root', required=True)
    p.add_argument('--tree', required=True)
    p.add_argument('--ownership', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--transport-profile', required=True)
    a = p.parse_args()
    root = Path(a.compiler_root)
    sys.path[:0] = [str(root / 'tools/s81_dv'), str(root / 'tools/s81_dv/layer_prog')]
    from dv_layer_compile import Die, ctl_path, ctl_payload, vp_cmd
    from layer_prog.final_ffn_transport import Network
    from layer_prog.lower_vpx import send_cfg

    die = Die(Path(a.tree))
    net = Network(die)
    ownership = json.loads(Path(a.ownership).read_text())
    assert ownership['die_sha256'] == die.die_sha
    profile = json.loads(Path(a.transport_profile).read_text())
    assert profile['schema'] == 'opentallas.s81_kv.transport_source.v1'
    rank = ownership['rank']
    packets = []
    for capture in ownership['halves']['B']['captures']:
        sid = die.slices()[capture['slice']]['sid']
        rows = capture['rows']
        kv = [r for r in rows if r['tensor'] == 'wkv']
        if not kv:
            continue
        assert len(kv) % 8 == 0
        for first in range(0, len(kv), 8):
            values = kv[first:first + 8]
            assert values[0]['native_row'] % 2 == 0 and values[0]['word'] == 0
            source_row = values[0]['native_row']
            target_row = 692 + (values[0]['golden_output_index'] - 1280) // 4
            assert target_row % 2 == 0 and 692 + 32 * rank <= target_row < 724 + 32 * rank
            legs = []

            def leg(kind, source, destination, sr, dr, path):
                if kind == 'local':
                    cfg = (send_cfg('E', 4, 0, 1 << destination, 0, dr, 1) & ~15) | (1 << 44)
                elif kind == 'typed_v':
                    assert source ^ 1 == destination
                    cfg = send_cfg('V', 4, 1, 1 << destination, 0, dr, 1)
                else:
                    direction = 'E' if destination // 2 > source // 2 else 'W'
                    cfg = send_cfg(direction, 4, abs(destination // 2 - source // 2), 1 << destination, 0, dr, 1)
                # Real command words, with explicit outstanding date obligations.
                legs.append(dict(kind=kind, source_sid=source, destination_sid=destination,
                    source_rows=[sr, sr + 1], destination_rows=[dr, dr + 1], path=path,
                    templates=[dict(target=4, leaf_mask=0, payload186=f'{ctl_payload(1 << source, 4, 0, cfg):047x}'),
                               dict(target=0, leaf_mask=1, payload186=f'{ctl_payload(1 << source, 0, 1, vp_cmd(6, a0=sr, n=1)):047x}')],
                    control_path=ctl_path(die, net.sid[source]),
                    source_component_edges=profile['component_edges'],
                    source_issue_edge=None, destination_sram_commit_edge=None))

            if sid == 7:
                leg('local', sid, 7, source_row, target_row, [])
            elif sid % 2:
                leg('horizontal', sid, 7, source_row, target_row, net.horizontal(sid, 7))
            else:
                bridges = net.bridges(0)
                if not bridges:
                    raise ValueError('Actual die has no landed partner bridge; no V path may be invented')
                col, name, link = min(bridges, key=lambda x: (abs(sid // 2 - x[0]) + abs(x[0] - 3), x[0]))
                partner_s, partner_n = 2 * col, 2 * col + 1
                if sid != partner_s:
                    leg('horizontal', sid, partner_s, source_row, 480, net.horizontal(sid, partner_s))
                    source_row = 480
                leg('typed_v', partner_s, partner_n, source_row, 480,
                    [dict(link=name, age_edges=link['age_edges'], landing=link['landing'])])
                leg('local' if partner_n == 7 else 'horizontal', partner_n, 7, 480, target_row,
                    [] if partner_n == 7 else net.horizontal(partner_n, 7))
            packets.append(dict(native_pairs=1, source_rank=rank, values=values, legs=legs))
    assert len(packets) == 16
    out = dict(schema='opentallas.s81.kv_transport_plan.v1', die_sha256=die.die_sha,
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        ownership_sha256=hashlib.sha256(Path(a.ownership).read_bytes()).hexdigest(),
        transport_source_ref='codex/s81-kvq-bind-1021@286841a83 (XRT ABI 59a8155d3)',
        source_profile=profile, source_profile_sha256=hashlib.sha256(Path(a.transport_profile).read_bytes()).hexdigest(),
        rank=rank, native_pairs=16, values=128, packets=packets, scratch_rows=[480, 481],
        global_inflight_pairs=1, inter_rank_exchange_qualified=False, calendar_qualified=False,
        required=['OT_S81SL_KV_TRANSPORT source assembly for normal slices; no old physical view alias',
                  'Actual frame GO/FIN/CAP completion dates',
                  'Composition of pinned primitive edges with native SRAM commit dates and fixed nonoverlapping CTL slots',
                  'All-four-rank 128-value carriage before D512 launch'],
        qualification='CONCRETE COMMAND/PATH PLAN ONLY; no invented dates, no lowered/token qualification')
    Path(a.out).write_text(json.dumps(out, indent=2) + '\n')
    print(f'KV_TRANSPORT_PLAN rank{rank} nativepairs16 legs{sum(len(x["legs"]) for x in packets)}; dates/interrank/CAP held')


if __name__ == '__main__':
    main()
