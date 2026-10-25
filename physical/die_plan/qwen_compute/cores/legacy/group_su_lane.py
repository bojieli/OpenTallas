#!/usr/bin/env python3
"""Extract actual five-leaf SU lane groups from a verified bound partition.

This is a hierarchy-only transform. Ports contain exactly the live cut bits;
in particular the SC return is 35 bits for lane0/4 and one bit for the others,
rather than the provisional plan's even 10/10/9/9 division. Child RTL, reset
and all existing pipeline stages are unchanged. A manifest maps every bit
back to its bound source expression for the plan/binder integration.
"""
import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

CELL = re.compile(r"^\s+(\w+)\s+(u_u_(?:exp|head|lrly|rcp|rsq)(\d+))\s*\((.*?)\);", re.M | re.S)
PORT = re.compile(r"\.(\w+)\(([^()]*)\)")
WIRE = re.compile(r"\bwire\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*;")
REF = re.compile(r"\b(w_u_(?:exp|head|lrly|rcp|rsq)\d+_\w+)(?:\[(\d+)(?::(\d+))?\])?")
EXT = re.compile(r"\b(x_su_c(?:_p1)?_i_q)(?:\[(\d+)(?::(\d+))?\])?")


def bitrefs(expr, widths, pattern=REF):
    out = []
    for m in pattern.finditer(expr):
        n, hi, lo = m.groups()
        h, l = (widths[n]-1, 0) if hi is None else (int(hi), int(lo or hi))
        out += [(n, b) for b in range(h, l-1, -1)]
    return out


def norm(s, lane):
    return re.sub(rf"\b(w_u_|u_u_)(exp|head|lrly|rcp|rsq){lane}(?=_|\b)",
                  lambda m: ("w_" if m[1] == "w_u_" else "u_") + m[2], s)


def pack(bits, lane=None):
    xs = [f"{n}[{b}]" for n,b in bits]
    if lane is not None:
        xs = [norm(x, lane) for x in xs]
    return "{" + ", ".join(xs) + "}"


def extract(text, lane, side):
    widths = {n: int(h)-int(l)+1 if h else 1 for h,l,n in WIRE.findall(text)}
    cells = [m for m in CELL.finditer(text) if int(m[3]) == lane]
    if len(cells) != 5:
        raise ValueError(f"lane{lane}: expected five children, got {len(cells)}")
    names = {m[2] for m in cells}
    selected = {n for n in widths if re.match(rf"w_u_(exp|head|lrly|rcp|rsq){lane}_", n)}
    decls = [f"    wire [{widths[n]-1}:0] {norm(n,lane)};" for n in sorted(selected)]
    external_widths = {n: widths[n] for n in widths if n.startswith('x_su_c')}
    fields, off, child_text = [], 0, []
    for m in cells:
        ports = []
        for pn, expr in PORT.findall(m[4]):
            refs = bitrefs(expr, external_widths, EXT)
            if refs:
                width = len(refs)
                fields.append(dict(child=norm(m[2],lane),port=pn,offset=off,width=width,
                                   source_expr=expr, source_bits=refs))
                expr = f"c_i[{off} +: {width}]"
                off += width
            ports.append(f"        .{pn}({norm(expr,lane)})")
        child_text.append(f"    {m[1]} {norm(m[2],lane)} (\n" + ",\n".join(ports) + "\n    );")
    if not 700 <= off <= 760:
        raise ValueError(f"lane{lane}: unexpected actual input width {off}")
    groups = defaultdict(set)
    consumers = []
    for m in re.finditer(r"u_bout_(\w+)\s*\([^\n]*?\.d\((.*?)\),\s*\.ea", text):
        bus, expr = m.groups()
        bits = [b for b in bitrefs(expr,widths) if b[0] in selected]
        if not bits:
            continue
        if bus.startswith('x_su_c') or bus == 'flt_o': group = 'c_o'
        elif bus in ('x_ctl_o','x_stm_o','x_sc_o'): group = bus[2:]
        else: raise ValueError(f"unclassified output bus {bus}")
        groups[group].update(bits)
        consumers.append(dict(bus=bus, group=group, bits=bits))
    group_bits = {g: sorted(bs, key=lambda b:(norm(b[0],lane),b[1]), reverse=True)
                  for g,bs in groups.items()}
    for g in ('c_o','ctl_o','stm_o','sc_o'):
        if not group_bits.get(g):
            raise ValueError(f"lane{lane}: no live {g}")
    # Every externally consumed selected-child bit must be present, including a
    # bit serving several consumers. Declared but unused leaf outputs stay local.
    remainder = text
    for m in reversed(cells): remainder = remainder[:m.start()] + remainder[m.end():]
    remainder = WIRE.sub('', remainder)
    observed = {b for b in bitrefs(remainder,widths) if b[0] in selected}
    mapped = set().union(*group_bits.values())
    if observed != mapped:
        raise ValueError(f"lane{lane}: unmapped/misclassified cut bits {observed-mapped}, extra{mapped-observed}")
    ports = ['    input wire clk,', '    input wire rst_n,', f'    input wire [{off-1}:0] c_i,']
    for i,(g,bs) in enumerate(group_bits.items()):
        ports.append(f"    output wire [{len(bs)-1}:0] {g}" + (',' if i+1<len(group_bits) else ''))
    body = '\n'.join(ports) + '\n);\n' + '\n'.join(decls) + '\n' + '\n'.join(child_text)
    for g,bs in group_bits.items():body += f"\n    assign {g} = {pack(bs,lane)};"
    body += '\nendmodule\n'
    signature = hashlib.sha256(body.encode()).hexdigest()
    return dict(side=side,lane=lane,fields=fields,groups=group_bits,consumers=consumers,
                signature=signature, widths={'c_i':off,**{g:len(bs) for g,bs in group_bits.items()}},
                child_modules=[m[1] for m in cells],body=body,
                reference_cells=[m[0].strip() for m in cells],
                reference_wires={n:widths[n] for n in sorted(selected)},
                external_wires=external_widths)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('bound_rtl')
    ap.add_argument('out')
    a = ap.parse_args()
    out = Path(a.out);out.mkdir(parents=True,exist_ok=True)
    classes, lanes = {}, []
    for side in ('w','e'):
        for region in (0,1):
            path = Path(a.bound_rtl)/f'qfd_qc_sl{side}_su_l{region}.sv'
            text = path.read_text()
            for lane in range(region*4,region*4+4):
                r = extract(text,lane,side)
                key = (side,r['signature'])
                if key not in classes:
                    name = f'qfd_qc_su_lane_{side}_c{sum(k[0]==side for k in classes)}'
                    classes[key] = name
                    (out/f'{name}.sv').write_text('// Grouped unchanged verified bound children; +0 cycles.\n'
                                                '`default_nettype none\nmodule '+name+' (\n'+r['body']+'`default_nettype wire\n')
                    (out/f'{name}.reference.json').write_text(json.dumps(r,indent=2)+'\n')
                r.pop('body')
                r.update(module=classes[key],bound_source=str(path),bound_sha256=hashlib.sha256(text.encode()).hexdigest(),
                         additional_cycles=0)
                lanes.append(r)
    manifest=dict(schema='opentallas.qc.su_lane_groups.v1',classes=sorted(classes.values()),lanes=lanes,
                  status='CANDIDATE: wrappers require lane miter+mutant before kit/plan adoption',
                  findings=['Original plan c_o counts destinations and double-counts lane0 l_last fanout.',
                            'Original sc_o division10/10/9/9 disagrees with actual35/1/1/1.',
                            'Original provisional core pin tables omit clk/rst_n pins.'])
    (out/'groups.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'classes':manifest['classes'], 'lanes':[{k:r[k] for k in ['side','lane','module','widths']} for r in lanes]},indent=2))


if __name__ == '__main__':main()
