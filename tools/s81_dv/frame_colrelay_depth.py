#!/usr/bin/env python3
"""Emit the opt-in h10 r0 p1 relay-depth form and its cycle/area ledger.

The input is generated frame_band_plan output. Only col_h10_l4_lp_r0 is
changed. Select COLRELAY_P1=1 in the plan contents for the measured p1 types.
The default parameter preserves the input datapath and all original instances.
"""
import argparse
import json
import re
from pathlib import Path

LINEAR = {'u_lpl_11_r': (66, 2), 'u_lpl_12_r': (2, 1),
          'u_y_es_p0_1': (2, 2), 'u_y_rr_1_0': (66, 1),
          'u_y_so_1_0': (2, 1), 'u_y_so_3_0': (2, 1),
          'u_y_x2_3_0': (536, 1)}
BRANCH = {'u_y_xa_1_0': (283, 'xai', 'i_x0'),
          'u_y_xb_1_0': (266, 'xbi', 'i_x1')}


def instances(text):
    out = {}
    for n, ln in enumerate(text.splitlines()):
        m = re.match(r'^\s+(\w+) (?:#\(.*?\) )?(u_\w+) \((\..*)\);', ln)
        if m:
            out[m[2]] = (n, m[1], dict(re.findall(r'\.(\w+)\(((?:[^()]|\([^()]*\))*)\)', m[3])))
    return out


def leaf(rsi):
    m = re.match(r'^(\w+)\[\((\d+)\)\s*\+:\s*\d+\]$', rsi)
    return f'{m[1]}[{m[2]}]' if m else rsi


def chain(name, width, depth, ck, rs, inp, *, kept=False):
    """A whole pipeline; all data stages use the same reset epoch."""
    out = []
    prev = inp
    for j in range(depth):
        net = f'{name}_s{j}'
        out.append(f'    wire [{width-1}:0] {net};')
        prim = 'ot_s81_rly_k' if kept else 'ot_s81_rly'
        extra = f', .ID({j})' if kept else ''
        out.append(f'    {prim} #(.W({width}), .RSREG(1){extra}) u_y_cr_{name}_{j} '
                   f'(.ck({ck}), .rs({rs}), .i({prev}), .o({net}));')
        prev = net
    return out, prev


def transform(text):
    pat = r'(^module col_h10_l4_lp_r0 #\(.*?^endmodule)'
    matches = list(re.finditer(pat, text, re.M | re.S))
    if len(matches) != 1:
        raise ValueError('need exactly one col_h10_l4_lp_r0 module')
    m = matches[0]
    block = m[1]
    if 'COLRELAY_P1' in block:
        raise ValueError('already transformed')
    block = block.replace('parameter integer MUT = 0,',
                          'parameter integer MUT = 0,\n    parameter integer COLRELAY_P1 = 0,', 1)
    if 'parameter integer COLRELAY_P1' not in block:
        raise ValueError('expected MUT parameter anchor')
    ins = instances(block)
    required = set(LINEAR) | set(BRANCH) | {"u_bs0", "u_bs2", "u_t1"}
    if required - set(ins):
        raise ValueError(f"missing measured groups/sinks: {sorted(required-set(ins))}")
    lines = block.splitlines()
    tails = []
    ledger = []
    for inst, (width, added) in LINEAR.items():
        n, mod, c = ins[inst]
        pin = 'o'
        orig = c[pin]
        if not re.fullmatch(r'\w+|\{[^{}]+\}', orig):
            raise ValueError(f'{inst}: unsupported output {orig}')
        stem = f'cr_{inst[2:]}'
        # Keep the original instance and register hierarchy; only its wire is renamed.
        raw = f'{stem}_old'
        lines[n] = lines[n].replace(f'.o({orig})', f'.o({raw})', 1)
        tails.append(f'    wire [{width-1}:0] {raw};')
        ck = c.get('ck')
        rs = c.get('rs', leaf(c.get('rsi', '')))
        if not ck or not rs:
            raise ValueError(f'{inst}: missing clock/reset')
        add, net = chain(stem, width, added, ck, rs, raw)
        tails.extend(add)
        tails.append(f'    assign {orig} = COLRELAY_P1 ? {net} : {raw};')
        ledger.append(dict(group=inst, width=width, added_cycles=added,
                           added_data_ff=width*added))
    for inst, (width, tpin, bpin) in BRANCH.items():
        n, mod, c = ins[inst]
        old = c['o']
        # Independently kept first stages prevent three identical-D branches merging.
        for sink, pin, depth in [('u_bs0', bpin, 3), ('u_t1', tpin, 2), ('u_bs2', bpin, 1)]:
            sn, sm, sc = ins[sink]
            if sc[pin] != old:
                raise ValueError(f'{inst}: {sink}.{pin} is not its complete bus')
            stem = f'cr_{inst[2:]}_{sink[2:]}'
            add, net = chain(stem, width, depth, c['ck'], c['rs'], c['i'], kept=True)
            tails.extend(add)
            selected = f'{stem}_selected'
            tails.append(f'    wire [{width-1}:0] {selected};')
            tails.append(f'    assign {selected} = COLRELAY_P1 ? {net} : {old};')
            # A sink line may have already been edited by the other branch bus.
            if f'.{pin}({old})' not in lines[sn]:
                raise ValueError(f'{sink}.{pin}: replacement anchor absent')
            lines[sn] = lines[sn].replace(f'.{pin}({old})', f'.{pin}({selected})', 1)
            ledger.append(dict(group=inst, sink=sink, pin=pin, width=width,
                               added_cycles=depth-1, candidate_data_ff=width*depth))
    # Preserve the baseline x/go/cfg alignment at the receiving boundaries.
    for sink, pin, width, added in [('u_bs0', 'i_cfg', 54, 2),
                                     ('u_bs0', 'i_go', 1, 2),
                                     ('u_t1', 'cci', 15, 1),
                                     ('u_e0', 'go_tag', 2, 2)]:
        sn, sm, sc = ins[sink]
        ck = sc.get('ck', sc.get('clk')); rs = sc.get('rs', sc.get('rst_n'))
        if pin not in sc or not ck or not rs:
            raise ValueError(f'{sink}: incomplete alignment interface')
        old = sc[pin]
        stem = f'cr_align_{sink[2:]}_{pin}'
        add, net = chain(stem, width, added, ck, rs, old)
        tails.extend(add)
        selected = f'{stem}_selected'
        tails.append(f'    wire [{width-1}:0] {selected};')
        tails.append(f'    assign {selected} = COLRELAY_P1 ? {net} : {old};')
        if f'.{pin}({old})' not in lines[sn]:
            raise ValueError(f'{sink}.{pin}: alignment anchor absent')
        lines[sn] = lines[sn].replace(f'.{pin}({old})', f'.{pin}({selected})', 1)
        ledger.append(dict(group='control_alignment', sink=sink, pin=pin,
                           width=width, added_cycles=added,
                           added_data_ff=width*added))
    lines.insert(len(lines)-1, '\n'.join(tails))
    output = text[:m.start()] + '\n'.join(lines) + text[m.end():]
    manifest = dict(schema='opentallas.s81.colrelay_depth.v1',
                    select='contents.u_r0.params.COLRELAY_P1=1; p1 measured types only',
                    groups=ledger, exactness_scope='component delay; frame calendar must mirror every branch delta',
                    reset='each added stage uses original source reset leaf; release overlap must be scheduled',
                    default='COLRELAY_P1=0 retains original cycle behavior')
    return output, manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--from', dest='src', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    out, report = transform(Path(a.src).read_text())
    Path(a.out).write_text(out)
    Path(a.report).write_text(json.dumps(report, indent=2)+'\n')
    print('COLRELAY_P1 groups', len(report['groups']))


if __name__ == '__main__':
    main()
