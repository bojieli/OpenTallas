#!/usr/bin/env python3
"""S81-P8-C: instance/bit-level hop graph of one frame band from the plan RTL (col_<M>_l4_lp_plan.sv) + macro LEF pins."""
import json, re, subprocess, sys
from pathlib import Path
from collections import defaultdict
WT = Path('/home/ubuntu/wt/s81-p6-1023')
PLAN = WT / 'rtl/dsrom_sys/s81_dv/frame_lp/plan'

def git_text(p):
    f = WT / p
    if f.is_file():
        return f.read_text()
    return subprocess.run(['git', '-C', str(WT), 'show', f'origin/main:{p}'], capture_output=True, text=True, check=True).stdout

_lefc = {}
def lef_pins(lef):
    """pin name -> (dir, (cx, cy)) in R0 macro frame; size"""
    if lef in _lefc:
        return _lefc[lef]
    txt = git_text(lef)
    size = tuple(map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', txt).groups()))
    pins = {}
    for m in re.finditer(r'^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$', txt, flags=re.M | re.S):
        name, body = m.group(1), m.group(2)
        dm = re.search(r'DIRECTION\s+(\w+)', body)
        r = re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', body)
        if not r:
            continue
        x0, y0, x1, y1 = map(float, r.groups())
        pins[name.replace('\\', '')] = (dm.group(1) if dm else 'INPUT', ((x0 + x1) / 2, (y0 + y1) / 2))
    _lefc[lef] = (pins, size)
    return _lefc[lef]

def ev(s, params):
    s = s.strip()
    for k, v in params.items():
        s = re.sub(r'\b%s\b' % k, str(v), s)
    m = re.fullmatch(r'\(?\s*(\d+)\s*==\s*(\d+)\s*\)?\s*\?\s*(\d+)\s*:\s*(\d+)', s)
    if m:
        a, b, c, d = map(int, m.groups())
        return c if a == b else d
    if not re.fullmatch(r'[\d\s()+\-*/]+', s):
        raise ValueError(s)
    return int(eval(s.replace('/', '//')))

def split_top(s, sep=','):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch in '({[':
            depth += 1
        elif ch in ')}]':
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur); cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out

class Band:
    def __init__(self, master, k):
        txt = (PLAN / f'{master}_l4_lp_plan.sv').read_text()
        body = None
        for m in re.split(r'^module ', txt, flags=re.M)[1:]:
            if m.split()[0] == f'{master}_l4_lp_r{k}':
                body = m; break
        self.k = k
        self.params = {}
        self.width = {}            # net -> (msb, lsb)
        self.ports = {}            # port -> dir
        hdr, rest = body.split(');', 1) if False else (None, body)
        for m in re.finditer(r'parameter\s+(?:\w+\s+)?(?:\[[^\]]*\]\s*)?(\w+)\s*=\s*([^,\n;)]+)', body[:4000]):
            try:
                self.params[m.group(1)] = int(m.group(2))
            except ValueError:
                pass
        for m in re.finditer(r'localparam\s+(?:integer\s+)?(\w+)\s*=\s*([^;]+);', body):
            try:
                self.params[m.group(1)] = ev(m.group(2), self.params)
            except Exception:
                pass
        for m in re.finditer(r'^\s*(input|output|inout)?\s*wire\s*(\[[^\]]+\])?\s*(\w+)\s*(?:=\s*(\w+))?\s*(?:[;,]|$)', body, flags=re.M):
            d, rng, n = m.group(1), m.group(2), m.group(3)
            if rng:
                a, b = rng[1:-1].split(':')
                try:
                    self.width[n] = (ev(a, self.params), ev(b, self.params))
                except Exception:
                    self.width[n] = None
            else:
                self.width[n] = (0, 0)
            if d:
                self.ports[n] = d
            if m.group(4):
                self.assigns_extra = getattr(self, 'assigns_extra', []) + [(n, m.group(4))]
        self.assigns = []
        for m in re.finditer(r'^\s*assign\s+(.+?)\s*=\s*(.+?);', body, flags=re.M):
            self.assigns.append((m.group(1), m.group(2)))
        self.assigns += getattr(self, 'assigns_extra', [])
        self.insts = []
        for m in re.finditer(r'^\s+(\w+)\s+(#\(.*?\)\s+)?(u_\w+)\s*\((.*?)\);\s*(//.*)?$', body, flags=re.M):
            mod, par, inst, conns = m.group(1), m.group(2) or '', m.group(3), m.group(4)
            cd = {}
            for c in split_top(conns):
                c = c.strip()
                pm = re.match(r'\.(\w+)\s*\((.*)\)$', c, flags=re.S)
                if pm:
                    cd[pm.group(1)] = pm.group(2).strip()
            pp = {}
            for c in split_top(par[2:-1].strip()[:-1] if par else ''):
                pm = re.match(r'\s*\.(\w+)\s*\((.*)\)\s*$', c)
                if pm:
                    pp[pm.group(1)] = pm.group(2)
            self.insts.append((mod, pp, inst, cd))

    def bits(self, e):
        """MSB-first list of bit ids ('net', i) or None for constants"""
        e = e.strip()
        if not e:
            return []
        if e.startswith('{'):
            inner = e[1:-1].strip()
            rm = re.match(r'^(\d+)\s*\{(.*)\}$', inner, flags=re.S)
            if rm:
                return self.bits('{' + rm.group(2) + '}') * int(rm.group(1))
            out = []
            for p in split_top(inner):
                out += self.bits(p)
            return out
        cm = re.match(r"^(\d+)?'[sS]?([bdhBDH])([0-9a-fA-F_xXzZ]+)$", e)
        if cm:
            return [None] * int(cm.group(1) or 32)
        if re.fullmatch(r'\d+', e):
            return [None] * 32
        m = re.match(r'^(\w+)\s*(\[(.*)\])?$', e, flags=re.S)
        if not m:
            raise ValueError('expr ' + e[:80])
        n, idx = m.group(1), m.group(3)
        w = self.width.get(n)
        if idx is None:
            if w is None:
                return [None]
            msb, lsb = w
            return [(n, i) for i in range(msb, lsb - 1, -1)]
        if '+:' in idx:
            a, b = idx.split('+:')
            a, b = ev(a, self.params), ev(b, self.params)
            return [(n, i) for i in range(a + b - 1, a - 1, -1)]
        if ':' in idx:
            a, b = idx.split(':')
            a, b = ev(a, self.params), ev(b, self.params)
            return [(n, i) for i in range(a, b - 1, -1)]
        return [(n, ev(idx, self.params))]

OUTLINE = (1442.88, 1226.88)
SKIP_MODS = {'ot_pl_land_reset_forest', 'ot_reset_sync'}
CTRL_PORTS = {'ck', 'clk', 'rs', 'rsi', 'rst', 'rst_n', 'rstn', 'reset'}

def _bfmap():
    txt = (WT / 'rtl/dsrom_sys/s81_dv/frame_lp/kit/dsfd_bf_col_kit.sv').read_text()
    body = txt.split('module dsfd_bf_col ', 1)[1].split('endmodule', 1)[0]
    out, skip = {}, False
    for ln in body.splitlines():
        t = ln.strip()
        if t.startswith('`ifdef'):
            skip = True; continue
        if t.startswith('`else'):
            skip = False; continue
        if t.startswith('`endif'):
            skip = False; continue
        if skip:
            continue
        m = re.match(r'assign (\w+)\[(\d+)\] = (\w+)(?:\[(\d+)\])?;', t) or re.match(r'assign (\w+)() = (\w+)(?:\[(\d+)\])?;', t)
        if not m:
            continue
        a, ai, c, ci = m.groups()
        if a.startswith('w_') and c in ('ci', 'rs', 'ck'):
            out[(c, int(ci))] = a[2:] + (f'[{ai}]' if ai != '' else '')
        elif c.startswith('w_') and a in ('r', 'qy'):
            out[(a, int(ai))] = c[2:] + (f'[{ci}]' if ci else '')
    return out
BFMAP = _bfmap()

class UF:
    def __init__(self):
        self.p = {}
    def f(self, a):
        p = self.p
        p.setdefault(a, a)
        while p[a] != a:
            p[a] = p[p[a]]
            a = p[a]
        return a
    def u(self, a, b):
        a, b = self.f(a), self.f(b)
        if a != b:
            self.p[a] = b

def port_xy(bus, i):
    w0, w1 = bus['window_um']
    t = w0 + (i + 0.5) / bus['width'] * (w1 - w0)
    f = bus['face']
    return {'N': (t, OUTLINE[1]), 'S': (t, 0.0), 'E': (OUTLINE[0], t), 'W': (0.0, t)}[f]

def build(master, k, macros, ptype):
    """macros: list of frame_band_macros entries for this band; ptype: die_plan partition type dict.
    returns (nodes, edges): nodes {id: dict(kind M/S/P, ...)}; edges list of (a, aoff, b, boff, label) per bit
    with aoff/boff pin offsets (R0 frame of macro) or None"""
    b = Band(master, k)
    site = {}
    for e in macros:
        n = e['inst'].split('.', 1)[1]
        if n.endswith('.u_view'):
            n = n[:-7]
        site[n] = e
    uf = UF()
    def link(la, lb):
        for x, y in zip(reversed(la), reversed(lb)):
            if x is not None and y is not None:
                uf.u(x, y)
    for l, r in b.assigns:
        link(b.bits(l), b.bits(r))
    drv, ld = defaultdict(list), defaultdict(list)    # bit -> [(node, pin_off, label)]
    nodes = {}
    unk = defaultdict(int)
    for mod, pp, inst, cd in b.insts:
        if mod in SKIP_MODS:
            continue
        if mod == 'ot_pl_pad' and any('lpr' in v for v in cd.values()):
            continue
        if mod == 'ot_pl_seam_w_pl' or (mod == 'ot_pl_pad' and ev(pp.get('N', '1'), b.params) == 0):
            ins, outs = ('i', 'q') if mod == 'ot_pl_seam_w_pl' else ('d', 'q')
            link(b.bits(cd[ins]), b.bits(cd[outs]))
            continue
        if inst in site:
            e = site[inst]
            pins, size = lef_pins(e['lef'])
            nodes[inst] = dict(kind='M', mod=e['module'], e=e)
            for p, ex in cd.items():
                if p in CTRL_PORTS:
                    continue
                bl = b.bits(ex)
                W = len(bl)
                for pos, bt in enumerate(bl):
                    if bt is None:
                        continue
                    i = W - 1 - pos
                    pn = f'{p}[{i}]' if f'{p}[{i}]' in pins else p
                    if e['module'] == 'ot_v41_bf_col':
                        pn = BFMAP.get((p, i), pn)
                    if pn not in pins:
                        unk[(e['module'], p)] += 1
                        continue
                    d, off = pins[pn]
                    if e['orient'] == 'MY':
                        off = (size[0] - off[0], off[1])
                    (drv if d == 'OUTPUT' else ld)[bt].append((inst, off, p))
            continue
        # soft registered node
        st = 1
        if mod == 'ot_pl_pad':
            st = ev(pp.get('N', '1'), b.params)
        if mod == 'ot_pl_seam_r_pl':
            st = max(ev(pp.get('K', '2'), b.params), 2) - 1
        nodes[inst] = dict(kind='S', mod=mod, stages=st)
        for p, ex in cd.items():
            if p in CTRL_PORTS:
                continue
            isout = p in ('o', 'q')
            for bt in b.bits(ex):
                if bt is not None:
                    (drv if isout else ld)[bt].append((inst, None, inst))
    buses = {x['name']: x for x in ptype['buses']}
    for p, d in b.ports.items():
        if p == 'clk':
            continue
        bn = p if p in buses else {'x_i0': 'xo_i0'}.get(p)
        if bn not in buses:
            unk[('PORT', p)] += 1
            continue
        for bt in b.bits(p):
            nid = f'P:{p}'
            nodes.setdefault(nid, dict(kind='P', bus=p))
            (drv if d == 'input' else ld)[bt].append((nid, port_xy(buses[bn], bt[1]), p))
    D, L = defaultdict(list), defaultdict(list)
    for bt, v in drv.items():
        D[uf.f(bt)] += v
    for bt, v in ld.items():
        L[uf.f(bt)] += v
    edges = []
    nodrv = 0
    for r, loads in L.items():
        ds = D.get(r)
        if not ds:
            nodrv += len(loads)
            continue
        for a in ds:
            for c in loads:
                edges.append((a[0], a[1], c[0], c[1], a[2], c[2]))
    return nodes, edges, dict(unknown=dict(unk), loads_without_driver=nodrv, nets=len(L))
