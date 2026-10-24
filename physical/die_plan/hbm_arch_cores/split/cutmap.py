#!/usr/bin/env python3
"""ELEM-HBM/SPLIT (2026-10-24): per-bit map of a B2r2 split-piece plan pin bus onto its master and canonical RTL top.

The B2r2 pins of an over-cap split piece are the HBM-P5 netcut boundary (pins_cut/netcut.py + gen_core_ports.busify):
one bus per (label, dir), label = the master top port the net reaches (lab_p), else the first member hierarchical pin
on the net (lab_m), else '~' + the first outside hierarchical pin (lab_o), else 'glue'.  netcut only kept bit COUNTS,
so the bit order inside a bus is fixed here, from the master structure:

    plan bus L, bit i  =  the i-th boundary net of L in ascending bit index ON THE LABELLING PIN
                          (master port bit for lab_p, member / outside instance pin bit for lab_m / lab_o);
                          'glue' buses (no labelling pin): ascending bit index on the include-root module port the
                          net crosses (see Piece.order_glue).

so a bus that is one pin keeps that pin's bit order and two plan pins of one net (tkm root x_..tile_0..ins_b[i] and
tile k ..ins_b[i]) carry the same index.

The master is re-elaborated from RTL (the as-built netlists are gone): yosys hierarchy + proc + opt_clean, every module
kept except the instances on the include / exclude path prefixes (netcut inlines exactly those), flatten -> design A
(yosys JSON).  netcut's labelling is re-run on A (cells in hierarchical-name order, internal cells first like the
as-built std cells) and every bus width is checked against the B2r2 pins file (MISMATCH = refused, plan item).

    analyse(A, include, exclude) -> Piece: classes (net ids of A), labels, plan bus -> [net id per bit]
"""
import collections
import json
import re
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'physical', 'die_plan', 'hbm', 'pins_cut'))
import gen_core_ports                                              # noqa: E402

CONST = ('0', '1', 'x', 'z')


def top_module(js, top):
    return js['modules'][top]


def scopes_of(mod):
    """flattened scope name -> hdl path ('/'-joined levels) from the $scopeinfo cells."""
    out = {}
    for c, x in mod['cells'].items():
        if x['type'] == '$scopeinfo':
            hd = x.get('attributes', {}).get('hdlname')
            out[c] = '/'.join(hd.split(' ')) if hd else c
    return out


def cell_path(name, cell, scopes):
    """hdl path of a cell: public cells by hdlname, flattened private cells by their $flatten scope prefix."""
    hd = cell.get('attributes', {}).get('hdlname')
    if hd:
        return '/'.join(hd.split(' '))
    if not name.startswith('$flatten\\'):
        return name                                  # cell of the top itself
    rest = name[len('$flatten\\'):]
    best = ''
    for s in scopes:
        if rest.startswith(s + '.') and len(s) > len(best):
            best = s
    if not best:
        raise ValueError(f'no scope for {name}')
    return scopes[best] + '/' + rest[len(best) + 1:]


def under(path, prefixes):
    return any(path == p or path.startswith(p + '/') for p in prefixes)


def order_key(path, internal):
    """as-built write_verilog order: hierarchical levels, sorted; internal (std / $) cells before named instances."""
    lv = path.split('/')
    return [((0 if (internal and k == len(lv) - 1) else 1), x) for k, x in enumerate(lv)]


class Piece:
    pass


def analyse(js, top, include, exclude=(), ren=None, strip='', glue_root=None):
    """netcut on design A.  include / exclude: hdl paths ('/'-joined, twin naming; '' = the whole master).
    ren(label) -> as-built label text (before busify).  Returns Piece."""
    mod = top_module(js, top)
    scopes = scopes_of(mod)
    hier = set(js['modules'])
    ren = ren or (lambda s: s)

    def ism(p):
        inc = ('' in include) or under(p, include)
        return inc and not under(p, exclude)
    users = collections.defaultdict(set)
    drv, lab_p, lab_m, lab_o = set(), {}, {}, {}
    pins = collections.defaultdict(list)        # net -> [(path, port, idx, dir, member, hierarchical)]
    for pn, p in mod['ports'].items():
        for i, b in enumerate(p['bits']):
            if b in CONST:
                continue
            users[b].add('o')
            lab_p.setdefault(b, (pn, i))
    cells = []
    for c, x in mod['cells'].items():
        if x['type'] == '$scopeinfo':
            continue
        path = cell_path(c, x, scopes)
        internal = x['type'].startswith('$') and x['type'] not in hier
        cells.append((order_key(path, internal), c, x, path, internal))
    cells.sort(key=lambda t: t[0])
    members = []
    for _, c, x, path, internal in cells:
        mm = ism(path)
        if mm:
            members.append((path, x['type'], c))
        pd = x.get('port_directions', {})
        for pn, bl in x['connections'].items():
            d = pd.get(pn)
            if d is None:
                raise ValueError(f'{c}: no direction for {pn}')
            for i, b in enumerate(bl):
                if b in CONST:
                    continue
                users[b].add('m' if mm else 'o')
                pins[b].append((path, pn, i, d, mm, not internal))
                if mm:
                    if not internal:
                        lab_m.setdefault(b, (path, pn, i))
                    else:
                        lab_m.setdefault(b, None)
                    if d == 'output':
                        drv.add(b)
                elif not internal:
                    lab_o.setdefault(b, (path, pn, i))
    P = Piece()
    P.members = members
    P.pins = pins
    res = dict(inp=collections.Counter(), out=collections.Counter())
    P.cls = {}                                    # net -> (label text, dir, sort key)
    for b in lab_m:
        if 'o' not in users[b]:
            continue
        if b in lab_p:
            lbl, key = lab_p[b][0], ('p', lab_p[b][1])
        elif lab_m[b] is not None:
            pth, pn, i = lab_m[b]
            lbl, key = ren(f'{pth}.{pn}'), ('m', i)
        elif b in lab_o:
            pth, pn, i = lab_o[b]
            lbl, key = '~' + ren(f'{pth}.{pn}'), ('o', i)
        else:
            lbl, key = 'glue', ('g', glue_root(b, pins[b]) if glue_root else None)
        d = 'out' if b in drv else 'inp'
        res[d][lbl] += 1
        P.cls[b] = (lbl, d, key)
    names = gen_core_ports.busify(res, strip)
    lbls = [(key, l) for key in ('inp', 'out') for l in sorted(res[key])]
    l2n = {kl: nm for kl, nm in zip(lbls, names)}
    P.ports = names                               # [[bus, dir, width, 0]] exactly as gen_core_ports
    P.bus = collections.defaultdict(list)
    for b, (lbl, d, key) in P.cls.items():
        P.bus[l2n[(d, lbl)][0]].append((key, b))
    for nm in P.bus:
        ks = [k for k, _ in P.bus[nm]]
        if any(k[1] is None for k in ks):
            raise ValueError(f'bus {nm}: no bit order key (glue without glue_root)')
        if len(set(ks)) != len(ks):
            raise ValueError(f'bus {nm}: duplicate bit order keys')
        P.bus[nm] = [b for _, b in sorted(P.bus[nm])]
    P.dirs = {nm[0]: nm[1] for nm in names}
    return P


def check_plan(P, plan_pins):
    """plan pins file rows -> list of mismatches (bus, plan width, derived width)."""
    pw = collections.Counter(re.sub(r'\[\d+\]$', '', p['name']) for p in plan_pins)
    dw = {nm: w for nm, _, w, _ in P.ports}
    bad = [(b, pw.get(b), dw.get(b)) for b in sorted(set(pw) | set(dw)) if pw.get(b) != dw.get(b)]
    return bad
