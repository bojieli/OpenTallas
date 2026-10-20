#!/usr/bin/env python3
"""Source-bit resolved static-age MODEL; never a physical/calendar certificate.

Audit the emitted relay layer, without changing functional-bind history. Plain
register paths have their actual tree/chain depth. Landed paths require actual
current clock/reset epoch evidence, which the legacy compiler report does not
provide. Its E/K placeholders (even numeric E) are not measured evidence; this
version refuses to qualify them. A future measured-epoch adapter needs review.

The strict CLI exits nonzero on missing metadata, unknown ages or unequal bit
ages. --diagnostic-incomplete-ages retains those failures and explicitly false
qualification while allowing diagnostic output collection. No layer is edited.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path


def load(path):
    with gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path) as f:
        return json.load(f)


def ranges(bits):
    out = []
    for src, dst in sorted(bits, key=lambda x: (x[1], x[0])):
        if out and src == out[-1][1] and dst == out[-1][3]:
            out[-1][1] += 1; out[-1][3] += 1
        else:
            out.append([src, src+1, dst, dst+1])
    return out


def audit(layer, compiler, precontract):
    defects, groups = [], {}
    row_ids = set()
    actual_instances = {x['name']: x for x in layer['instances']}
    declared = {x['bus']: x for x in compiler.get('compiler', [])}
    if not layer.get('relay_splice_v2') or not declared:
        defects.append('empty layer or compiler row inventory')
    for bus in layer['relay_splice_v2']:
        bid = bus['bus']
        if bid in row_ids:
            defects.append(f'duplicate bus {bid}')
        row_ids.add(bid)
        cr = declared.get(bid)
        if not cr or cr.get('driver', '').split('.', 1)[0] != bus['driver']:
            defects.append(f'{bid}: missing/mismatched compiler row')
        if len(bus['driver_bits']) != bus['bits'] or len(bus['loads']) != bus['bits']:
            defects.append(f'{bid}: incomplete real bit map')
            continue
        tree = {n['id']: n for n in bus['nodes']}
        age = {}
        for sink, sk in bus['sinks'].items():
            emitted = [n['names'] for n in bus['nodes']] + sk['chain']
            for names in emitted:
                if len(names) != bus['tiles'] or any(n not in actual_instances for n in names):
                    defects.append(f'{bid}->{sink}: incomplete actual emitted tile inventory')
            count, n, visited = 0, sk['src'][0], set()
            while n is not None:
                if n in visited or n not in tree:
                    defects.append(f'{bid}->{sink}: invalid station tree')
                    count = None; break
                visited.add(n); count += 1; n = tree[n]['parent']
            if bus['kind'] == 'old' and count is not None:
                age[sink] = (count+len(sk['chain']), None)
            else:
                age[sink] = (None, 'missing_actual_clock_reset_epoch_evidence')
        for (port, srcbit), loads in zip(bus['driver_bits'], bus['loads']):
            for sink, dstport, dstbit in loads:
                key = (bus['driver'], port, sink, dstport)
                group = groups.setdefault(key, {})
                if sink not in age:
                    defects.append(f'{bid}: actual load {sink} absent from sink inventory')
                val, why = age.get(sink, (None, 'missing_sink_inventory'))
                entry = group.setdefault(bid, dict(bus=bid, kind=bus['kind'],
                                                  age_edges=val, unknown_reason=why, bits=[]))
                entry['bits'].append((srcbit, dstbit))
    if row_ids != set(declared):
        defects.append('layer/compiler row inventory differs')
    expected = collections.defaultdict(set)
    for edge in precontract['edges']:
        si, sp, lo, hi = edge['source']
        di, dp, dlo, dhi = edge['sink']
        key = (si, sp, di, dp)
        if key in groups:
            if hi-lo != dhi-dlo:
                defects.append(f'{key}: invalid original edge width')
                continue
            expected[key].update((lo+i,dlo+i) for i in range(hi-lo))
    records = []
    for key, bybus in sorted(groups.items()):
        ages = {v['age_edges'] for v in bybus.values() if v['age_edges'] is not None}
        unknown = any(v['age_edges'] is None for v in bybus.values())
        kinds = {v['kind'] for v in bybus.values()}
        seen, duplicate, actual_pairs = set(), False, set()
        for v in bybus.values():
            for src, dst in v['bits']:
                actual_pairs.add((src,dst))
                if dst in seen:
                    duplicate = True
                seen.add(dst)
            v['source_to_sink_ranges_half_open'] = ranges(v.pop('bits'))
        complete = bool(expected[key]) and actual_pairs == expected[key]
        status = 'FAIL' if unknown or len(ages)>1 or duplicate or not complete else 'PASS'
        records.append(dict(producer=list(key[:2]), consumer=list(key[2:]),
                            status=status, known_ages=sorted(ages), unknown_age=unknown,
                            mixed_plain_forwarded=('old' in kinds and len(kinds)>1),
                            duplicate_consumer_bits=duplicate, consumer_bits=len(seen),
                            complete_original_source_bit_map=complete,
                            rows=list(bybus.values())))
    failed = sum(x['status']=='FAIL' for x in records)
    return dict(schema='opentallas.hbm.relay-static-age-model.v1',
                qualification_eligible=False, calendar_qualified=False,
                native_qualified=False, physical_qualified=False,
                verdict='FAIL' if defects or failed else 'PASS', defects=defects,
                groups=len(records), failing_groups=failed,
                unknown_groups=sum(x['unknown_age'] for x in records),
                mixed_groups=sum(x['mixed_plain_forwarded'] for x in records),
                unequal_known_groups=sum(len(x['known_ages'])>1 for x in records),
                paths=records,
                scope='Static source-bit age model only; no transaction/calendar or physical qualification.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--layer', required=True); ap.add_argument('--compiler-report', required=True)
    ap.add_argument('--pre-relay-contract', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--diagnostic-incomplete-ages', action='store_true')
    a = ap.parse_args()
    report = audit(load(a.layer), load(a.compiler_report),load(a.pre_relay_contract))
    report['inputs_sha256'] = {k:hashlib.sha256(Path(v).read_bytes()).hexdigest()
                              for k,v in [('layer',a.layer),('compiler_report',a.compiler_report),
                                          ('pre_relay_contract',a.pre_relay_contract)]}
    report['diagnostic'] = a.diagnostic_incomplete_ages
    Path(a.out).write_text(json.dumps(report, indent=2)+'\n')
    prefix = 'DIAGNOSTIC_STATIC_AGE_MODEL' if a.diagnostic_incomplete_ages else 'STATIC_AGE_MODEL'
    print(prefix, report['verdict'], 'groups',report['groups'],
          'unknown',report['unknown_groups'], 'mixed',report['mixed_groups'],
          'unequal',report['unequal_known_groups'], 'qualification=false')
    return 0 if a.diagnostic_incomplete_ages or report['verdict']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
