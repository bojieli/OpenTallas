#!/usr/bin/env python3
"""Source-pinned mapped dependency and clock-root census, not physical closure.

Run via ot-run. Leaves remain candidates; this never removes a declared port or
relabels an upstream source. Dependency cones include state/control feedback.
"""
import argparse
from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def census(module):
    inputs = [(port, i, b) for port, p in module['ports'].items() if p['direction'] == 'input'
              for i, b in enumerate(p['bits']) if isinstance(b, int)]
    reach = defaultdict(int)
    successors = defaultdict(set)
    clocks = defaultdict(int)
    sequential_bits = 0
    for cell in module.get('cells', {}).values():
        kind = cell['type']
        if kind == '$scopeinfo' and not cell.get('connections'):
            continue  # Yosys 0.68 source/hierarchy metadata, not hardware.
        if not kind.startswith('$_'):
            raise ValueError('not a fully generic mapped cell: ' + kind)
        seq = bool(re.match(r'^\$_(?:DFF|SDFF|DFFE|SDFFE|SDFFCE|DFFSR|DLATCH|SR)', kind))
        con = cell['connections']
        dirs = cell['port_directions']
        ins = [b for p, bits in con.items() if dirs.get(p) == 'input' and not (seq and p == 'C')
               for b in bits if isinstance(b, int)]
        outs = [b for p, bits in con.items() if dirs.get(p) == 'output' for b in bits if isinstance(b, int)]
        if seq:
            sequential_bits += len(outs)
            cb = con.get('C', con.get('E', []))
            clocks[str(cb)] += len(outs)
        for b in ins:
            successors[b].update(outs)
    todo = deque()
    for index, (_, _, bit) in enumerate(inputs):
        reach[bit] |= 1 << index
        todo.append(bit)
    while todo:
        bit = todo.popleft()
        for nxt in successors[bit]:
            updated = reach[nxt] | reach[bit]
            if updated != reach[nxt]:
                reach[nxt] = updated
                todo.append(nxt)
    outputs = {}
    used_mask = 0
    for port, p in module['ports'].items():
        if p['direction'] != 'output':
            continue
        mask = 0
        for bit in p['bits']:
            if isinstance(bit, int):
                mask |= reach[bit]
        outputs[port] = mask
        used_mask |= mask

    def decode(mask):
        ports = defaultdict(list)
        for index, (port, bit, _) in enumerate(inputs):
            if mask & (1 << index):
                ports[port].append(bit)
        return dict(ports)

    return dict(sequential_bits=sequential_bits, clock_net_bits=dict(clocks),
                input_bits=len(inputs), output_bits=sum(len(p['bits']) for p in module['ports'].values() if p['direction'] == 'output'),
                dependencies_by_output={p: decode(mask) for p, mask in outputs.items()},
                structurally_used_inputs=decode(used_mask),
                structurally_unused_inputs=decode(((1 << len(inputs)) - 1) ^ used_mask),
                note='Structural mapped support, including feedback and control; unused does not authorize changing the RTL ABI or physical workload')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--yosys', default=str(Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'))
    ap.add_argument('--half', choices=['a', 'b'], required=True)
    ap.add_argument('--column', type=int, choices=range(4), required=True)
    ap.add_argument('--reuse-mapped', action='store_true', help='Analyze an existing map only after its exact generated inputs and script match')
    a = ap.parse_args()
    root = a.root.resolve()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sources = ['rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv',
               'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_return_columns.sv',
               'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_sfu.sv']
    text = (root / sources[0]).read_text()

    def extract(name):
        m = re.search(r'\bmodule\s+' + re.escape(name) + r'\b', text)
        return text[m.start():text.index('endmodule', m.start()) + 9]

    support = (root / sources[2]).read_text()
    sfu = (root / sources[3]).read_text()
    b = sfu.index('module ot_hdc_vline')
    support += '\n' + sfu[b:sfu.index('endmodule', b) + 9]
    support += '\n' + '\n'.join(extract(n) for n in ('ot_s81_hc_ctq', 'ot_s81_hc_ctrs', 'ot_s81_hc_ctra', 'ot_s81_hc_ctrb'))
    original = (root / sources[1]).read_text()
    top = 'ot_s81_hc_ctr' + a.half + '_column'
    match = re.search(r'module\s+' + top + r'\s*#\((.*?)\)\s*\(', original, re.S)
    header = match.group(1)
    for name, value in [('READ_STAGE', 1), ('CHAIN_STEP', 6), ('COLUMN', a.column)]:
        header, n = re.subn(name + r'\s*=\s*\w+', name + ' = ' + str(value), header)
        assert n == 1
    specialized = original[:match.start(1)] + header + original[match.end(1):]
    script = 'read_verilog -sv reference.sv specialized.sv; hierarchy -top ' + top + '; proc; flatten; synth -top ' + top + ' -noabc; write_json mapped.json\n'
    generated = {'reference.sv': support, 'specialized.sv': specialized, 'census.ys': script}
    if a.reuse_mapped:
        for path, expected in generated.items():
            assert (out / path).read_text() == expected, 'stale mapped input: ' + path
        assert 'End of script.' in (out / 'yosys.log').read_text(), 'original synthesis did not finish'
    else:
        for path, expected in generated.items():
            (out / path).write_text(expected)
        with (out / 'yosys.log').open('w') as log:
            subprocess.run([a.yosys, '-s', 'census.ys'], cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
    mapped = json.loads((out / 'mapped.json').read_text())
    result = census(mapped['modules'][top])
    result.update(top=top, params=dict(NG=256, D=5120, NCOL=3, GS=8, S_RD=2, S_RT=4, ML=5, AL=4, READ_STAGE=1, CHAIN_STEP=6, COLUMN=a.column),
                  source_sha256={p: sha(root / p) for p in sources}, specialized_sha256=sha(out / 'specialized.sv'),
                  specialization='Only three target-module parameter defaults changed; no logic edit',
                  scope='CURRENT_SOURCE_GENERIC_DEPENDENCIES_NOT_NATIVE_AREA_OR_PHYSICAL_QUALIFICATION')
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(top=top, column=a.column, sequential_bits=result['sequential_bits'],
                          used={p: len(v) for p, v in result['structurally_used_inputs'].items()})))


if __name__ == '__main__':
    main()
