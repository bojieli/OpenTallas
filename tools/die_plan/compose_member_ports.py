#!/usr/bin/env python3
"""Rename the ports of composed cuts to the member-port names of the hardened core view.

A composed cut (bind_compose spec, asbuilt.compose) names its boundary ports after the parent nets it replaced
(vm_kq, vm_rr__b771, tkx_w_addr); the hard core built from the same members names them after the members
(split_conn.py: writer_kq0..7, vmasm_rd_il, writer_tkw_d).  Same terminals, different names, so the bound parent
cannot instantiate the core view.  This tool rewrites only the port table of the matching cores, keyed on the
exact {member, port, bit} anchors already in the spec: every bit keeps its anchor, so the connection does not
change.  Each renamed port is the union of the bits that anchor on one member port, in member-bit order.

Bits with several anchors (clock fan-out) keep their port.  --add-input PORT=MEMBER.PORT adds an input whose bits
are anchored on the member's port (as-built constant straps omitted from the cut); bind_compose accepts '0'/'1'
endpoint constants.  Fails closed: a bit range with holes, a direction conflict or a name collision is an error.

usage: compose_member_ports.py IN OUT --inst REGEX --prefix u_writer=writer_ --prefix u_vmasm=vmasm_
                               [--add-input writer_sid=u_writer.sid:2]
"""
import argparse
import json
import re
import sys


def roles(path):
    return path.rsplit('.', 1)[-1]


def rename(core, prefixes, add_inputs):
    old = core['ports']
    new = {}
    stats = {'renamed': [], 'kept': [], 'added': []}
    groups = {}
    order = []
    for pn, pd in old.items():
        d = pd['dir']
        bits = pd['bits']
        # one anchor per bit, one member port for the whole group?
        slots = {}
        anchored = True
        for b in bits:
            a = b if isinstance(b, list) else [b]
            if len(a) != 1:
                anchored = False
                break
            a = a[0]
            r = roles(a['member'])
            if r not in prefixes:
                anchored = False
                break
            slots.setdefault((r, a['port']), {})[a['bit']] = a
        if not anchored:
            new[pn] = pd
            stats['kept'].append(pn)
            continue
        for (r, mp), m in slots.items():
            target = prefixes[r] + mp
            if target in groups and groups[target][0] != d:
                raise SystemExit(f'{core["inst"]}: {target}: direction conflict')
            if target not in groups:
                groups[target] = (d, {})
                order.append(target)
            for bi, a in m.items():
                if bi in groups[target][1]:
                    raise SystemExit(f'{core["inst"]}: {target}[{bi}] anchored twice')
                groups[target][1][bi] = [a]
        stats['renamed'].append(pn)
    for t in order:
        d, bits = groups[t]
        n = len(bits)
        if sorted(bits) != list(range(n)):
            raise SystemExit(f'{core["inst"]}: {t}: bits have holes: {sorted(bits)[:8]} of {n}')
        if t in new or t in old and old[t] is not None and t not in stats['renamed']:
            if t in new:
                raise SystemExit(f'{core["inst"]}: {t}: name collision')
        new[t] = {'dir': d, 'bits': [bits[i] for i in range(n)]}
    for spec in add_inputs:
        name, member = spec
        role, port, width = member
        if name in new:
            continue
        ms = [m for m in core['members'] if roles(m) == role]
        if len(ms) != 1:
            raise SystemExit(f'{core["inst"]}: --add-input {name}: {len(ms)} members named {role}')
        new[name] = {'dir': 'input', 'bits': [[{'member': ms[0], 'port': port, 'bit': i}] for i in range(width)]}
        stats['added'].append(name)
    core['ports'] = new
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--inst', required=True, help='regex matching core inst')
    ap.add_argument('--prefix', action='append', required=True, metavar='ROLE=PREFIX', help='member role -> port prefix')
    ap.add_argument('--add-input', action='append', default=[], metavar='PORT=ROLE.PORT:WIDTH')
    a = ap.parse_args(argv)
    prefixes = dict(x.split('=', 1) for x in a.prefix)
    adds = []
    for spec in a.add_input:
        name, rest = spec.split('=', 1)
        role_port, width = rest.rsplit(':', 1)
        role, port = role_port.split('.', 1)
        adds.append((name, (role, port, int(width))))
    with open(a.input) as f:
        doc = json.load(f)
    rx = re.compile(a.inst)
    hits = 0
    for core in doc['cores']:
        if not rx.fullmatch(core['inst']):
            continue
        hits += 1
        s = rename(core, prefixes, adds)
        print(core['inst'], {k: (len(v), v[:6]) for k, v in s.items()})
    if not hits:
        raise SystemExit(f'no core matches {a.inst}')
    with open(a.output, 'w') as f:
        json.dump(doc, f)
    print('wrote', a.output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
