#!/usr/bin/env python3
"""HBM-BIND (2026-10-24): generate the 8-SM B2 die top (NW + NE quadrants of the r18h5 16-SM as-built die + the die-level
blocks) as a TRANSPORT-COLLAPSED logical netlist, from the r18h5 die netlist and a machine-readable bind delta.

    python3 tools/hbm_b2/b2_top.py --die physical/die_plan/hbm/bind/inputs/die_r18h5.v.gz \
        --asbuilt physical/die_plan/hbm/bind/asbuilt.json --delta results/arch/hbm_arch_1024/b2_bind_wiring.json \
        --out DIR

Method
  1. Parse the r18h5 netlist (instances, port expressions, wire widths, top ports).
  2. Collapse every as-built transport instance (asbuilt.json `transport`: relays, long-hop forwarded-clock stages,
     landings, pads) bit-exactly: each leaf input bit is traced back to its source bit (a leaf output bit, a die input
     port bit or a constant) and the as-built register stages on that path are counted.  The plan binder
     (tools/die_plan/bind.py) re-inserts the B2 plan's own stations; the r18h5 stage counts are written to
     DIR/b2_paths.json as the reference latency of every kept path (never hidden).
  3. Keep instances by the delta `keep` rule (quadrant tags NW/NE, untagged die-level blocks, explicit keep list,
     explicit drop list); drop the rest.
  4. Apply the delta per kept instance: `remaster` (new master / params), `port_map` (old port bit ranges -> new port
     bit ranges, e.g. 4-quadrant slot buses -> 2-quadrant buses), `reattach` (an input bit range re-sourced from a kept
     instance's output range: S-edge SerDes endpoints onto the NW/NE COLL masters, in-band host, ...), `drop_ports`
     (ports the 2-quadrant master no longer has).
  5. Emit DIR/die_b2.v (module hbm_b2_die) and DIR/b2_top_report.json: every input bit of every kept leaf must have a
     kept source (else CUT_UNRESOLVED), every output bit of a kept leaf should have a load or a top port (else
     OUTPUT_UNREAD, listed), no constant reaches a non-strap input (CONST_INPUT, listed with the as-built constant).
     The strict port-bind check (tools/die_port_bind.py) is run separately on die_b2.v.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import sys
from pathlib import Path

QTAG = re.compile(r'(?:^|_)(SW|SE|NW|NE)(?=\d|_|$)')
INST_RE = re.compile(r'^\s+(\w+)\s*(?:#\((.*?)\))?\s+(\w+)\s*\(\n(.*?)\n\s*\);', re.S | re.M)
CONN_RE = re.compile(r'^\s*\.(\w+)\((.*)\),?\s*$')
WIRE_RE = re.compile(r'^\s*(input|output|wire)\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*;', re.M)


# ---------------------------------------------------------------------------------------------------------- expressions
def split_top(s, sep=','):
    out, d, cur = [], 0, []
    for ch in s:
        if ch in '{(':
            d += 1
        elif ch in '})':
            d -= 1
        if ch == sep and d == 0:
            out.append(''.join(cur)); cur = []
        else:
            cur.append(ch)
    out.append(''.join(cur))
    return [x.strip() for x in out if x.strip()]


def parse_expr(e, widths):
    """-> list of segments LSB-first: ('n', net, lo, hi) inclusive bit range, or ('c', width, value)."""
    e = e.strip()
    if not e:
        return []
    if e.startswith('{'):
        inner = e[1:-1].strip()
        m = re.match(r'^(\d+)\s*\{(.*)\}$', inner, re.S)
        if m:   # replication {N{...}}
            sub = parse_expr('{' + m.group(2) + '}', widths)
            return sub * int(m.group(1))
        parts = split_top(inner)
        segs = []
        for p in reversed(parts):   # MSB first in source -> LSB-first list
            segs += parse_expr(p, widths)
        return segs
    m = re.match(r"^(\d+)'([bdh])([0-9a-fA-FxXzZ_]+)$", e)
    if m:
        w = int(m.group(1)); base = {'b': 2, 'd': 10, 'h': 16}[m.group(2)]
        v = m.group(3).replace('_', '')
        if re.search('[xXzZ]', v):
            return [('c', w, 'x')]
        return [('c', w, int(v, base))]
    m = re.match(r'^(\w+)\s*\[(\d+)(?::(\d+))?\]$', e)
    if m:
        hi = int(m.group(2)); lo = int(m.group(3)) if m.group(3) is not None else hi
        return [('n', m.group(1), lo, hi)]
    m = re.match(r'^(\w+)$', e)
    if m:
        n = m.group(1)
        if n not in widths:
            raise KeyError(f'net {n} has no declaration')
        lo, hi = widths[n]
        return [('n', n, lo, hi)]
    raise ValueError(f'cannot parse expression {e[:120]}')


def seg_width(s):
    return s[1] if s[0] == 'c' else s[3] - s[2] + 1


def width_of(segs):
    return sum(seg_width(s) for s in segs)


def slice_segs(segs, lo, hi):
    """bits [lo, hi] (inclusive, LSB-first) of a segment list."""
    out, base = [], 0
    for s in segs:
        w = seg_width(s)
        a, b = max(lo, base), min(hi, base + w - 1)
        if a <= b:
            if s[0] == 'c':
                v = s[2] if s[2] == 'x' else (s[2] >> (a - base)) & ((1 << (b - a + 1)) - 1)
                out.append(('c', b - a + 1, v))
            else:
                out.append(('n', s[1], s[2] + a - base, s[2] + b - base))
        base += w
    return out


# -------------------------------------------------------------------------------------------------------------- netlist
class Die:
    def __init__(self, path, transport):
        txt = gzip.open(path, 'rt').read() if str(path).endswith('.gz') else Path(path).read_text()
        m = re.search(r'module\s+(\w+)\s*\((.*?)\);', txt, re.S)
        self.top = m.group(1)
        self.widths, self.dirs = {}, {}
        for w in WIRE_RE.finditer(txt):
            kind, hi, lo, n = w.group(1), w.group(2), w.group(3), w.group(4)
            self.widths[n] = (int(lo), int(hi)) if hi is not None else (0, 0)
            if kind in ('input', 'output'):
                self.dirs[n] = kind
        self.insts = {}
        for mm in INST_RE.finditer(txt[m.end():]):
            master, params, name, conns = mm.group(1), mm.group(2) or '', mm.group(3), mm.group(4)
            pc = {}
            for line in conns.split('\n'):
                c = CONN_RE.match(line)
                if c:
                    pc[c.group(1)] = c.group(2)
            self.insts[name] = dict(master=master, params=params, conns=pc)
        self.transport = transport
        self.driver = {}      # net -> (inst, port)  (by the GEN naming rule inst__port)
        for n in self.widths:
            if '__' in n and self.dirs.get(n) != 'input':
                i, p = n.rsplit('__', 1)
                if i in self.insts and p in self.insts[i]['conns']:
                    self.driver[n] = (i, p)
        self._tcache = {}
        self.memo = {}

    def trule(self, inst):
        m = self.insts[inst]['master']
        if m not in self._tcache:
            self._tcache[m] = None
            for r in self.transport:
                if re.fullmatch(r['module'], m):
                    self._tcache[m] = r
                    break
        return self._tcache[m]

    def is_transport(self, inst):
        return self.trule(inst) is not None

    def stages(self, inst):
        r = self.trule(inst)
        st = r['stages']
        if r.get('stages_param'):
            pm = re.search(r'\.' + r['stages_param'] + r'\((\d+)\)', self.insts[inst]['params'])
            if pm:
                st = int(pm.group(1))
        return st

    def resolve(self, segs, depth=0):
        """segments -> list of (seg, stages) where seg is a leaf-output / top-input net range or a constant."""
        out = []
        for s in segs:
            if s[0] == 'c':
                out.append((s, 0)); continue
            n, lo, hi = s[1], s[2], s[3]
            d = self.driver.get(n)
            if d is None or not self.is_transport(d[0]):
                out.append((s, 0)); continue
            inst, port = d
            r = self.trule(inst)
            src_port = r['map'].get(port)
            if src_port is None:
                raise ValueError(f'transport {inst}.{port} has no input map')
            key = (inst, src_port)
            if key not in self.memo:
                ex = parse_expr(self.insts[inst]['conns'][src_port], self.widths)
                self.memo[key] = ex
            ex = self.memo[key]
            nlo = self.widths[n][0]
            win = width_of(ex)
            if r.get('replicate') and win and (hi - nlo) >= win:
                # replicated fan-out copies (lh fN): out bit k = in bit k mod in-width
                sub = []
                for k in range(lo - nlo, hi - nlo + 1):
                    sub += slice_segs(ex, k % win, k % win)
            else:
                sub = slice_segs(ex, lo - nlo, hi - nlo)
            if width_of(sub) != hi - lo + 1:
                raise ValueError(f'transport {inst}.{port}[{hi}:{lo}] maps outside its input ({win} b)')
            st = self.stages(inst)
            for s2, st2 in self.resolve(sub, depth + 1):
                out.append((s2, st2 + st))
        # merge adjacent ranges of the same net with equal stages
        mg = []
        for s, st in out:
            if mg and s[0] == 'n' and mg[-1][0][0] == 'n' and mg[-1][0][1] == s[1] and mg[-1][1] == st \
                    and mg[-1][0][3] + 1 == s[2]:
                p = mg[-1][0]
                mg[-1] = (('n', p[1], p[2], s[3]), st)
            else:
                mg.append((s, st))
        return mg


def src_inst(die, net):
    d = die.driver.get(net)
    return d[0] if d else None


# ------------------------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--die', required=True)
    ap.add_argument('--asbuilt', required=True)
    ap.add_argument('--delta', required=True)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    ab = json.loads(Path(a.asbuilt).read_text())
    delta = json.loads(Path(a.delta).read_text())
    die = Die(a.die, ab['transport'])
    a.out.mkdir(parents=True, exist_ok=True)
    keepq = set(delta['keep']['quadrants'])
    keep_x, drop_x = set(delta['keep'].get('instances', [])), set(delta['keep'].get('drop_instances', []))
    leaves = [n for n in die.insts if not die.is_transport(n)]

    def kept(n):
        if n in drop_x:
            return False
        if n in keep_x:
            return True
        m = QTAG.search(n)
        return (m is None) or (m.group(1) in keepq)
    K = [n for n in leaves if kept(n)]
    Kset = set(K)
    remaster = delta.get('remaster', {})
    port_map = delta.get('port_map', {})      # inst -> port -> [[old_lo, old_hi, new_lo]] (kept slices; others dropped)
    reattach = delta.get('reattach', {})      # inst -> port -> [[lo, hi, src_inst, src_port, src_lo]]
    drop_ports = delta.get('drop_ports', {})  # inst -> [ports]
    rename_out = delta.get('rename_out', {})  # inst -> {old out port: new out port}
    rebuild = delta.get('rebuild', {})        # inst -> port -> [[src_inst, src_port, lo, hi] | ["const", w, v]] LSB-first
    out_width = delta.get('out_width', {})    # inst -> {out port: new width} (remastered masters whose outputs grow/shrink)
    add_ports = delta.get('add_ports', {})    # inst -> {port: "out" | "in"} ports the new master has and r18h5 lacked
    straps = [re.compile(x) for x in delta.get('strap_ports', [])]

    rep = collections.defaultdict(list)
    paths = []
    conns_out = {}
    loads = collections.defaultdict(lambda: collections.defaultdict(set))   # net -> bit -> readers (for open outputs)
    stats = collections.Counter()

    def is_strap(inst, port):
        return any(r.fullmatch(f'{inst}.{port}') for r in straps)

    for n in K:
        i = die.insts[n]
        rm = remaster.get(n, {})
        dp = set(drop_ports.get(n, []))
        new = {}
        for port, expr in i['conns'].items():
            if port in dp:
                continue
            net_self = f'{n}__{port}'
            if die.driver.get(net_self) == (n, port):      # output port of this instance
                op = rename_out.get(n, {}).get(port, port)
                if port in port_map.get(n, {}):
                    new[op] = ('out_map', port)
                else:
                    new[op] = ('out', net_self)
                continue
            segs = parse_expr(expr, die.widths) if expr else []
            res = die.resolve(segs)
            # input: build the bit list LSB-first
            flat = []
            for s, st in res:
                if s[0] == 'c':
                    flat.append((s, st))
                else:
                    flat.append((s, st))
            new[port] = ('in', flat)
        for port, kind in add_ports.get(n, {}).items():
            if kind == 'out':
                new[port] = ('out', f'{n}__{port}')
            else:
                new[port] = ('in', [])
        conns_out[n] = dict(master=rm.get('master', i['master']), params=rm.get('params', i['params']), ports=new)

    # second pass: port maps, reattach, classify sources
    def seg_src_kept(s):
        if s[0] == 'c':
            return 'const'
        si = src_inst(die, s[1])
        if si is None:
            return 'top' if die.dirs.get(s[1]) == 'input' else 'undriven'
        return 'kept' if si in Kset else 'dropped'

    out_lines = []
    used_top_in, used_nets = set(), set()
    for n in K:
        c = conns_out[n]
        pm = port_map.get(n, {})
        ra = reattach.get(n, {})
        final = {}
        for port, v in c['ports'].items():
            if v[0] == 'out':
                w0 = out_width.get(n, {}).get(port)
                if w0 is None:
                    w0 = die.widths[v[1]][1] - die.widths[v[1]][0] + 1
                final[port] = ('out', v[1], w0); continue
            if v[0] == 'out_map':
                # an output port whose width shrinks: the new net is n__port with the kept slices
                tot = sum(h - l + 1 for l, h, _ in pm[v[1]])
                final[port] = ('out', f'{n}__{port}', tot); continue
            flat = v[1]
            if port in rebuild.get(n, {}):
                flat = []
                for e in rebuild[n][port]:
                    if e[0] == 'const':
                        flat.append((('c', e[1], e[2]), 0))
                    else:
                        si, sp, lo, hi = e
                        flat.append((('n', f'{si}__{sp}', lo, hi), 'new'))
            segs = [s for s, _ in flat]
            sts = [st for _, st in flat]
            if port in pm:   # keep only the mapped old slices, placed at their new offsets
                tot = max(nl + h - l + 1 for l, h, nl in pm[port])
                newsegs = [None] * tot
                bits = []
                for s, st in flat:
                    for k in range(seg_width(s)):
                        bits.append((slice_segs([s], k, k)[0], st))
                for l, h, nl in pm[port]:
                    for k in range(h - l + 1):
                        newsegs[nl + k] = bits[l + k]
                if any(x is None for x in newsegs):
                    rep['PORT_MAP_GAP'].append(f'{n}.{port}')
                    newsegs = [x if x is not None else (('c', 1, 'x'), 0) for x in newsegs]
                flat = newsegs
            if port in ra:
                bits = []
                for s, st in flat:
                    for k in range(seg_width(s)):
                        bits.append((slice_segs([s], k, k)[0], st))
                for lo, hi, si, sp, slo in ra[port]:
                    for k in range(hi - lo + 1):
                        if lo + k >= len(bits):
                            bits.extend([(('c', 1, 'x'), 0)] * (lo + k + 1 - len(bits)))
                        bits[lo + k] = (('n', f'{si}__{sp}', slo + k, slo + k), 'new')
                flat = bits
            # classify
            for s, st in flat:
                cls = seg_src_kept(s) if not (s[0] == 'n' and st == 'new') else \
                    ('reattach' if s[1].rsplit('__', 1)[0] in Kset else 'dropped')
                w = seg_width(s)
                stats[cls] += w
                if cls == 'dropped':
                    rep['CUT_UNRESOLVED'].append(f'{n}.{port} <- {s[1]}[{s[3]}:{s[2]}] ({w} b)')
                elif cls == 'const' and not is_strap(n, port):
                    rep['CONST_INPUT'].append(f'{n}.{port} <- {w}\'{s[2]}')
                elif cls == 'undriven':
                    rep['UNDRIVEN'].append(f'{n}.{port} <- {s[1]}')
                if s[0] == 'n':
                    used_nets.add(s[1])
                    if die.dirs.get(s[1]) == 'input':
                        used_top_in.add(s[1])
                    for b in range(s[2], s[3] + 1):
                        loads[s[1]][b].add(n)
            final[port] = ('in', flat)
            paths.append(dict(inst=n, port=port, src=sorted({f'{src_inst(die, s[1]) or s[1]}' for s, _ in flat if s[0] == 'n'}),
                              stages=sorted({st for _, st in flat if isinstance(st, int)}),
                              new=any(st == 'new' for _, st in flat)))
        c['final'] = final

    # outputs without loads (kept leaves): reported
    top_out = [x for x, d in die.dirs.items() if d == 'output']
    top_out_kept = []
    for t in top_out:
        si = src_inst(die, t)
        if si in Kset:   # a die output driven by a kept leaf (transport faults are dropped with their transport)
            top_out_kept.append(t)
            for b in range(die.widths[t][0], die.widths[t][1] + 1):
                loads[t][b].add('TOP')
    for n in K:
        for port, v in conns_out[n]['final'].items():
            if v[0] != 'out':
                continue
            net, w = v[1], v[2]
            if net in top_out_kept:
                continue
            unread = [b for b in range(w) if not loads[net].get(b)]
            if unread:
                rep['OUTPUT_UNREAD'].append(f'{n}.{port} {len(unread)}/{w} b')
                stats['out_unread'] += len(unread)

    # emit Verilog
    def vexpr(flat):
        parts = []
        for s, _ in reversed(flat):
            if s[0] == 'c':
                parts.append(f"{s[1]}'b{'x' * s[1]}" if s[2] == 'x' else f"{s[1]}'d{s[2]}")
            else:
                lo0 = die.widths.get(s[1], (0, 0))[0]
                parts.append(f'{s[1]}[{s[3]}:{s[2]}]')
        # merge is cosmetic only; keep the plain concatenation
        return parts[0] if len(parts) == 1 else '{' + ', '.join(parts) + '}'

    ports_in = sorted(used_top_in)
    lines = ['// GENERATED by tools/hbm_b2/b2_top.py (HBM-BIND 2026-10-24): 8-SM B2 die = r18h5 NW + NE + die level,',
             '// transport collapsed (the plan binder inserts the B2 stations); see b2_top_report.json / b2_paths.json.',
             '`default_nettype none',
             f"module hbm_b2_die ({', '.join(ports_in + top_out_kept)});"]
    for p in ports_in:
        lo, hi = die.widths[p]; lines.append(f'  input wire [{hi}:{lo}] {p};')
    for p in top_out_kept:
        lo, hi = die.widths[p]; lines.append(f'  output wire [{hi}:{lo}] {p};')
    decl = set(ports_in) | set(top_out_kept)
    for n in K:
        for port, v in conns_out[n]['final'].items():
            if v[0] == 'out' and v[1] not in decl:
                lines.append(f'  wire [{v[2] - 1}:0] {v[1]};'); decl.add(v[1])
    for n in K:
        c = conns_out[n]
        ps = []
        for port, v in c['final'].items():
            ps.append(f'    .{port}({v[1] if v[0] == "out" else vexpr(v[1])})')
        par = f" #({c['params']})" if c['params'] else ''
        lines.append(f"  {c['master']}{par} {n} (\n" + ',\n'.join(ps) + '\n  );')
    lines.append('endmodule')
    lines.append('`default_nettype wire')
    (a.out / 'die_b2.v').write_text('\n'.join(lines) + '\n')
    (a.out / 'b2_paths.json').write_text(json.dumps(paths))
    summary = dict(schema='opentallas.hbm_b2.top_report.v1', kept_leaves=len(K), dropped_leaves=len(leaves) - len(K),
                   transport_collapsed=len(die.insts) - len(leaves), bits=dict(stats),
                   counts={k: len(v) for k, v in rep.items()},
                   remastered=sorted(remaster), top_in=len(ports_in), top_out=len(top_out_kept))
    (a.out / 'b2_top_report.json').write_text(json.dumps(dict(summary, detail=rep), indent=1))
    print(json.dumps(summary, indent=1))
    return 0 if not rep.get('CUT_UNRESOLVED') and not rep.get('UNDRIVEN') else 1


if __name__ == '__main__':
    sys.exit(main())
