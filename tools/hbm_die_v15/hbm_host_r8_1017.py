#!/usr/bin/env python3
"""H-DIE-R8 2026-10-17 host-side die binding (post-layer on the generated d4f contract + die.v, after HBM-TIE and HBM-FAULT).

(1) cp_rx fold (HBMA-HOST2 e0619da11, CLOSED hdie_host_cprx_r1-r1-1807890a7, main 9a6c6dfe3): host_cp_landing
    (ot_hbm_host_landing256) + host_cp_packet (ot_hbm_host_packet_static) -> ONE instance host_cp_rx = ot_hbm_host_cp_rx
    (landing PINREG=1 + packet RXREG=0 inside, the 512-b landing->packet bus is internal; default params TXC=32
    RRELAY=1 = the closed view's).  Port map: landing in_v/in_data/pop -> same names, landing fault -> land_fault, every
    packet port except rx_valid/rx_packet/rx_ready -> same name.  The three landing<->packet edges are dropped.
    Slot: host_cp (the shared host region; the folded tile is 246.24 x 194.4).
(2) host_status (ot_hbm_status_join_fa after hbm_fault_1017.py): RRELAY=1 (regional reset relay, as the closed r2 join
    hdie_host_status_r2 and the successor kit hdie_host_status_fa_r3).
(3) HBM-FAULT leaves fl_/fs_/fr_: slot = their own name (grants patch tools/hbm_die_v15/v16_layers/r8_host_grants_patch.json
    gives each a 21.6 um slot beside its sources; without the patch the GEN places them by connectivity).  hbm_fault_1017
    names the SOURCE instance as the slot, which would squeeze a leaf into a full tile slot (su_<Q><k>, coll_<Q>).

usage: hbm_host_r8_1017.py contract IN.json[.gz] OUT.json[.gz]
       hbm_host_r8_1017.py die IN_die.v OUT_die.v
       hbm_host_r8_1017.py grants GRANTS.json PATCH.json OUT.json      (append the patch slots; refuses name clashes)
"""
import gzip
import json
import re
import sys

REGION = 'hbm_host_r8_1017'
LAND, PKT, RX = 'host_cp_landing', 'host_cp_packet', 'host_cp_rx'
RX_M = 'ot_hbm_host_cp_rx'
HS = 'rtl/hbm_accel/host_static_20261015/'
RX_SRC = HS + 'ot_hbm_host_cp_rx.sv'
RX_DEPS = ['rtl/hbm_accel/io_native_20261014/ot_hbm_host_landing256.sv', HS + 'ot_hbm_host_packet_static.sv', 'rtl/lib/ot_rst_relay.sv']
INTERNAL = {'out_v', 'out_data', 'out_ready', 'rx_valid', 'rx_packet', 'rx_ready'}
LEAF_RE = re.compile(r'^f[lsr]_(SW|SE|NE|NW)\d?$')


def ld(p):
    return json.load(gzip.open(p) if p.endswith('.gz') else open(p))


def dump(c, p):
    s = json.dumps(c, indent=1)
    (gzip.open(p, 'wt') if p.endswith('.gz') else open(p, 'w')).write(s)


def rename(inst, port):
    """(old inst, port) -> (new inst, port) or None for the internal landing<->packet ports."""
    if inst == LAND:
        if port in INTERNAL:
            return None
        return RX, {'fault': 'land_fault'}.get(port, port)
    if inst == PKT:
        if port in INTERNAL:
            return None
        return RX, port
    return inst, port


def contract(cin, cout):
    c = ld(cin)
    I, E = c['instances'], c['edges']
    land, pkt = I.pop(LAND), I.pop(PKT)
    assert land['master'] == 'ot_hbm_host_landing256' and pkt['master'] == 'ot_hbm_host_packet_static', (land['master'], pkt['master'])
    assert not land['params'] and not pkt['params'], (land['params'], pkt['params'])
    ports = {p: v for p, v in pkt['ports'].items() if p not in INTERNAL}
    for p in ('in_v', 'in_data', 'pop'):
        ports[p] = land['ports'][p]
    ports['land_fault'] = land['ports']['fault']
    I[RX] = dict(pkt, master=RX_M, source=RX_SRC, params={}, rtl_deps=RX_DEPS, ports=ports, region=pkt.get('region'),
                 note=f'{REGION}: folded host_cp_landing + host_cp_packet (ot_hbm_host_cp_rx, CLOSED hdie_host_cprx_r1-r1-1807890a7); '
                      'landing PINREG=1 + packet RXREG=0, no 512-b die bus')
    n0 = len(E)
    out = []
    for e in E:
        s, d = e['source'], e['sink']
        if {s[0], d[0]} <= {LAND, PKT}:
            continue                                  # landing <-> packet (now inside the fold)
        rs, rd = rename(s[0], s[1]), rename(d[0], d[1])
        assert rs and rd, e
        out.append(dict(e, source=[rs[0], rs[1]] + list(s[2:]), sink=[rd[0], rd[1]] + list(d[2:])))
    c['edges'] = E = out
    cr = []
    for x in c['clock_resets']:
        if x['instance'] == LAND:
            continue
        cr.append(dict(x, instance=RX) if x['instance'] == PKT else x)
    c['clock_resets'] = cr
    c['straps'] = [dict(x, inst=rename(x['inst'], x['port'])[0], port=rename(x['inst'], x['port'])[1])
                   if x.get('inst') in (LAND, PKT) else x for x in c.get('straps', [])]
    oo = []
    for o in c['open_outputs']:
        r = rename(o[0], o[1])
        if r is None:
            continue
        oo.append([r[0], r[1]] + list(o[2:]))
    c['open_outputs'] = oo
    M = c['masters']
    for m_ in ('ot_hbm_host_landing256', 'ot_hbm_host_packet_static'):
        M[m_] -= 1
    M[RX_M] = M.get(RX_M, 0) + 1
    c['masters'] = {k: v for k, v in M.items() if v}
    # (2) host status join reset relay
    hs = I['host_status']
    assert hs['master'] == 'ot_hbm_status_join_fa', 'run hbm_fault_1017.py contract first'
    hs['params']['RRELAY'] = 1
    # (3) fault leaves: own slots
    nl = 0
    for n, i in I.items():
        if LEAF_RE.match(n) and i['master'] == 'ot_hbm_fault_leaf':
            i['slot'] = n; nl += 1
    assert nl == 22, nl
    s = c['summary']
    s.update(instances=len(I), masters=len(c['masters']), edges=len(E), edge_bits=sum(e['bits'] for e in E),
             clock_reset_ports=len(c['clock_resets']), open_output_ports=len(c['open_outputs']))
    c.setdefault('notes', {})[REGION] = __doc__.split('usage:')[0].strip()
    dump(c, cout)
    print(f'contract: {LAND}+{PKT} -> {RX} ({RX_M}), edges {n0} -> {len(E)}, host_status RRELAY=1, {nl} fault leaves own slots')


def _block(v, master, inst):
    m = re.search(r'\n  ' + re.escape(master) + r'(?: #\([^\n]*\))? ' + re.escape(inst) + r' \(\n(.*?)\n  \);\n', v, re.S)
    assert m, inst
    conns = dict(re.findall(r'\.(\w+)\((.*?)\)(?:,|$)', m.group(1), re.M))
    return m, conns


def die(din, dout):
    v = open(din).read()
    ml, cl = _block(v, 'ot_hbm_host_landing256', LAND)
    mp, cp = _block(v, 'ot_hbm_host_packet_static', PKT)
    conns = [('clk', cp['clk']), ('rst_n', cp['rst_n']),
             ('in_v', cl['in_v']), ('in_data', cl['in_data']), ('pop', f'{RX}__pop')]
    conns += [(p, n) for p, n in cp.items() if p not in INTERNAL and p not in ('clk', 'rst_n')]
    conns.append(('land_fault', f'{RX}__land_fault'))
    assert cl['clk'] == cp['clk'] and cl['rst_n'] == cp['rst_n']
    blk = f'\n  {RX_M} {RX} (\n' + ',\n'.join(f'    .{p}({n})' for p, n in conns) + '\n  );\n'
    a, b = sorted([ml, mp], key=lambda m: m.start())
    v = v[:a.start()] + blk + v[a.end():b.start()] + '\n' + v[b.end():]
    for w in ('host_cp_landing__out_v', 'host_cp_landing__out_data', 'host_cp_packet__rx_ready'):
        v, k = re.subn(r'  wire \[\d+:0\] ' + w + ';\n', '', v)
        assert k == 1, w
        assert not re.search(r'\b' + w + r'\b', v), w
    v = re.sub(r'\bhost_cp_landing__pop\b', f'{RX}__pop', v)
    v = re.sub(r'\bhost_cp_landing__fault\b', f'{RX}__land_fault', v)
    v = re.sub(r'\bhost_cp_packet__(\w+)', RX + r'__\1', v)
    assert not re.search(r'\bhost_cp_(landing|packet)\b', v)
    v, k = re.subn(r'(ot_hbm_status_join_fa #\([^\n]*?\.FCLR\(125\))\) host_status \(', r'\1, .RRELAY(1)) host_status (', v)
    assert k == 1, 'host_status (run hbm_fault_1017.py die first)'
    open(dout, 'w').write(v)
    print(f'die.v: {LAND}+{PKT} -> {RX} ({RX_M}), host_status RRELAY=1')


def grants(gin, patch, gout):
    g = json.load(open(gin)); p = json.load(open(patch))
    have = {s['name'] for s in g['slots']}
    clash = [s['name'] for s in p['slots'] if s['name'] in have]
    assert not clash, clash
    g['slots'] += p['slots']
    json.dump(g, open(gout, 'w'), indent=1)
    print(f'grants: +{len(p["slots"])} slots ({p.get("region")})')


if __name__ == '__main__':
    {'contract': contract, 'die': die, 'grants': grants}[sys.argv[1]](*sys.argv[2:])
