#!/usr/bin/env python3
"""Candidate exact PV calendar restoration; physical footprint allocation remains required."""
import argparse
import json
import re
from pathlib import Path
from collections import Counter
import r8


def derive(bg):
    rows, bad, seen = [], [], set()
    cost, ports = Counter(), Counter()
    for g in bg['landing']:
        if not re.match(r'^pvw_[01]__', g['sink']):
            continue
        for m in g['members']:
            if not re.match(r'^pvw_[01]__', m['source']):
                continue
            if m['source'].split('__')[0] != g['sink'].split('__')[0]:
                raise ValueError('cross-pair PV edge')
            if r8.RESET_RX.search(m['sink_port']) or r8.RESET_RX.search(m['source'].rpartition('.')[2]):
                continue
            mid = r8.mkey(g, m)
            if mid in seen:
                raise ValueError('duplicate PV member ' + mid)
            seen.add(mid)
            old, bound = int(m['asbuilt_stages']), int(m['bound_stages'])
            current = int(m.get('landed_stages', bound))
            if max(bound, current) > old:
                bad.append(dict(id=mid, asbuilt=old, bound=bound, landed=current))
                continue
            width = r8.nbits(m['sink_bits'])
            rows.append(dict(id=mid, sink=g['sink'], sink_part=g['sink_part'], src_part=g['src_part'],
                             sink_port=m['sink_port'], sink_bits=m['sink_bits'], source=m['source'],
                             asbuilt=old, bound=bound, pad=old-bound, landed=old, lane=m['lane']))
            cost[g['sink_part']] += (old-current)*width
            ports[m['sink_port']] += 1
    if bad:
        raise ValueError('PV path exceeds original calendar; padding cannot restore: ' + json.dumps(bad[:12]))
    if not rows or not any(x['sink_port'] == 'join_go' for x in rows) or not any(x['sink_port'] == 'col_valid' for x in rows):
        raise ValueError('PV command/column crossings absent; wrong bind/source ABI')
    return dict(schema=r8.SCHEMA, die='qwen_kvsys', kind='pv_exact_asbuilt_calendar',
                note='CANDIDATE: restore original PV edge ages; allocate added FF footprints before physical adoption',
                merge_rule='authoritative land_r8_extra; append after generic tables',
                summary=dict(members=len(rows), additional_flops=sum(cost.values()), additional_flops_by_part=dict(cost),
                             members_by_port=dict(ports), schedule_cycles_added_vs_asbuilt=0), members=rows)


def check(bg, table):
    expected = {m['id']: m for m in table['members']}
    found = set()
    for g in bg['landing']:
        for m in g['members']:
            mid = r8.mkey(g, m)
            if mid in expected:
                found.add(mid)
                want = expected[mid]['asbuilt']
                got = int(m.get('landed_stages', m['bound_stages']))
                if got != want:
                    raise ValueError(f'PV calendar {mid}: landed {got} != asbuilt {want}')
    if found != expected.keys():
        raise ValueError('PV calendar missing members: ' + str(sorted(expected.keys() - found)[:12]))
    return dict(verdict='PASS', members=len(found), schedule_cycles_added_vs_asbuilt=0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bus_groups', type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--check', type=Path, help='candidate table to verify against a fresh bind')
    a = p.parse_args()
    bg = json.loads(a.bus_groups.read_text())
    doc = check(bg, json.loads(a.check.read_text())) if a.check else derive(bg)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc, indent=1) + '\n')
    print(json.dumps(doc.get('summary', doc), sort_keys=True))


if __name__ == '__main__':
    main()
