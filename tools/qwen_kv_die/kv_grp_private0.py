"""Strict selected-source GRP private ABI deletion, never a physical qualification.

No leaf, equation, state, clock, reset, or schedule changes. Unknown source
specializations refuse instead of silently applying a historical exemption.
"""
import hashlib
import re

SELECTED_SHA256 = 'df66545140a103b45170c9132cf19e521945c61c8fc649e836df4bb9c49e6e97'
MODULE_SHA256 = {
    'qkd_kvs_grp': '40515e24839ae0bcb6172e2a820044c024198596a6d332160f295459bea14743',
    'qkd_kvs_grp_h': '1fce3160686a1d27a90412f881996787edbacc22e12e924cc4952ed9ff570aed',
}
DELETED = ('x__tok', 'x__tep', 'y__tok', 'y__tep')


def module_body(text, name):
    match = re.search(r'\bmodule ' + re.escape(name) + r'\s*\(.*?\bendmodule', text, re.S)
    if not match:
        raise ValueError(f'private0 missing selected module {name}')
    return match.group(0)


def check_selected(body, name):
    if hashlib.sha256(body.encode()).hexdigest() != MODULE_SHA256[name]:
        raise ValueError(f'private0 selected module identity changed: {name}')


def private_text(text):
    """Emit the two distinct private modules from the exact selected public file."""
    if hashlib.sha256(text.encode()).hexdigest() != SELECTED_SHA256:
        raise ValueError('private0 selected full source identity changed')
    out = []
    for name in MODULE_SHA256:
        body = module_body(text, name)
        check_selected(body, name)
        body = body.replace('module ' + name + ' (', 'module ' + name + '_private0 (', 1)
        for port in DELETED:
            body, n = re.subn(r'^    (?:input|output) wire \[\d+:0\] ' + port + r',\n', '', body, flags=re.M)
            assert n == 1, port
        for equation in ('    assign y__tok = x__tok;\n', '    assign y__tep = x__tep;\n'):
            assert body.count(equation) == 1
            body = body.replace(equation, '')
        body = body.replace('input wire [12:0] x__est,', 'input wire x__est,')
        body = body.replace('assign y__est__0_1 = x__est[0:0];', 'assign y__est__0_1 = x__est;')
        if name.endswith('_h'):
            body = body.replace('    output wire [270:0] o_dn,\n', '')
            body = body.replace('input wire [270:0] i_ctl,', 'input wire [193:0] i_ctl,')
            body = body.replace('    assign o_dn = {i_ctl[193:183], i_ctl[270:194], i_ctl[182:0]};\n', '')
        out.append(body + '\n')
    return '`timescale 1ns/1ps\n// Stage 1 ABI deletion only; not a physical-safe design.\n' + '\n'.join(out)


def apply_tiles(tiles, emit):
    """Update the actual generator schema before RTL, binding, parent and pin maps."""
    counts = {'grp': 0, 'grp_h': 0}
    for tile in tiles.values():
        kind = tile['kind']
        if kind not in counts:
            continue
        name = 'qkd_kvs_' + kind
        check_selected(module_body(emit(tile, name), name), name)
        ports = tile['ports']
        for port in DELETED:
            del ports[port]
        ports['x__est'].update(width=1, scalar=True)
        ports['y__est__0_1']['expr'] = 'x__est'
        if kind == 'grp_h':
            del ports['o_dn']
            ports['i_ctl']['width'] = 194
        counts[kind] += 1
    if counts != {'grp': 28, 'grp_h': 4}:
        raise ValueError(f'private0 selected replica counts changed: {counts}')


def parent_connections(text):
    """Explicit low-bit slices at the parent, retaining all producer nets.

    The existing die buses retain their original widths and other consumers.
    Never rely on an implicit Verilog truncation for the new private ABI.
    """
    counts = {'qkd_kvs_grp_private0': 0, 'qkd_kvs_grp_h_private0': 0}

    def change(match):
        master, instance, raw = match.groups()
        pairs = re.findall(r'\.(\w+)\(([^()]*)\)', raw)
        if len(pairs) != len(set(p for p, _ in pairs)):
            raise ValueError(f'private0 duplicate named parent port: {instance}')
        conns = dict(pairs)
        for port in DELETED + (('o_dn',) if master.endswith('_h_private0') else ()):
            conns.pop(port, None)
        est = conns['x__est']
        est_net = re.fullmatch(r'(\w+)(?:\[(?:12|0):0\])?', est)
        if not est_net:
            raise ValueError(f'private0 expected full EST producer net: {instance}: {est}')
        conns['x__est'] = est_net[1] + '[0:0]'
        if master.endswith('_h_private0'):
            ctl = conns['i_ctl']
            ctl_net = re.fullmatch(r'(\w+)(?:\[(?:270|193):0\])?', ctl)
            if not ctl_net:
                raise ValueError(f'private0 expected full control producer net: {instance}: {ctl}')
            conns['i_ctl'] = ctl_net[1] + '[193:0]'
        counts[master] += 1
        return f'  {master} {instance} (' + ', '.join(f'.{p}({e})' for p, e in conns.items()) + ');'

    result = re.sub(r'^  (qkd_kvs_grp(?:_h)?_private0) (slg_\w+) \((.*)\);$', change, text, flags=re.M)
    if counts != {'qkd_kvs_grp_private0': 28, 'qkd_kvs_grp_h_private0': 4}:
        raise ValueError(f'private0 parent replica counts changed: {counts}')
    return result
