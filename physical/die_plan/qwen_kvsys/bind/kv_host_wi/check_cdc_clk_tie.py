#!/usr/bin/env python3
"""Fail-closed check: the Wi host parent's 4 SAMECLK=1 cdc cores stay on one clock.

COORD ruling 11-10 (KV-HOST-WI, KV-TOK-8 PASS): form S (signed qkd_hr_cdc_ch/pc/hi/ci
views, SAMECLK=1) is valid only while every host clock port that feeds the 8 crossings
of those cores is tied to the single bound clock of kv3_hub_Wi. This script enforces it.

Checks, any failure -> exit 1:
  1. the bound RTL instantiates qkd_host_root_admission_obsx_bo1_c45 exactly once;
  2. each of the 11 crossing clock ports (both sides of all 8 crossings, traced from
     the kv45 host) is connected, and only to the bound module's clock input (`clk` or
     a replication / concatenation of it, nothing else: no alias wires, no gating);
  3. the bound module declares that clock as an input port;
  4. with --parent: each of the 4 cdc cores in parent.sv takes its `ck` from one of the
     11 ports (so a regenerated parent cannot move a core onto an unchecked port).

Usage: check_cdc_clk_tie.py <bound.sv> [--parent parent.sv] [--clk clk] [--json out.json]
"""
import json
import re
import sys

HOST = 'qkd_host_root_admission_obsx_bo1_c45'
# host port -> crossings using it (wclk/rclk), traced from the kv45 elaboration
CROSSING_PORTS = {
    'ck_qm_host': ['cdc_hi.u_hx.wclk', 'cdc_hi.u_cx.rclk'],
    'ck_qm_ingest': ['cdc_hi.u_hx.rclk', 'cdc_hi.u_cx.wclk', 'cdc_ci.u_ox.wclk', 'cdc_ci.u_rx.rclk'],
    'ck_qm_core': ['cdc_ci.u_ox.rclk', 'cdc_ci.u_rx.wclk'],
    'ck_qm_ing_w': ['cdc_ch.u_ing.wclk'],
    'ck_qm_ing_r': ['cdc_ch.u_ing.rclk'],
    'ck_qm_done_w': ['cdc_ch.u_done.wclk'],
    'ck_qm_done_r': ['cdc_ch.u_done.rclk'],
    'ck_phy_rx_w': ['cdc_pc.u_rx.wclk'],
    'ck_phy_rx_r': ['cdc_pc.u_rx.rclk'],
    'ck_phy_tx_w': ['cdc_pc.u_tx.wclk'],
    'ck_phy_tx_r': ['cdc_pc.u_tx.rclk'],
}
CDC_CORES = ('qkd_hr_cdc_ch', 'qkd_hr_cdc_pc', 'qkd_hr_cdc_hi', 'qkd_hr_cdc_ci')


def strip_comments(t):
    t = re.sub(r'/\*.*?\*/', ' ', t, flags=re.S)
    return re.sub(r'//[^\n]*', '', t)


def balanced(t, i):
    """t[i] == '(' -> index just past the matching ')'."""
    d = 0
    for j in range(i, len(t)):
        if t[j] == '(':
            d += 1
        elif t[j] == ')':
            d -= 1
            if d == 0:
                return j + 1
    raise ValueError('unbalanced parentheses')


def instances(t, mod):
    """[(inst_name, port_text)] for every instantiation of module `mod`."""
    out = []
    for m in re.finditer(r'(?<![\w$])' + re.escape(mod) + r'\s*(#\s*\()?', t):
        i = m.end()
        if m.group(1):
            i = balanced(t, i - 1)
        n = re.match(r'\s*([A-Za-z_][\w$]*)\s*\(', t[i:])
        if not n:
            continue  # a module declaration or a name mention, not an instance
        k = i + n.end() - 1
        out.append((n.group(1), t[k + 1:balanced(t, k) - 1]))
    return out


def connections(ports):
    res = {}
    for m in re.finditer(r'\.\s*([A-Za-z_][\w$]*)\s*\(', ports):
        k = m.end() - 1
        res[m.group(1)] = ports[k + 1:balanced(ports, k) - 1].strip()
    return res


def only_clk(expr, clk):
    e = re.sub(r'\s+', '', expr)
    if e == clk:
        return True
    if not (e.startswith('{') and e.endswith('}')):
        return False
    body = e[1:-1]
    m = re.fullmatch(r'(\d+)\{(.*)\}', body)  # {N{...}}
    if m:
        return only_clk(m.group(2), clk)
    parts = []
    d = 0
    cur = ''
    for ch in body:
        if ch == '{':
            d += 1
        elif ch == '}':
            d -= 1
        if ch == ',' and d == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    parts.append(cur)
    return bool(parts) and all(only_clk(p, clk) for p in parts)


def main(argv):
    args = {'--parent': None, '--clk': 'clk', '--json': None}
    pos = []
    it = iter(argv)
    for a in it:
        if a in args:
            args[a] = next(it)
        else:
            pos.append(a)
    if len(pos) != 1:
        print(__doc__)
        return 2
    clk = args['--clk']
    fails = []
    t = strip_comments(open(pos[0]).read())
    if not re.search(r'\binput\b[^;,)]*?\b' + re.escape(clk) + r'\b', t):
        fails.append('bound RTL has no input port named %s' % clk)
    inst = instances(t, HOST)
    if len(inst) != 1:
        fails.append('expected exactly 1 instance of %s, found %d' % (HOST, len(inst)))
    conn = connections(inst[0][1]) if inst else {}
    rows = []
    for p, xs in CROSSING_PORTS.items():
        e = conn.get(p)
        ok = e is not None and only_clk(e, clk)
        rows.append(dict(port=p, crossings=xs, connected=e, ok=ok))
        if not ok:
            fails.append('%s (%s) is connected to %r, not only to %s' % (p, ', '.join(xs), e, clk))
    if args['--parent']:
        pt = strip_comments(open(args['--parent']).read())
        for c in CDC_CORES:
            ci = instances(pt, c)
            if len(ci) != 1:
                fails.append('parent: expected 1 instance of %s, found %d' % (c, len(ci)))
                continue
            ck = re.sub(r'\s+', '', connections(ci[0][1]).get('ck', ''))
            if ck not in CROSSING_PORTS:
                fails.append('parent: %s.ck is %r, not one of the checked crossing ports' % (c, ck))
    verdict = 'FAIL' if fails else 'PASS'
    rep = dict(check='kv_host_wi.cdc_clk_tie.v1', bound=pos[0], parent=args['--parent'], clk=clk,
               host_instance=inst[0][0] if len(inst) == 1 else None, ports=rows, fails=fails, verdict=verdict)
    if args['--json']:
        with open(args['--json'], 'w') as h:
            json.dump(rep, h, indent=1)
    for f in fails:
        print('FAIL', f)
    print(verdict, '%d/%d crossing clock ports tied to %s' % (sum(r['ok'] for r in rows), len(rows), clk))
    sys.stdout.flush()
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
