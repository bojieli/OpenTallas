#!/usr/bin/env python3
"""Prepare the exact native-DW629 -> physical-AHUB631 parent wire adapter.

This emits no blackboxes and grants no activation. A real native golden, current
child SIGNED/postroute EQ631, and the strict signed-view adapter remain required.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from rtlnet import Net, split_top, DECL
from kv_core_rtl import inst_blocks


class ContractError(ValueError):
    pass


def module(text, name):
    m = re.search(r'\bmodule\s+' + re.escape(name) + r'\b.*?\bendmodule\b', text, re.S)
    if not m:
        raise ContractError('missing real source module ' + name)
    return m.group(0)


def defaults(text, name):
    m = re.search(r'\bmodule\s+' + re.escape(name) + r'\s*#\((.*?)\)\s*\(', text, re.S)
    if not m:
        raise ContractError('explicit native parameter declaration required: ' + name)
    out = {}
    for item in split_top(m.group(1)):
        p = re.fullmatch(r'\s*parameter\s+(?:(?:integer|\[[^]]+\])\s+)?(\w+)\s*=\s*(.*?)\s*', item)
        if not p:
            raise ContractError('unparsed parameter declaration: ' + item)
        out[p[1]] = re.sub(r'\s+', '', p[2]).lower()
    return out


def overrides(line, master, inst):
    m = re.fullmatch(r'\s*' + re.escape(master) + r'\s*#\((.*)\)\s+' + re.escape(inst) + r'\s*\(\s*', line)
    if not m:
        raise ContractError('exact parameterized instance header required: ' + inst)
    out = {}
    for item in split_top(m[1]):
        p = re.fullmatch(r'\s*\.(\w+)\((.*)\)\s*', item)
        if not p or p[1] in out:
            raise ContractError('unparsed/duplicate parameter override')
        out[p[1]] = re.sub(r'\s+', '', p[2]).lower()
    return out


def bit_text(bit):
    name, index = bit
    return name + '[' + str(index) + ']'


def prepare(parent, native_dw, physical_wrapper, physical_dw, output):
    parent, output = Path(parent), Path(output)
    text = parent.read_text()
    old = Net(parent)
    if old.insts.get('u_ahub', (None,))[0] != 'qkd_ahub_static_dw':
        raise ContractError('current native qkd_ahub_static_dw u_ahub required')
    lines, spans = inst_blocks(text, {'u_ahub'})
    a, z = spans['u_ahub']
    h = next(line for line in lines[a:z + 1] if re.match(r'\s*qkd_ahub_static_dw\b', line))
    native_params = defaults(Path(native_dw).read_text(), 'qkd_ahub_static_dw')
    native_overrides = overrides(h, 'qkd_ahub_static_dw', 'u_ahub')
    if set(native_overrides) - set(native_params):
        raise ContractError('unknown native parameter override')
    native_params.update(native_overrides)
    native_ports = {}
    for line in module(Path(native_dw).read_text(), 'qkd_ahub_static_dw').splitlines():
        d = DECL.match(line)
        if d and d[1] in ('input', 'output', 'inout'):
            native_ports[d[4]] = (d[1], int(d[2]) - int(d[3]) + 1 if d[2] else 1)
    wrapper = Path(physical_wrapper).read_text()
    wh = next((x for x in wrapper.splitlines() if re.match(r'\s*qkd_ahub_static_dw_ck7\b', x)), '')
    child_params = defaults(Path(physical_dw).read_text(), 'qkd_ahub_static_dw_ck7')
    child_overrides = overrides(wh, 'qkd_ahub_static_dw_ck7', 'u_leaf')
    if set(child_overrides) - set(child_params):
        raise ContractError('unknown physical child parameter override')
    child_params.update(child_overrides)
    if native_params != child_params:
        raise ContractError('native/physical effective parameters differ')
    child = Net(physical_wrapper)
    conns = dict(old.insts['u_ahub'][1])
    if set(conns) != set(child.ports) or len(conns) != 20:
        raise ContractError('exact twenty named ports required')
    if set(native_ports) != set(conns) or any(native_ports[p][0] != child.ports[p] for p in conns):
        raise ContractError('native/physical port directions differ')
    if sum(w for _, w in native_ports.values()) != 629 or sum(child.width[p] for p in child.ports) != 631:
        raise ContractError('native629/physical631 boundary differs')
    if 'u_ahub' in old.width or any('__ot_ahub631_am' + str(i) in old.width for i in range(4)):
        raise ContractError('adapter wire collision')
    ck = old.bits(conns['ck'])
    if len(ck) != 1 or ck[0] is None or child.width['ck'] != 7:
        raise ContractError('one native clock and seven physical roles required')
    new_conns = dict(conns, ck='{' + ', '.join([conns['ck']] * 7) + '}')
    declarations, assigns, endpoints = [], [], []
    for port in sorted(conns):
        bits = old.bits(conns[port])
        if any(b is None for b in bits):
            raise ContractError('unresolved endpoint/constant in ' + port)
        if port == 'ck':
            continue
        if re.fullmatch(r'am[0-3]', port):
            if child.ports[port] != 'output' or child.width[port] != 35 or len(bits) != 36:
                raise ContractError('exact AM36 -> AM35 contract required')
            wire = '__ot_ahub631_' + port
            declarations.append('    wire [34:0] ' + wire + ';')
            new_conns[port] = wire
            for i, bit in enumerate(reversed(bits)):
                rhs = "1'b0" if i == 1 else f'{wire}[{i if i == 0 else i - 1}]'
                assigns.append('    assign ' + bit_text(bit) + ' = ' + rhs + ';')
                endpoints.append(dict(port=port, native_bit=i, parent=list(bit), physical_bit=None if i == 1 else (i if i == 0 else i - 1)))
        elif len(bits) != child.width[port]:
            raise ContractError('unmodified endpoint width differs: ' + port)
    body = ['    // PREP ONLY: exact typed AHUB631 parent adapter; child qualification is separate.']
    body += declarations + assigns + ['    qkd_ahub u_ahub (']
    body += [',\n'.join(f'        .{p}({new_conns[p]})' for p in conns), '    );']
    rewritten = '\n'.join(lines[:a] + body + lines[z + 1:])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rewritten)
    new = Net(output)
    if old.ports != new.ports or any(old.width[p] != new.width[p] for p in old.ports):
        raise ContractError('external parent ABI changed')
    if {k: v for k, v in old.insts.items() if k != 'u_ahub'} != {k: v for k, v in new.insts.items() if k != 'u_ahub'}:
        raise ContractError('non-AHUB instance connectivity changed')
    if new.bits(new.insts['u_ahub'][1]['ck']) != ck * 7:
        raise ContractError('seven clock roles not bound to the original logical clock')
    for port in conns:
        if port == 'ck' or re.fullmatch(r'am[0-3]', port):
            continue
        if old.bits(conns[port]) != new.bits(new.insts['u_ahub'][1][port]):
            raise ContractError('unmodified AHUB endpoint changed: ' + port)
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    return dict(schema='opentallas.kv.ahub_parent_wire_adapter.v1', status='PREP_ONLY', activation_allowed=False,
                native_instance='qkd_ahub_static_dw u_ahub', physical_instance='qkd_ahub u_ahub', instance_preserved=True,
                native_bits=629, physical_bits=631, named_ports=20, cycles_added=0,
                effective_parameters=native_params, am_endpoints=endpoints,
                clock_roles={f'ck[{i}]': list(ck[0]) for i in range(7)}, parent_ABI_unchanged=True,
                other_instances_unchanged=True, native_parent_sha256=digest(parent), adapted_parent_sha256=digest(output),
                physical_wrapper_sha256=digest(physical_wrapper), physical_dw_sha256=digest(physical_dw),
                native_golden='original parent + original native DW source, never a blackboxed golden',
                required=['current exact child SIGNED + postroute EQ631', 'qualified source/parameter/port identity',
                          'seven internal clock-tap dispatch and root clock-model gates',
                          'CTL separate dead-drop + boot+2/mission0 whole-parent composition',
                          'strict signed-view activation adapter; this PREP helper does not activate views'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ['native-parent', 'native-dw', 'physical-wrapper', 'physical-dw', 'out-parent', 'report']:
        ap.add_argument('--' + name, required=True)
    ap.add_argument('--prepare-only', action='store_true')
    a = ap.parse_args()
    if not a.prepare_only:
        ap.error('no release activation path: --prepare-only required; retain strict SIGNED/EQ child gates')
    result = prepare(a.native_parent, a.native_dw, a.physical_wrapper, a.physical_dw, a.out_parent)
    Path(a.report).write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(dict(status=result['status'], ports=20, physical_bits=631, cycles_added=0)))


if __name__ == '__main__':
    main()
