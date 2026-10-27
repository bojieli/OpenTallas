#!/usr/bin/env python3
"""Diagnose failed native station edges by exact resolved bit intersection.

This does not approve a replacement endpoint or change any plan. Candidate
consumers are an audit of the supplied source vehicle, including its hash.
"""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hbm_b2'))
from b2_top import Die, parse_expr


def resolved_bits(die, expression):
    result = set()
    for segment, _ in die.resolve(parse_expr(expression, die.widths)):
        if segment[0] == 'n':
            result.update((segment[1], bit) for bit in range(segment[2], segment[3] + 1))
    return result


def audit(native, config, report):
    die = Die(native, config['transport'])
    ports = {}
    reverse = collections.defaultdict(set)
    errors = {}
    for inst, spec in die.insts.items():
        if die.is_transport(inst):
            continue
        for port, expression in spec['conns'].items():
            try:
                bits = resolved_bits(die, expression)
            except (KeyError, ValueError, RecursionError) as error:
                errors[f'{inst}.{port}'] = str(error)
                continue
            ports[inst, port] = bits
            for bit in bits:
                reverse[bit].add((inst, port))
    rows = []
    for failed in report['rows']:
        if failed.get('verdict') == 'PASS':
            continue
        row = {key: failed.get(key) for key in ('type', 'station', 'field', 'conn', 'reason', 'source_native', 'source_port', 'target_native')}
        source = failed.get('source_native'), failed.get('source_port')
        bits = ports.get(source)
        if bits is None:
            row['status'] = 'NEEDS_EXACT_SPLIT_ALIAS_OR_ROLE_CONTRACT'
        elif not bits:
            row['status'] = 'CONSTANT_ONLY_SOURCE'
        else:
            candidates = collections.Counter(endpoint for bit in bits for endpoint in reverse[bit] if endpoint[0] != source[0])
            row['source_unique_bits'] = len(bits)
            row['actual_native_partners'] = [dict(instance=inst, port=port, shared_unique_bits=count,
                partner_unique_bits=len(ports[inst, port]), master=die.insts[inst]['master'],
                source_net_driver=bool( any(die.driver.get(net) == (inst, port) for net, _ in bits & ports[inst, port])))
                for (inst, port), count in sorted(candidates.items(), key=lambda item: (-item[1], item[0]))]
            row['status'] = 'EXACT_PARTNERS_FOUND' if candidates else 'NO_OTHER_NATIVE_PORT_SHARES_SOURCE_BITS'
        rows.append(row)
    return dict(schema='opentallas.native_failed_edge_audit.v1', native_sha256=hashlib.sha256(Path(native).read_bytes()).hexdigest(),
        scope='Diagnostic only: never authorizes aliases, endpoint replacement, station deletion, or a newer source vehicle.',
        failed_edges=len(rows), statuses=dict(collections.Counter(row['status'] for row in rows)), parse_errors=errors, rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('native', 'asbuilt', 'report', 'out'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('refusing existing output')
    result = audit(args.native, json.loads(args.asbuilt.read_text()), json.loads(args.report.read_text()))
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['statuses'], sort_keys=True))


if __name__ == '__main__':
    main()
