#!/usr/bin/env python3
"""Generate a binary-control functional projection, never a timing model."""
import gzip
import hashlib
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent


def groups(text, kind):
    for match in re.finditer(r'\b' + kind + r'\s*\(([^()]*)\)\s*\{', text):
        depth, pos = 1, match.end()
        while depth:
            if text[pos] == '{':
                depth += 1
            elif text[pos] == '}':
                depth -= 1
            pos += 1
        yield match.group(1).strip(), text[match.end():pos - 1]


def field(body, key):
    matches = re.findall(r'\b' + key + r'\s*:\s*([^;]+);', body)
    assert len(matches) == 1, (key, matches)
    return matches[0].strip().strip('"')


def expression(expr, pins):
    assert not re.sub(r'[A-Za-z_][A-Za-z_0-9]*|[!()*+^01\s]', '', expr), expr
    assert set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*', expr)) <= set(pins), expr
    return expr.replace('!', '~').replace('*', '&').replace('+', '|')


def main():
    manifest = json.loads((BASE / 'manifest.json').read_text())
    cells, libraries = {}, {}
    for path in sorted((BASE / 'official').glob('*.lib.gz')):
        content = gzip.decompress(path.read_bytes())
        libraries[path.name] = hashlib.sha256(content).hexdigest()
        for name, body in groups(content.decode(), 'cell'):
            assert name not in cells, name
            cells[name] = body
    result = ['// SIMULATION ONLY: exact frozen Liberty binary functions; no SDF/timing.',
              '// Uninitialized state remains X in a four-state simulator.',
              '`timescale 1ns/1ps']
    ledger = {}
    for name, spec in sorted(manifest['used_masters'].items()):
        body = cells[name]
        pins = dict(groups(body, 'pin'))
        assert set(pins) == set(spec['ports']), (name, set(pins), spec['ports'])
        directions = {pin: field(value, 'direction') for pin, value in pins.items()}
        assert directions == spec['directions'], (name, directions, spec['directions'])
        seq = list(groups(body, 'ff'))
        result.append('module ' + name + '(' + ', '.join(spec['ports']) + ');')
        for pin in spec['ports']:
            result.append('  ' + directions[pin] + (' reg ' if seq and directions[pin] == 'output' else ' ') + pin + ';')
        if seq:
            assert len(seq) == 1 and list(pins).count('QN') == 1
            state, ff = seq[0]
            assert state == 'IQN,IQNN', (name, state)
            assert field(ff, 'clocked_on') == 'CLK'
            assert field(ff, 'next_state') == '!D'
            assert field(pins['QN'], 'function') == 'IQN'
            if name.startswith('DFFASRHQN'):
                assert field(ff, 'clear') == '!SETN'
                assert field(ff, 'preset') == '!RESETN'
                assert field(ff, 'clear_preset_var1') == 'L'
                assert field(ff, 'clear_preset_var2') == 'L'
                result += ['  reg previous_CLK;',
                           '  always @(CLK or RESETN or SETN) begin',
                           "    if (!SETN) QN <= 1'b0;",
                           "    else if (!RESETN) QN <= 1'b1;",
                           "    else if ((CLK === 1'b1) && (previous_CLK === 1'b0)) QN <= ~D;",
                           '    previous_CLK = CLK;',
                           '  end']
                ledger[name] = {'ff': 'posedge CLK: QN=~D; SETN low wins QN=0; otherwise RESETN low QN=1',
                                'scope': 'binary controls only; no UDP uncertain-edge/notifier semantics'}
            else:
                assert name.startswith('DFFHQN')
                result += ['  always @(posedge CLK) QN <= ~D;']
                ledger[name] = {'ff': 'posedge CLK: QN=~D'}
        else:
            functions = {}
            for pin, value in pins.items():
                if directions[pin] == 'output':
                    functions[pin] = field(value, 'function')
                    expr = expression(functions[pin], pins)
                    if expr in ('0', '1'):
                        expr = "1'b" + expr
                    result.append('  assign ' + pin + ' = ' + expr + ';')
            ledger[name] = {'functions': functions}
        result.append('endmodule')
    output = '\n'.join(result) + '\n'
    (BASE / 'functional_projection.v').write_text(output)
    (BASE / 'projection_manifest.json').write_text(json.dumps({
        'scope': 'Unvalidated simulation-only binary-control functional projection; no simulator executed',
        'source_lib_decompressed_sha256': libraries,
        'projection_sha256': hashlib.sha256(output.encode()).hexdigest(),
        'masters': ledger,
        'pending_checks': ['Fleet exhaustive combinational truth tables against original official gate primitives',
                           'HQN both data polarities and between-edge hold',
                           'ASRHQN assert/release RESETN and SETN off-edge at both clock levels',
                           'Both controls low priority and reset release while SETN held low',
                           'Comparison with official UDP after separately approved delayed-net projection',
                           'Native/reference full mechanism miter and causal mutants']
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
