"""Extract the exact 32 mapped bank predecoders; emit untrusted official cube hints.

No mapped state is waived. The official LEC must prove every cube jointly.
The small miter separately checks the actual extracted next-state cone against
the native every-edge command capture, including the first capture (BASE).
"""
import argparse
import hashlib
import itertools
import json
import re
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mapped', type=Path, required=True)
    ap.add_argument('--native', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    s, native = a.mapped.read_text(), a.native.read_text()
    cells, drivers = {}, {}
    for m in re.finditer(r'^  (\S+) (\S+)\s+\(\n(.*?)^  \);', s, re.M | re.S):
        typ, name, body = m.groups()
        ports = dict(re.findall(r'\.(\w+)\((.*?)\)', body, re.S))
        cells[name] = (typ, ports)
        for q in ('Y', 'QN', 'Q'):
            if q in ports:
                drivers[ports[q].strip()] = (typ, ports)
    records, hints, assertions, declarations = [], [], [], []
    captured = set()
    for i in range(287018, 287050):
        name = f'_{i}_'
        typ, ports = cells[name]
        assert typ == 'DFFHQNx1_ASAP7_75t_R' and ports['CLK'] == 'store0_clk'
        leaves = set()

        def expression(sig):
            if re.fullmatch(r'cmd1_D\[\d+\]', sig):
                leaves.add(int(re.search(r'\[(\d+)\]', sig)[1]))
                return sig.replace('cmd1_D', 'd')
            t, p = drivers[sig]
            vs = [expression(v.strip()) for k, v in p.items() if k not in ('Y', 'Q', 'QN')]
            if t.startswith('BUF'):
                return vs[0]
            if t.startswith('INV'):
                return '(~' + vs[0] + ')'
            op = '&' if t.startswith(('AND', 'NAND')) else '|' if t.startswith(('OR', 'NOR')) else None
            assert op, (sig, t)
            x = '(' + op.join(vs) + ')'
            return '(~' + x + ')' if t.startswith(('NAND', 'NOR')) else x

        expr = expression(ports['D'])
        bits = sorted(leaves)
        assert len(bits) == 4 and bits in [list(range(720, 724)), list(range(744, 748))]
        ones = []
        for vals in itertools.product((0, 1), repeat=4):
            x = expr
            for bit, value in zip(bits, vals):
                x = x.replace(f'd[{bit}]', str(value))
            if eval(x, {'__builtins__': {}}, {}) & 1:
                ones.append(list(vals))
        assert len(ones) == 1, (name, ones)
        # lec.py flop_key canonicalizes ASAP7 IQN (!D) back to positive D.
        keys = [f'ff:u_dut.cmd1_Q[{b}]' for b in bits]
        hints.append(['gate', f'ff:u_dut.{name}', ['cube', 'gold', keys, ones[0]]])
        records.append(dict(gate_key=f'ff:u_dut.{name}', cell=typ, clock='store0_clk',
                            async_reset=None, enable=None, D_net=ports['D'], QN_net=ports['QN'],
                            canonical_polarity='positive D (lec.py IQN inversion)',
                            native_capture_bits=bits, cube=ones[0], extracted_D_expression=expr))
        captured.update(bits)
        declarations.append(f'reg g{i}; always @(posedge clk) g{i} <= {expr};')
        predicate = ' & '.join(f"(q[{b}] == 1'b{v})" for b, v in zip(bits, ones[0]))
        assertions.append(f'assert(g{i} == ({predicate}));')
    # Check exact selected native source, not just a hand-written capture model.
    captures = []
    cap_outputs = re.search(r'assign \{([^}]+)\} = g_compose_m3_q;', native)
    cap_inputs = re.search(r'always @\(posedge \{store0_clk\[0\]\}\) g_compose_m3_q <= \{([^}]+)\};', native)
    assert cap_outputs and cap_inputs
    cap_map = dict(zip([x.strip() for x in cap_outputs[1].split(',')],
                       [x.strip() for x in cap_inputs[1].split(',')]))
    assert len(cap_map) == 768
    for bit in sorted(captured):
        am = re.search(rf'assign cmd1_Q\[{bit}\] = (\w+);', native)
        assert am, bit
        net = am[1]
        assert cap_map[net] == f'cmd1_D[{bit}]', (bit, net, cap_map[net])
        captures.append(dict(bit=bit, native_output_net=net,
                             register='g_compose_m3_q', clock='store0_clk[0]',
                             D=cap_map[net], enable=None, reset=None))
    # Arbitrary initial states; filled becomes true on the FIRST actual capture.
    # At that point all related state is established from the same arbitrary D.
    header = 'module predecode(input clk,input [767:0] d);\nreg [767:0] q; reg filled=0;\nalways @(posedge clk) begin q<=d; filled<=1; end\n'
    body = '\n'.join(declarations)
    check = '\nalways @* if(filled) begin\n' + '\n'.join(assertions) + '\nend\nendmodule\n'
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/'predecode.sv').write_text(header + body + check)
    # Mutant is the same extracted actual cone with one input polarity changed.
    old = declarations[0]
    new = old.replace('d[744]', '(~d[744])')
    assert old != new
    (a.out/'predecode_mutant.sv').write_text(header + body.replace(old, new, 1) + check)
    (a.out/'lec_hints.json').write_text(json.dumps(hints, indent=2)+'\n')
    receipt = dict(status='EXTRACTED_NOT_SOURCE_EQ', mapped_sha256=hashlib.sha256(s.encode()).hexdigest(),
                   native_sha256=hashlib.sha256(native.encode()).hexdigest(), records=records,
                   native_captures=captures, base='after first actual capture; arbitrary initial states and input D',
                   original_official_verdict='UNPROVEN', whole_proof_rerun=False)
    (a.out/'correspondence.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(f'EXTRACTED {len(records)} exact predecoder cubes and {len(captures)} native captures')


if __name__ == '__main__':
    main()
