#!/usr/bin/env python3
"""Audit/repair SU tap-to-bank relay clock bindings (TOK-HBM SU31, 2026-10-25).

The SU slice has a serial control clock and a STREAM pg_clk. Its lg_rq/lg_wq
pins belong to pg_clk. Counting serial relays as stream edges corrupts the
fixed return calendar even if READ_RETURN equals the nominal lane count.
Only fully traced SU-bank request paths are eligible for repair. Source is
never modified; --repair-out writes a successor plus a JSON change inventory.
"""
import argparse
import json
import re
from pathlib import Path
import coll_transport as CT


def trace_bit(inst, name, port, bit):
    """Follow a valid bit through sliced/packed relay buses without changing lane."""
    def atoms(expr):
        expr = expr.strip()
        return [x.strip() for x in expr[1:-1].split(',')] if expr.startswith('{') else [expr]
    def width(expr):
        parts = atoms(expr)
        if len(parts) > 1:
            return sum(width(x) for x in parts)
        m = re.search(r"\[(\d+):(\d+)\]$", expr)
        if m:
            return abs(int(m[1]) - int(m[2])) + 1
        if re.search(r"\[\d+\]$", expr):
            return 1
        m = re.match(r"(\d+)'", expr)
        if m:
            return int(m[1])
        h = CT.HOP.search(expr)
        if h and (h[1] or h[3]) in inst:
            hp = inst[h[1] or h[3]][1]
            return width(hp.get('i') or hp.get('a'))
        raise ValueError(f'unknown expression width: {expr}')
    def select(expr, bit):
        for part in reversed(atoms(expr)):
            w = width(part)
            if bit >= w:
                bit -= w
                continue
            m = re.search(r"\[(\d+)(?::(\d+))?\]$", part)
            if m:
                base = int(m[2] or m[1])
                return part[:m.start()], base + bit
            return part, bit
        raise ValueError(f'bit outside expression: {expr}')
    expr, hops, seen = inst[name][1][port], [], set()
    while True:
        net, bit = select(expr, bit)
        m = CT.HOP.fullmatch(net)
        if not m or (m[1] or m[3]) not in inst:
            return hops[::-1], f'{net}[{bit}]'
        hop = m[1] or m[3]
        if hop in seen:
            raise ValueError(f'relay loop {hop}')
        seen.add(hop); hops.append(hop)
        hp = inst[hop][1]
        expr = hp.get('i') or hp.get('a')


def audit(die_v):
    names = {f'su_{q}{g}' for q in ('SW', 'SE', 'NW', 'NE') for g in range(4)}
    names |= {f'vmb_{q}{b}' for q in ('SW', 'SE', 'NW', 'NE') for b in range(8)}
    inst = CT.parse_instances(die_v, names)
    paths, changes = [], {}
    for v in sorted(names):
        if not v.startswith('vmb_') or v not in inst:
            continue
        bp = inst[v][1]
        expected = bp.get('clk')
        for port, source_port in (('rq0', 'lg_rq'), ('wq0', 'lg_wq')):
            if port not in bp:
                continue
            hops, root = trace_bit(inst, v, port, 16 if port == 'rq0' else 280)
            source = re.search(r'\b(su_(?:SW|SE|NW|NE)\d)__' + source_port + r'\b', root)
            if not source:
                continue
            source = source[1]
            source_clock = inst.get(source, ('', {}))[1].get('pg_clk')
            mismatches = []
            for hop in hops:
                master, hp = inst[hop]
                for cp in ('ck', 'clk', 'ckf'):
                    if cp in hp and hp[cp] != expected:
                        mismatches.append(dict(instance=hop, port=cp, clock=hp[cp], expected=expected))
                        # Clock repair is safe only for the ordinary full-cycle
                        # relay used by these paths, never a forwarded landing.
                        if master.startswith(('hbfd_rly', 'hbfd_pad')) and cp == 'ck':
                            changes[hop] = dict(clock=expected, reset=bp.get('rst_n'), old_clock=hp[cp], old_reset=hp.get('rs'))
            paths.append(dict(bank=v, port=port, source=source, source_clock=source_clock,
                              bank_clock=expected, hops=hops, mismatches=mismatches,
                              ok=bool(expected and source_clock == expected and not mismatches)))
    # Returns use the same stream clock, including pads inserted to align
    # individual banks. Audit valid bits to keep packed bundles on their lanes.
    for q in ('SW', 'SE', 'NW', 'NE'):
        for b in range(8):
            v, source = f'vmb_{q}{b}', f'su_{q}{b//2}'
            if v not in inst or source not in inst:
                continue
            bp, sp = inst[v][1], inst[source][1]
            expected = sp.get('pg_clk')
            for port, bit, root_port in (('lg_rr', (b%2)*257+256, 'rr0'), ('lg_w_done', b%2, 'wq_done0')):
                if port not in sp:
                    continue
                hops, root = trace_bit(inst, source, port, bit)
                if f'{v}__{root_port}' not in root:
                    continue
                mismatches = []
                for hop in hops:
                    master, hp = inst[hop]
                    for cp in ('ck', 'clk', 'ckf'):
                        if cp in hp and hp[cp] != expected:
                            mismatches.append(dict(instance=hop,port=cp,clock=hp[cp],expected=expected))
                            if master.startswith(('hbfd_rly','hbfd_pad')) and cp=='ck':
                                changes[hop]=dict(clock=expected,reset=bp.get('rst_n'),old_clock=hp[cp],old_reset=hp.get('rs'))
                paths.append(dict(bank=v,port=port,source=v,source_clock=bp.get('clk'),bank_clock=expected,
                                  hops=hops,mismatches=mismatches,
                                  ok=bool(expected and bp.get('clk')==expected and not mismatches)))
    return dict(schema='opentallas.hbm_su_bank_clock.v1', verdict='PASS' if paths and all(p['ok'] for p in paths) else 'FAIL',
                paths=paths, repair_relays=changes)


def repaired_source(die_v, report):
    source = Path(die_v).read_text()
    for name, change in report['repair_relays'].items():
        rx = re.compile(r'(^\s*hbfd_(?:rly|pad)\w*[^\n]*\b' + re.escape(name) + r'\s*\(\s*\n)(.*?)(^\s*\);)', re.M | re.S)
        def sub(m):
            body = re.sub(r'\.ck\([^\n]*\)', '.ck(' + change['clock'] + ')', m[2])
            if change['reset']:
                body = re.sub(r'\.rs\([^\n]*\)', '.rs(' + change['reset'] + ')', body)
            return m[1] + body + m[3]
        source, n = rx.subn(sub, source)
        if n != 1:
            raise ValueError(f'{name}: expected one ordinary relay instance, got {n}')
    return source


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--die-v', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--repair-out', type=Path)
    a = ap.parse_args()
    r = audit(a.die_v)
    a.out.write_text(json.dumps(r, indent=1) + '\n')
    if a.repair_out:
        if a.repair_out.resolve() == a.die_v.resolve():
            raise ValueError('source overwrite forbidden')
        a.repair_out.write_text(repaired_source(a.die_v, r))
    print(f"SU_BANK_CLOCK {r['verdict']} paths={len(r['paths'])} wrong_clock_relays={len(r['repair_relays'])}")
    return 0 if r['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
