#!/usr/bin/env python3
"""Compare a real RTL header and exact place_pin TCL with die-assigned pins."""
import argparse
import ast
import json
import math
import re
from pathlib import Path


def number(expr, values):
    node = ast.parse(expr.replace('$clog2', 'clog2'), mode='eval').body
    def walk(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return n.value
        if isinstance(n, ast.Name):
            return values[n.id]
        if isinstance(n, ast.BinOp):
            a, b = walk(n.left), walk(n.right)
            if isinstance(n.op, ast.Add): return a + b
            if isinstance(n.op, ast.Sub): return a - b
            if isinstance(n.op, ast.Mult): return a * b
            if isinstance(n.op, (ast.Div, ast.FloorDiv)): return a // b
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'clog2':
            return math.ceil(math.log2(walk(n.args[0])))
        raise ValueError(f'unsupported RTL constant {expr}')
    return walk(node)


def ports(path, master):
    text = re.sub(r'//[^\n]*', '', path.read_text())
    m = re.search(r'\bmodule\s+' + re.escape(master) + r'\s*#\((.*?)\)\s*\((.*?)\)\s*;', text, re.S)
    if not m:
        raise ValueError(f'no real parameterized module {master}')
    values = {}
    for decl in m[1].split(','):
        decl = re.sub(r'\b(parameter|integer)\b', '', decl).strip()
        name, expr = decl.split('=', 1)
        values[name.strip()] = number(expr.strip(), values)
    out, width = {}, 1
    for decl in m[2].split(','):
        decl = decl.strip()
        full = re.match(r'(input|output)\s+(?:wire|reg)\s+(?:\[([^]]+)\]\s*)?(\w+)$', decl)
        if full:
            if full[2]:
                hi, lo = full[2].split(':')
                width = abs(number(hi, values) - number(lo, values)) + 1
            else:
                width = 1
            name = full[3]
        elif re.fullmatch(r'\w+', decl):
            name = decl
        else:
            raise ValueError(f'unparsed real RTL port {decl!r}')
        out[name] = width
    return out


def check(assignment, rtl, tcl):
    a = json.loads(assignment.read_text())
    widths = ports(rtl, a['master'])
    expected = {}
    for face, names in a['pins'].items():
        for name in names:
            for i in range(widths[name]):
                pin = name if widths[name] == 1 else f'{name}[{i}]'
                expected[pin] = (face, a['pin_ranges'][name])
    for name, groups in a.get('split_ports', {}).items():
        for group in groups:
            hi, lo = group['bits']
            for i in range(lo, hi + 1):
                pin = f'{name}[{i}]'
                if pin in expected: raise ValueError(f'duplicate assigned pin {pin}')
                expected[pin] = (group['face'], group['range'])
    actual_ports = {name if n == 1 else f'{name}[{i}]' for name, n in widths.items() for i in range(n)}
    if set(expected) != actual_ports:
        raise ValueError(f'RTL/assignment mismatch missing={sorted(actual_ports-set(expected))} extra={sorted(set(expected)-actual_ports)}')
    placed = {}
    pattern = r'place_pin\s+-pin_name\s+\{([^}]+)\}\s+-layer\s+(\S+)\s+-location\s+\{(\S+)\s+(\S+)\}'
    for name, layer, x, y in re.findall(pattern, tcl.read_text()):
        if name in placed: raise ValueError(f'duplicate placed pin {name}')
        placed[name] = (layer, float(x), float(y))
    if set(placed) != set(expected):
        raise ValueError(f'placed/assigned mismatch missing={sorted(set(expected)-set(placed))} extra={sorted(set(placed)-set(expected))}')
    for name, (face, (lo, hi)) in expected.items():
        layer, x, y = placed[name]
        if layer != a['face_layers'][face]: raise ValueError(f'{name}: wrong layer {layer}')
        edge = 0 if face in ('W', 'S') else a['outline']['w' if face == 'E' else 'h']
        fixed, along = (x, y) if face in ('W', 'E') else (y, x)
        if abs(fixed-edge) > 0.001 or not lo-0.025 <= along <= hi+0.025:
            raise ValueError(f'{name}: ({x},{y}) outside assigned {face} {lo}..{hi}')
    return {'master': a['master'], 'ports': len(widths), 'bits': len(placed), 'verdict': 'PASS'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('assignment', type=Path)
    p.add_argument('rtl', type=Path)
    p.add_argument('tcl', type=Path)
    args = p.parse_args()
    print(json.dumps(check(args.assignment, args.rtl, args.tcl), sort_keys=True))


if __name__ == '__main__':
    main()
