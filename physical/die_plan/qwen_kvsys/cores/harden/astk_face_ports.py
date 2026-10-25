#!/usr/bin/env python3
"""Emit an ASTK core wrapper with exclusive tc launch flops and a fault landing.

Feed the output and updated qkd_astk_static_leaves.sv to the core kit generator.
The four tc ports and full qo port keep their original edge. Incoming fault
b gains one cycle with an unreset data capture and reset valid flag. Measured
WN delta: +78 FF total; no added command or nominal token cycles.
"""
import argparse
import json
import re
from pathlib import Path


def transform(text):
    if 'codex_astk_tc_faces' in text:
        raise ValueError('ASTK faces already transformed')
    names = re.findall(r'output wire \[14:0\] (\w+__tc)', text)
    if len(names) != 4:
        raise ValueError(f'expected four 15-bit tc output ports, found {names}')
    controller = re.search(r'(qkd_astk_ctl_s(?:_p)?) #\(([^\n]+)\) (\w+) \(', text)
    if not controller:
        raise ValueError('expected one qkd_astk_ctl_s instance')
    text = text.replace(controller.group(0),
                        f'{controller.group(1)} #({controller.group(2)}, .PORT_REGS(1)) {controller.group(3)} (\n        .tc_faces(codex_astk_tc_faces), .qo_face(codex_astk_qo_face),', 1)
    for face, name in enumerate(names):
        for bit in range(15):
            old = rf'assign {re.escape(name)}\[{bit}\] = n\d+\[{bit}\];'
            text, count = re.subn(old, f'assign {name}[{bit}] = codex_astk_tc_faces[{15*face+bit}];', text)
            if count != 1:
                raise ValueError(f'expected one alias {name}[{bit}], got {count}')
    qo = re.search(r'output wire \[571:0\] (\w+__qo)', text)
    if not qo:
        raise ValueError('expected full qo output port')
    for bit in range(572):
        text, count = re.subn(rf'assign {re.escape(qo.group(1))}\[{bit}\] = n\d+\[{bit}\];',
                              f'assign {qo.group(1)}[{bit}] = codex_astk_qo_face[{bit}];', text)
        if count != 1:
            raise ValueError(f'expected one qo alias bit{bit}, found{count}')
    fault = '.b(g_phys_fault_u_fault__b[0])'
    if text.count(fault) != 1:
        raise ValueError('expected one ASTK incoming fault pin')
    text, count = re.subn(r'qkd_astk_fault_join (\w+) \(', r'qkd_astk_fault_join #(.PORT_REGS(1)) \1 (', text)
    if count != 1:
        raise ValueError('expected one fault join instance')
    marker = '    wire [0:0] n0;'
    if text.count(marker) != 1:
        raise ValueError('expected generated core local declarations')
    text = text.replace(marker, '''    // ASTK face fix: exclusive command launches and an input-fault capture.
    wire [59:0] codex_astk_tc_faces;
    wire [571:0] codex_astk_qo_face;
''' + marker)
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    a.output.write_text(transform(a.source.read_text()))
    print(json.dumps(dict(source=str(a.source), output=str(a.output), extra_flops_estimate=78,
                         tc_cycles=0, incoming_fault_cycles=1)))


if __name__ == '__main__':
    main()
