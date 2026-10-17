#!/usr/bin/env python3
"""Flatten a SOFT die-level parent into its children (H-NETLIST/IDX 2026-10-16, H-DIE grant 6413258a6).

Used by full_die_v16.py --soft-idx NETMAP: the die instance hb_idx (ot_hbm_idx_client_static_sw) is replaced by the
children of the wires-only composition ot_hbm_idx_client_static_soft (net map: idx_soft_netmap_1016.py), as die-level
instances hb_idx__<child>. Works on the bit-level driver map after every edge, relay splice, clock and strap of the
contract is bound to hb_idx's ports, so the die-facing connectivity is exactly the hb_idx port connectivity:
  child input bit  <- ['P', p, b]: whatever drove hb_idx.p[b] (edge, relay station, clock/release, strap, or nothing:
                      then it stays undriven and is listed as an exposed input as before)
                   <- ['N', net]: the child output bit driving that internal net
                   <- ['C', v]: a constant of the composition RTL (first_ord / sid / k literals), recorded as a strap
  every load of hb_idx.p[b] (output) <- the child output bit (or constant / passthrough input) the map names.
No RTL changes: the composition's equivalence with ot_hbm_idx_client_static_sw is proven separately
(idx_soft_equiv_1016.py, results/arch/hbm_idx_soft_parent_1016).
"""
from __future__ import annotations

import collections

# child instance name in the composition -> die slot of the grant (results/arch/hbm_die_v16/idx_soft_parent_grant_1016.json)
IDX_SLOTS = dict(ctl='idx_ctl', operands='idx_op', query='idx_q', scorer0='idx_s0', scorer1='idx_s1', scorer2='idx_s2',
                 scorer3='idx_s3', selector='idx_sel', link='idx_link')


def _runs(items):
    """[(key, src_bit, dst_bit)] sorted -> runs [key, s_lo, s_hi, d_lo, d_hi) with both bits consecutive"""
    out = []
    for key, s, d in items:
        if out and out[-1][0] == key and out[-1][2] == s and out[-1][4] == d:
            out[-1][2] += 1; out[-1][4] += 1
        else:
            out.append([key, s, s + 1, d, d + 1])
    return out


def soft_flatten(parent, nm, insts, ports, drv, E, clocks, straps, rtl, problems, slots=IDX_SLOTS):
    if parent not in insts:
        problems.append(f'soft flatten: {parent} not in the contract'); return
    if any(s['inst'] == parent for s in straps):
        problems.append(f'soft flatten: straps on {parent} are not supported'); return
    pi = insts.pop(parent)
    pports = ports.pop(parent)
    cname = {c: f'{parent}__{c}' for c in nm['children']}
    net_drv = {int(k): (cname[v[0]], v[1], v[2]) for k, v in nm['net_drivers'].items()}
    # ---- new instances
    for c, x in nm['children'].items():
        n = cname[c]
        nq = int(nm.get('params', {}).get('N_Q', 4))
        prm = {'N_Q': nq} if (x['master'] == 'ot_hbm_idx_ctl_static' and nq != 4) else {}   # default N_Q=4 keeps params {}
        insts[n] = dict(master=x['master'], source=x['source'], params=prm, slot=slots.get(c), owner=pi.get('owner'),
                        region='idx_soft', note=f'soft child {c} of {parent} ({pi["master"]}); H-DIE grant 6413258a6')
        ports[n] = rtl.ports(x['master'], x['source'], prm)
        insts[n]['ports'] = ports[n]
        for p, d in x['ports'].items():
            if p not in ports[n] or ports[n][p]['bits'] != len(d['bits']) or ports[n][p]['direction'] != d['direction']:
                problems.append(f'soft flatten: {n}.{p} net map disagrees with the parsed RTL port')
    # ---- driver of each former parent output bit
    def out_src(p, b):
        t = nm['outputs'][p][b]
        if t[0] == 'N':
            return net_drv[int(t[1])]
        if t[0] == 'C':
            return ('CONST', int(t[1]), 0)
        return drv.get((parent, t[1], int(t[2])))           # passthrough of a parent input
    # ---- loads of parent outputs: rewire to the child driver
    for k, s in list(drv.items()):
        if s[0] == parent:
            ns = out_src(s[1], s[2])
            if ns is None:
                del drv[k]
            else:
                drv[k] = ns
    # ---- child inputs
    pin_loads = collections.defaultdict(list)                # (p, b) -> [(child inst, port, bit)]
    soft_straps = collections.defaultdict(list)
    for c, x in nm['children'].items():
        n = cname[c]
        for p, d in x['ports'].items():
            if d['direction'] != 'input':
                continue
            for b, t in enumerate(d['bits']):
                if t[0] == 'P':
                    pin_loads[(t[1], int(t[2]))].append((n, p, b))
                    s = drv.get((parent, t[1], int(t[2])))
                    if s is not None:
                        drv[(n, p, b)] = s
                elif t[0] == 'N':
                    drv[(n, p, b)] = net_drv[int(t[1])]
                else:
                    drv[(n, p, b)] = ('CONST', int(t[1]), 0)
                    soft_straps[(n, p)].append((b, int(t[1])))
    for k in [k for k in drv if k[0] == parent]:
        del drv[k]
    for (n, p), bv in soft_straps.items():
        bv.sort()
        lo = bv[0][0]; hi = bv[-1][0] + 1
        if [b for b, _ in bv] != list(range(lo, hi)):
            problems.append(f'soft flatten: non-contiguous constant bits on {n}.{p}')
        straps.append(dict(inst=n, port=p, lo=lo, hi=hi, value=sum(v << (b - lo) for b, v in bv), master=insts[n]['master'],
                           reason=f'composition constant of {nm["top"]} (RTL literal, not a tie of a real producer)'))
    # ---- clocks / resets
    newc = []
    for c_ in clocks:
        if c_['instance'] != parent:
            newc.append(c_); continue
        seen = set()
        for b in range(c_['bits']):
            for (n, p, cb) in pin_loads.get((c_['port'], b), []):
                if (n, p) not in seen:
                    seen.add((n, p))
                    newc.append(dict(c_, instance=n, port=p, bits=ports[n][p]['bits'],
                                     note=f"soft child port of {parent}.{c_['port']}"))
    clocks[:] = newc
    # ---- edges
    newE = []
    for e in E:
        si, sp, slo, shi = e['source']; di, dp, dlo, dhi = e['sink']
        if si != parent and di != parent:
            newE.append(e); continue
        items = []                                           # ((src inst, src port, dst inst, dst port), sbit, dbit)
        for k in range(shi - slo):
            src = (si, sp, slo + k)
            if si == parent:
                src = out_src(sp, slo + k)
                if src is None or src[0] == 'CONST':
                    continue
            dsts = [(di, dp, dlo + k)] if di != parent else pin_loads.get((dp, dlo + k), [])
            for d in dsts:
                items.append(((src[0], src[1], d[0], d[1]), src[2], d[2]))
        items.sort(key=lambda t: (t[0], t[2]))
        for j, (key, s0, s1, d0, d1) in enumerate(_runs(items)):
            newE.append(dict(e, name=f"{e['name']}__soft{j}", bits=s1 - s0, source=[key[0], key[1], s0, s1],
                             sink=[key[2], key[3], d0, d1], basis=(e.get('basis') or '') + f' | soft {parent} flatten'))
    items = []
    for c, x in nm['children'].items():
        n = cname[c]
        for p, d in x['ports'].items():
            if d['direction'] == 'input':
                for b, t in enumerate(d['bits']):
                    if t[0] == 'N':
                        s = net_drv[int(t[1])]
                        items.append(((s[0], s[1], n, p), s[2], b))
    items.sort(key=lambda t: (t[0], t[2]))
    for j, (key, s0, s1, d0, d1) in enumerate(_runs(items)):
        newE.append(dict(name=f'{parent}_soft_{key[0][len(parent) + 2:]}_{key[1]}__{key[2][len(parent) + 2:]}_{key[3]}_{j}',
                         bits=s1 - s0, source=[key[0], key[1], s0, s1], sink=[key[2], key[3], d0, d1], clock=None,
                         ready_or_credit=False, allowed_exception=None,
                         basis=f'internal net of {nm["top"]} (idx_soft_netmap_1016.py)', region='idx_soft'))
    E[:] = newE
    def map_range(p, lo, hi):
        """hb_idx.p[lo:hi) -> [[child, port, lo, hi]] (inputs: every child load; outputs: the child driver)"""
        it = []
        for k in range(lo, hi):
            if pports[p]['direction'] == 'input':
                it += [((n, cp), cb, cb) for (n, cp, cb) in pin_loads.get((p, k), [])]
            else:
                s = out_src(p, k)
                if s is not None and s[0] not in ('CONST', 'PIN') and s[0] in ports:
                    it.append(((s[0], s[1]), s[2], s[2]))
        it.sort()
        return [[key[0], key[1], s0, s1] for key, s0, s1, _, _ in _runs(it)]
    return dict(parent=parent, master=pi['master'], children={cname[c]: x['master'] for c, x in nm['children'].items()},
                internal_nets=len(net_drv), composition_constants=len(soft_straps), _map_range=map_range,
                _parent_ports=pports)
