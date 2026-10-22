"""Inventory actual native FF, memory, and boundary roles from ODB/Liberty.

This is a pre-layout source audit. It makes no timing, PG, or reach claim.
"""
import argparse
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path

import odb


def blocks(text, kind):
    for match in re.finditer(r'\b' + kind + r'\s*\(([^)]*)\)\s*\{', text):
        start = pos = match.end()
        depth = 1
        while depth:
            depth += (text[pos] == '{') - (text[pos] == '}')
            pos += 1
        yield match[1].strip('" '), text[start:pos - 1]


def attr(text, key):
    match = re.search(r'\b' + key + r'\s*:\s*"?([^";]+)"?\s*;', text)
    return match[1].strip() if match else None


def audit(path, output):
    db = odb.dbDatabase.create()
    odb.read_db(db, str(path))
    block = db.getChip().getBlock()
    roles, libraries = {}, []
    for lib in Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib').rglob('*RVT_TT*.lib*'):
        text = gzip.open(lib, 'rt').read() if lib.suffix == '.gz' else lib.read_text()
        libraries.append({'path': str(lib), 'sha256': hashlib.sha256(lib.read_bytes()).hexdigest()})
        for name, body in blocks(text, 'cell'):
            seq = list(blocks(body, 'ff'))
            pins = {pin: {'direction': attr(value, 'direction'), 'function': attr(value, 'function'),
                          'clock': attr(value, 'clock') == 'true'} for pin, value in blocks(body, 'pin')}
            ins = [pin for pin, value in pins.items() if value['direction'] == 'input']
            outs = [pin for pin, value in pins.items() if value['direction'] == 'output']
            unary = False
            if len(ins) == len(outs) == 1:
                fn = re.sub(r'[()\s]', '', pins[outs[0]]['function'] or '')
                unary = fn in (ins[0], '!' + ins[0], ins[0] + "'")
            roles[name] = {'pins': pins, 'ff': dict((key, attr(seq[0][1], key)) for key in
                          ('next_state', 'clocked_on', 'clear', 'preset')) if seq else None,
                          'unary': unary}
    errors, rows, constant_outputs, unused_inputs = [], [], [], []
    masters = collections.Counter(inst.getMaster().getName() for inst in block.getInsts())
    memory = [{'instance': inst.getName(), 'master': inst.getMaster().getName()} for inst in block.getInsts()
              if inst.getMaster().isBlock()]
    unknown = sorted(name for name in masters if name not in roles and name not in {r['master'] for r in memory}
                     and any(str(p.getSigType()) not in ('POWER', 'GROUND') for p in
                             next(i for i in block.getInsts() if i.getMaster().getName() == name).getMaster().getMTerms()))
    errors += ['unknown functional master ' + name for name in unknown]

    def ends(net, direction, seen):
        if not net or net.getId() in seen:
            return []
        seen = seen | {net.getId()}
        result = []
        for pin in net.getITerms():
            if str(pin.getMTerm().getIoType()) != direction:
                continue
            inst = pin.getInst()
            role = roles.get(inst.getMaster().getName(), {})
            if role.get('unary'):
                other = [p for p in inst.getITerms() if str(p.getMTerm().getIoType()) != direction]
                for p in other:
                    result += ends(p.getNet(), direction, seen)
            else:
                result.append((pin, role))
        return result

    for port in block.getBTerms():
        if str(port.getSigType()) in ('POWER', 'GROUND') or port.getName() in ('ck', 'ck[0]'):
            continue
        direction = str(port.getIoType())
        endpoints = ends(port.getNet(), 'INPUT' if direction == 'INPUT' else 'OUTPUT', set())
        row = {'port': port.getName(), 'direction': direction, 'endpoints': []}
        if not endpoints:
            if direction == 'INPUT':
                unused_inputs.append(port.getName())
            else:
                errors.append('no native sequential endpoint ' + port.getName())
        for pin, role in endpoints:
            seq = role.get('ff')
            name = pin.getMTerm().getName()
            entry = {'pin': pin.getInst().getName() + '/' + name,
                     'master': pin.getInst().getMaster().getName(), 'actual_lib_ff': seq}
            row['endpoints'].append(entry)
            if not seq:
                function = role.get('pins', {}).get(name, {}).get('function')
                literal = re.sub(r'[()\s]', '', function or '')
                if direction == 'OUTPUT' and literal in ('0', '1', "1'b0", "1'b1"):
                    entry['actual_lib_constant_function'] = function
                    constant_outputs.append({'port': port.getName(), **entry})
                else:
                    errors.append('non-FF boundary endpoint ' + entry['pin'])
            elif direction == 'INPUT':
                next_state = re.sub(r'[()!\s\x27]', '', seq['next_state'] or '')
                reset_pins = re.findall(r'\b[A-Za-z_]\w*\b', (seq['clear'] or '') + ' ' + (seq['preset'] or ''))
                reset_input = port.getName() in ('rst_n', 'rst_n[0]')
                if name != next_state and not (reset_input and name in reset_pins):
                    errors.append('input does not terminate at actual FF D/reset ' + entry['pin'])
        rows.append(row)
    report = {'schema': 'opentallas.native_boundary_inventory.v1', 'PASS': not errors,
              'odb_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'libraries': libraries,
              'native_instances': sum(masters.values()), 'sequential_instances': sum(count for name, count in masters.items() if roles.get(name, {}).get('ff')),
              'macro_instances': memory, 'actual_master_counts': dict(masters), 'boundary_bits': len(rows),
              'constant_outputs_not_FF': constant_outputs, 'unused_inputs_without_endpoints': unused_inputs,
              'errors': errors, 'boundary': rows,
              'scope': 'Native pre-layout FF role/first and last endpoint inventory through Liberty-proven BUF/INV. Reset input can drive actual FF clear/preset. Literal Liberty constant outputs and unused inputs are separately exposed, require source functional correspondence; they are not claimed as FF endpoints. No physical timing, clock envelope, PG, reach, grouped storage capacity, or legal-constant source proof claim.'}
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('PASS', 'native_instances', 'sequential_instances', 'macro_instances', 'boundary_bits', 'errors')}))
    return report['PASS']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('odb', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if audit(args.odb, args.out) else 1)
