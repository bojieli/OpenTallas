#!/usr/bin/env python3
"""Data-flow link model for the explorer: one links record per die revision, from the project's own geometry sources.

A link is one logical connection between two or more die blocks: its driver end (when the source says which end
drives), its sink ends, its width in bits, the physical hops it takes (through pipeline registers / stations when the
source places them), its register stages, its pin-to-pin length and the unrelated blocks its flight lines cross.
Nothing is invented: a field the source does not give is written as null and shown as unknown.

Sources (one sub-command each):
  s81       S81 construction plan (insts/buses) + its pins LEF (exact pin centroids via tools/hier_contract/pin_align).
            Pass-through registers (rly/stn/hstn/rstg/xstg) are collapsed: a chain driver -> relays -> sink becomes ONE
            link whose hops and stage count are the plan's own register instances.
  qwen      Qwen compute-die system geometry export (insts, buses, generated master pin rectangles).
  hbm       HBM system geometry: a whole-die rectangle candidate (boxes) + the current global graph (directed edges);
            pins are not published there, so ends are block centres and say so.
  explorer  A Chip Explorer die cache (explorer_geom.py export): block centres, undirected buses.

Output: <out>/<id>.links.json.gz (schema opentallas.dataflow.links.v1) and <out>/index.json (one row per record).

  python3 tools/fleet_viz/dataflow_links.py s81 --id s81_gen18c --plan P.json.gz --lef L.lef.gz --out DIR ...
"""
import argparse, bisect, collections, datetime, gzip, hashlib, json, math, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCHEMA = 'opentallas.dataflow.links.v1'
# chain_guide_cut_unique.py (S81 geometry stream): 260 um windows, 75% of two routing layers (80 nm, 64 nm pitch)
CUT = dict(window_um=260.0, tracks_per_window=260 * (.75 / .080 + .75 / .064), limit=0.60,
           source='tools/s81/chain_guide_cut_unique.py: capacity = 260*(0.75/0.080+0.75/0.064) tracks per 260 um '
                  'window; cut ratio = bits crossing / capacity; owner limit 0.60 (cut-analysis-before-rtl)')
CONTROL = {'clock_trunk', 'reset', 'reset_tree', 'clock', 'col_clock', 'col_reset', 'fclk', 'top_in', 'rst', 'clk'}
S81_REG = {'rly', 'stn', 'hstn', 'rstg', 'xstg'}
_PSL = re.compile(r'^(.*)\[(\d+):(\d+)\]$')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_json(p):
    raw = Path(p).read_bytes()
    return json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)


def git_head():
    try:
        return subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip() or None
    except OSError:
        return None


def r1(v):
    return None if v is None else round(v, 1)


class Builder:
    """Blocks (rectangles) + links; computes lengths, bit-um and bypass crossings."""

    def __init__(self):
        self.names, self.master, self.kind, self.group, self.reg = [], [], [], [], []
        self.x, self.y, self.w, self.h = [], [], [], []
        self.index = {}
        self.links = []

    def block(self, name, master, kind, group, x, y, w, h, reg=False):
        i = len(self.names)
        self.index[name] = i
        for col, v in ((self.names, name), (self.master, master), (self.kind, kind), (self.group, group), (self.reg, 1 if reg else 0),
                       (self.x, round(x, 3)), (self.y, round(y, 3)), (self.w, round(w, 3)), (self.h, round(h, 3))):
            col.append(v)
        return i

    def centre(self, i):
        return (self.x[i] + self.w[i] / 2, self.y[i] + self.h[i] / 2)

    def clip(self, i, q):
        """pins unknown: the point of block i's outline nearest to q (a lower bound on the wire, never the centre)"""
        x0, y0, x1, y1 = self.x[i], self.y[i], self.x[i] + self.w[i], self.y[i] + self.h[i]
        px, py = min(max(q[0], x0), x1), min(max(q[1], y0), y1)
        if x0 < px < x1 and y0 < py < y1:      # q inside the block: nearest face
            d = {(x0, py): px - x0, (x1, py): x1 - px, (px, y0): py - y0, (px, y1): y1 - py}
            px, py = min(d, key=d.get)
        return (px, py)

    def link(self, lid, cls, bits, ends, directed, hops=None, stages=None, note=None, extra=None):
        """ends: [(block, port, (x, y) | None, 'pin'|'box')]; hops: [(x1, y1, x2, y2, bits)] or None (direct)."""
        ends = [(b, p, pt if pt is not None else (self.centre(b) if b is not None and b >= 0 else None),
                 pk if pt is not None else ('box' if b is not None and b >= 0 else None)) for b, p, pt, pk in ends]
        self.links.append(dict(id=lid, cls=cls, bits=bits, ends=ends, directed=directed, hops=hops, stages=stages, note=note, extra=extra or {}))

    # ------------------------------------------------------------------ crossings
    def _grid(self, cell):
        g = collections.defaultdict(list)
        for i in range(len(self.names)):
            if self.reg[i] or self.w[i] <= 0 or self.h[i] <= 0:
                continue
            for gx in range(int(self.x[i] // cell), int((self.x[i] + self.w[i]) // cell) + 1):
                for gy in range(int(self.y[i] // cell), int((self.y[i] + self.h[i]) // cell) + 1):
                    g[(gx, gy)].append(i)
        return g

    def _crosses(self, i, a, b):
        """segment a-b intersects the interior of block i (Liang-Barsky, 0.5 um shrink so touching faces do not count)"""
        x0, y0, x1, y1 = self.x[i] + .5, self.y[i] + .5, self.x[i] + self.w[i] - .5, self.y[i] + self.h[i] - .5
        if x1 <= x0 or y1 <= y0:
            return False
        dx, dy = b[0] - a[0], b[1] - a[1]
        t0, t1 = 0.0, 1.0
        for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
            if p == 0:
                if q < 0:
                    return False
            else:
                t = q / p
                if p < 0:
                    if t > t1: return False
                    t0 = max(t0, t)
                else:
                    if t < t0: return False
                    t1 = min(t1, t)
        return t0 < t1

    def finish(self, cell=250.0):
        grid = self._grid(cell)
        out = []
        for L in self.links:
            ends = L['ends']
            if L['hops'] is None and any(e[3] == 'box' for e in ends) and all(e[2] is not None for e in ends) and len(ends) >= 2:
                drv = ends[0][2]; rest = [e[2] for e in ends[1:]]
                mean = (sum(p[0] for p in rest) / len(rest), sum(p[1] for p in rest) / len(rest))
                d0 = self.clip(ends[0][0], mean) if ends[0][3] == 'box' else drv
                ends = [(ends[0][0], ends[0][1], d0, ends[0][3])] + [
                    (b, p, self.clip(b, d0) if pk == 'box' else pt, pk) for b, p, pt, pk in ends[1:]]
            pts = [e[2] for e in ends]
            placed = [p is not None for p in pts]
            if L['hops'] is not None:
                segs = [((h[0], h[1]), (h[2], h[3]), h[4]) for h in L['hops']]
            elif all(placed) and len(pts) >= 2:
                segs = [(pts[0], p, L['bits'] or 0) for p in pts[1:]]
            else:
                segs = []
            own = {e[0] for e in ends if e[0] is not None and e[0] >= 0}
            groups = {self.group[b] for b in own if self.group[b]}
            crossed = set()
            endpts = [p for p in pts if p is not None]

            def contains(i):
                return any(self.x[i] <= q[0] <= self.x[i] + self.w[i] and self.y[i] <= q[1] <= self.y[i] + self.h[i] for q in endpts)
            for a, b, _ in segs:
                n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) // (cell / 2)) + 1)
                cand = set()
                for k in range(n + 1):
                    t = k / n
                    cand.update(grid.get((int((a[0] + (b[0] - a[0]) * t) // cell), int((a[1] + (b[1] - a[1]) * t) // cell)), ()))
                for i in cand:
                    if i in own or i in crossed or (self.group[i] and self.group[i] in groups):
                        continue
                    if self._crosses(i, a, b) and not contains(i):
                        crossed.add(i)
            hop_len = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b, _ in segs]
            bitum = sum(l * (bt or 0) for l, (_, _, bt) in zip(hop_len, segs)) if segs else None
            # path length to the farthest sink: direct = farthest end; relayed = longest driver->sink path over hops
            if L['hops'] is None:
                length = max(hop_len) if hop_len else None
            else:
                length = L.get('path_um')
            rec = dict(i=L['id'], c=L['cls'], b=L['bits'], d=1 if L['directed'] else 0,
                       e=[[e[0] if e[0] is not None else -1, e[1], r1(e[2][0]) if e[2] else None, r1(e[2][1]) if e[2] else None, e[3]] for e in ends],
                       s=L['stages'], L=r1(length), mh=r1(max(hop_len)) if hop_len else None, bu=round(bitum) if bitum is not None else None,
                       x=len(crossed), xb=sorted(crossed, key=lambda i: -self.w[i] * self.h[i])[:12])
            if L['hops'] is not None:
                rec['h'] = [[r1(h[0]), r1(h[1]), r1(h[2]), r1(h[3]), h[4]] for h in L['hops']]
            if L.get('note'):
                rec['n'] = L['note']
            rec.update({k: v for k, v in L['extra'].items() if v is not None})
            out.append(rec)
        blocks = dict(name=self.names, master=self.master, kind=self.kind, group=self.group, reg=self.reg,
                      x=self.x, y=self.y, w=self.w, h=self.h)
        return blocks, out


def cut_metrics(outline, links):
    """worst cut ratio: L-route (x then y) per hop/flight segment, each link counted once per 260 um window"""
    Wn, cap = CUT['window_um'], CUT['tracks_per_window']
    v, hz = collections.Counter(), collections.Counter()
    for l in links:
        if not l.get('b'): continue
        segs = l.get('h') or ([[l['e'][0][2], l['e'][0][3], e[2], e[3], l['b']] for e in l['e'][1:]] if l['e'] and l['e'][0][2] is not None else [])
        seen = set()
        for x1, y1, x2, y2, b in segs:
            if None in (x1, y1, x2, y2): continue
            b = b or l['b']; j = int(y1 // Wn)
            for k in range(int(min(x1, x2) // Wn) + 1, int(math.ceil(max(x1, x2) / Wn))):
                if ('v', k, j) not in seen: seen.add(('v', k, j)); v[(k, j)] += b
            i = int(x2 // Wn)
            for k in range(int(min(y1, y2) // Wn) + 1, int(math.ceil(max(y1, y2) / Wn))):
                if ('h', k, i) not in seen: seen.add(('h', k, i)); hz[(k, i)] += b
    vals = [x / cap for x in list(v.values()) + list(hz.values())]
    return (max(vals) if vals else 0.0), sum(1 for x in vals if x > CUT['limit'])


def metrics(meta, links):
    reach = meta.get('reach_um') or 500.0
    worst, over = cut_metrics(meta['outline'], links)
    tl = [l for l in links if l.get('t') is not None and l.get('L') is not None]
    return dict(sum_width_length_bit_um=round(sum((l['b'] or 0) * (l['L'] or 0) for l in links)),
                sum_bit_um_hops=round(sum(l['bu'] or 0 for l in links)),
                sum_traffic_length=round(sum(l['t'] * l['L'] for l in tl)) if tl else None, traffic_links=len(tl),
                over_reach_bits=sum(l['b'] or 0 for l in links if (l.get('mh') if l.get('mh') is not None else (l.get('L') or 0)) > reach),
                relays=sum(l['s'] or 0 for l in links if l.get('s') is not None) if meta.get('stages_explicit') else None,
                relay_bit_stages=sum((l['s'] or 0) * (l['b'] or 0) for l in links if l.get('s') is not None) if meta.get('stages_explicit') else None,
                needed_relay_bit_stages_lower_bound=sum((l['b'] or 0) * max(0, math.ceil((l['L'] or 0) / reach) - 1) for l in links),
                worst_cut=round(worst, 4), cut_windows_over_limit=over)


def write(out_dir, rid, meta, blocks, links, inputs, args):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    if getattr(args, 'candidate_of', None):
        meta['role'] = 'candidate'
        meta['candidate'] = dict(of=args.candidate_of, agent=args.candidate_agent, name=args.candidate_name or rid, note=args.candidate_note, log=args.candidate_log)
    placed = [l for l in links if l['L'] is not None]
    cov = dict(links=len(links), placed=len(placed), unplaced=len(links) - len(placed),
               width_known=sum(1 for l in links if l['b']), directed=sum(1 for l in links if l['d']),
               pin_ends=sum(1 for l in links for e in l['e'] if e[4] == 'pin'), box_ends=sum(1 for l in links for e in l['e'] if e[4] == 'box'),
               unplaced_ends=sum(1 for l in links for e in l['e'] if e[4] is None),
               stages_known=sum(1 for l in links if l['s'] is not None), bypass=sum(1 for l in links if l['x']),
               blocks=len(blocks['name']), bits_total=sum(l['b'] or 0 for l in links),
               bit_um_total=sum(l['bu'] or 0 for l in links))
    cov['metrics'] = metrics(meta, links)
    rec = dict(schema=SCHEMA, id=rid, **meta, cut=CUT, coverage=cov,
               provenance=dict(tool='tools/fleet_viz/dataflow_links.py', tool_sha256=sha(__file__), repo_head=git_head(),
                               generated=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
                               argv=sys.argv[1:], inputs=inputs),
               blocks=blocks, links=links)
    raw = json.dumps(rec, separators=(',', ':')).encode()
    (out_dir / (rid + '.links.json.gz')).write_bytes(gzip.compress(raw, 9, mtime=0))
    idx_p = out_dir / 'index.json'
    idx = json.loads(idx_p.read_text()) if idx_p.exists() else dict(schema='opentallas.dataflow.links_index.v1', records=[])
    row = dict(id=rid, file=rid + '.links.json.gz', label=meta['label'], design=meta['design'], token_designs=meta.get('token_designs', []),
               revision=meta['revision'], role=meta.get('role'), candidate=meta.get('candidate'), scope=meta.get('scope'), coverage=cov,
               inputs=[dict(path=i['path'], sha256=i['sha256']) for i in inputs], generated=rec['provenance']['generated'],
               bytes=len(raw))
    idx['records'] = [r for r in idx['records'] if r['id'] != rid] + [row]
    idx['records'].sort(key=lambda r: (r['design'], r['id']))
    idx_p.write_text(json.dumps(idx, indent=1) + '\n')
    print('%s: %d blocks, %d links (%d placed, %d bypass), %.1f MB raw' % (rid, cov['blocks'], cov['links'], cov['placed'], cov['bypass'], len(raw) / 1e6))


def meta_from(a, **kw):
    m = dict(label=a.label, design=a.design, token_designs=[t for t in (a.token_designs or '').split(',') if t],
             revision=a.revision, role=a.role, scope=kw.pop('scope', None), reach_um=a.reach, reach_source=a.reach_source)
    m.update(kw)
    return m


def collapse(B, data, reg, centroid, directed):
    """data: [(id, cls, bits, [(inst, port), ...])] with the driver first when `directed`; buses that share a
    pass-through register instance (reg) are one chain: hops = the buses, stages = registers on the longest path."""
    pin_centroid = centroid

    def centroid(n, p, bits):
        pt, pk = pin_centroid(n, p, bits)
        if pt is None and n in B.index:
            return B.centre(B.index[n]), 'box'
        return pt, pk
    # union buses through pass-through registers
    parent = list(range(len(data)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    via = collections.defaultdict(list)
    for k, b in enumerate(data):
        for n, _ in b[3]:
            if n in reg:
                via[n].append(k)
    for ks in via.values():
        for k in ks[1:]:
            ra, rb = find(ks[0]), find(k)
            if ra != rb: parent[rb] = ra
    groups = collections.defaultdict(list)
    for k in range(len(data)):
        groups[find(k)].append(k)
    for root, ks in groups.items():
        buses = [data[k] for k in ks]
        if len(buses) == 1 and not any(n in reg for n, _ in buses[0][3]):
            bid, cls, bits, ends = buses[0]
            E = []
            for n, p in ends:
                pt, pk = centroid(n, p, bits)
                E.append((B.index.get(n, -1) if n in B.index else None, p, pt, pk))
            B.link(bid, cls, bits, E, directed)
            continue
        # relayed group: hops = every bus, ends = non-register endpoints; stage count/path along driver->sink
        hops, adj = [], collections.defaultdict(list)
        drivers, sinks = [], []
        for bid, cls, bits, ends in buses:
            n0, p0 = ends[0]
            a0, k0 = centroid(n0, p0, bits)
            if n0 not in reg:
                drivers.append((n0, p0, bits))
            for n, p in ends[1:]:
                a1, k1 = centroid(n, p, bits)
                a0c = a0
                if a0 is not None and a1 is not None:
                    if k1 == 'box': a1 = B.clip(B.index[n], a0)
                    if k0 == 'box': a0c = B.clip(B.index[n0], a1)
                    if k1 == 'box': a1 = B.clip(B.index[n], a0c)
                if n not in reg:
                    sinks.append((n, p, bits))
                if not directed:
                    if n not in reg: drivers.append((n, p, bits))
                    if n0 not in reg: sinks.append((n0, p0, bits))
                l = abs(a1[0] - a0c[0]) + abs(a1[1] - a0c[1]) if a0c is not None and a1 is not None else None
                if l is not None:
                    hops.append((a0c[0], a0c[1], a1[0], a1[1], bits))
                adj[n0].append((n, l))
                if not directed:
                    adj[n].append((n0, l))
        # longest driver -> sink path (stages = registers passed) over the hop graph
        best_len, best_st = None, None
        for dn, _, _ in drivers:
            dist = {dn: (0.0, 0)}; q = collections.deque([dn])
            while q:
                u = q.popleft()
                for v, l in adj.get(u, ()):
                    if v in dist or l is None:
                        continue
                    dist[v] = (dist[u][0] + l, dist[u][1] + (1 if v in reg else 0)); q.append(v)
            for sn, _, _ in sinks:
                if sn in dist:
                    if best_len is None or dist[sn][0] > best_len:
                        best_len, best_st = dist[sn]
        main = max(buses, key=lambda b: b[2] or 0)
        E = []
        seen = set()
        for n, p, bits in drivers + sinks:
            if (n, p) in seen: continue
            seen.add((n, p))
            pt, pk = centroid(n, p, bits)
            E.append((B.index.get(n) if n in B.index else None, p, pt, pk))
        if len(E) < 2:
            continue
        nreg = len({n for b in buses for n, _ in b[3] if n in reg})
        name = re.sub(r'_(d|y)?\d+$', '', main[0]) if len(buses) > 1 else main[0]
        B.link(name + ('~%d' % root if name in ('',) else ''), main[1], max(b[2] or 0 for b in buses), E, directed and bool(drivers), hops=hops,
               stages=best_st if best_st is not None else nreg)
        B.links[-1]['path_um'] = best_len
        B.links[-1]['hop_buses'] = len(buses)
    # disambiguate repeated chain names
    cnt = collections.Counter(l['id'] for l in B.links); seen = collections.Counter()
    for l in B.links:
        if cnt[l['id']] > 1:
            seen[l['id']] += 1; l['id'] = '%s#%d' % (l['id'], seen[l['id']])


# ------------------------------------------------------------------------------------------------------------ S81
def cmd_s81(a):
    sys.path.insert(0, str(REPO / 'tools' / 'hier_contract'))
    import pin_align as PA
    plan = load_json(a.plan)
    lef = gzip.decompress(Path(a.lef).read_bytes()).decode() if str(a.lef).endswith('.gz') else Path(a.lef).read_text()
    pins = PA.read_pins([lef])
    B = Builder()
    inst = {}
    for r in plan['insts']:
        name, master, x, y, w, h, orient, kind = r[:8]
        region = r[8] if len(r) > 8 else None
        B.block(name, master, kind, region or None, x, y, w, h, reg=kind in S81_REG)
        inst[name] = (master, x, y, w, h, orient)
    aliases, overrides = plan.get('port_aliases', {}), plan.get('pins', {})

    class It:  # pin_align.place wants x, y, orient
        __slots__ = ('x', 'y', 'orient')

    cache = {}

    def centroid(n, port, bits):
        key = (n, port)
        if key in cache:
            return cache[key]
        res = (None, None)
        if n in inst:
            master, x, y, w, h, orient = inst[n]
            rec = pins.get(master)
            if rec:
                W, H, pp = rec
                names = overrides.get(n + '|' + port)
                if names is None:
                    m = _PSL.match(port); base = m.group(1) if m else port; lo = int(m.group(2)) if m else 0
                    al = aliases.get(master, {}).get(base)
                    names = al[lo:lo + bits] if al is not None else [f'{base}[{lo + i}]' for i in range(max(1, bits or 1))]
                    if bits == 1 and names and names[0] not in pp and base in pp:
                        names = [base]
                it = It(); it.x, it.y, it.orient = x, y, orient
                ps = [PA.place(it, W, H, pp[k]) for k in names if k in pp]
                if ps:
                    res = ((sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)), 'pin')
        cache[key] = res
        return res

    reg = {n for n, v in inst.items() if B.kind[B.index[n]] in S81_REG}
    data = [b for b in plan['buses'] if b[1] not in CONTROL and len(b[3]) >= 2]
    collapse(B, data, reg, centroid, True)
    blocks, links = B.finish()
    inputs = [dict(path=str(a.plan), sha256=sha(a.plan), role='construction plan (insts/buses)', commit=a.source_commit),
              dict(path=str(a.lef), sha256=sha(a.lef), role='pins LEF (exact pin rectangles)', commit=a.source_commit)]
    for extra in a.extra or []:
        inputs.append(dict(path=extra, sha256=sha(extra), role='supporting record'))
    write(a.out, a.id, meta_from(a, outline=plan['die'], scope=plan.get('scope'),
                                  relay_reach_um=215.0, stages_explicit=True, relay_reach_source='hub_station_reach_um (tools/s81/die_link_repin_search.py CC_REACH)',
                                  registers='rly/stn/hstn/rstg/xstg collapsed into their chains (hops and stages are the plan register instances)',
                                  direction='ends[0] drives (plan convention: generator writes the driver first; group_placement_opt.Model)',
                                  pins='exact LEF pin centroids per port (pin_align.read_pins/place, plan port_aliases and pin overrides)'),
          blocks, links, inputs, a)


# ------------------------------------------------------------------------------------------------------------ Qwen
ORI_Q = {'R0': 'N', 'N': 'N', 'MY': 'FN', 'FN': 'FN', 'MX': 'FS', 'FS': 'FS', 'R180': 'S', 'S': 'S'}


def cmd_qwen(a):
    g = load_json(a.geometry)
    B = Builder()
    # register-like masters (explicit relays) are not functional blocks for the bypass count
    for r in g['insts']:
        n = r['n']; grp = re.sub(r'(_\d+)+$', '', n)
        B.block(n, r['m'], r['m'], grp, r['x'], r['y'], r['w'], r['h'], reg=bool(re.match(r'qfd_rly', r['m'])))
    orient = {r['n']: r.get('o', 'R0') for r in g['insts']}
    masters = g['masters']
    pin_by_master = {}
    for m, v in masters.items():
        d = collections.defaultdict(list)
        for p in v.get('pins', []):
            nm = p['name']; base = nm.split('[')[0]
            rx = p['rect']; d[base].append(((rx[0] + rx[2]) / 2, (rx[1] + rx[3]) / 2, nm))
        pin_by_master[m] = d
    inst = {r['n']: r for r in g['insts']}

    def centroid(n, port):
        r = inst.get(n)
        if not r: return None, None
        m = _PSL.match(port); base = m.group(1) if m else port
        ps = pin_by_master.get(r['m'], {}).get(base)
        if not ps: return None, None
        if m:
            lo, hi = sorted((int(m.group(2)), int(m.group(3))))
            sel = [p for p in ps if '[' in p[2] and lo <= int(p[2].split('[')[1].rstrip(']')) <= hi] or ps
        else:
            sel = ps
        W, H = masters[r['m']]['w'], masters[r['m']]['h']
        cx, cy = sum(p[0] for p in sel) / len(sel), sum(p[1] for p in sel) / len(sel)
        o = ORI_Q.get(orient.get(n, 'R0'), 'N')
        if o == 'S': cx, cy = W - cx, H - cy
        elif o == 'FN': cx = W - cx
        elif o == 'FS': cy = H - cy
        return (r['x'] + cx, r['y'] + cy), 'pin'

    for b in g['buses']:
        if b['c'] in CONTROL or len(b['e']) < 2:
            continue
        E = []
        for n, p in b['e']:
            pt, pk = centroid(n, p)
            E.append((B.index.get(n), p, pt, pk))
        B.link(b['b'], b['c'], b['n'], E, False)
    blocks, links = B.finish()
    inputs = [dict(path=a.geometry_path or str(a.geometry), sha256=sha(a.geometry), role='current generated system geometry + master pins', commit=a.source_commit)]
    write(a.out, a.id, meta_from(a, outline=[g['die']['w'], g['die']['h']], scope=g.get('scope'),
                                  registers='relays are implicit in the wire model of this export: stage counts unknown', stages_explicit=False,
                                  direction='unknown (the export lists ends without a driver flag)',
                                  pins='generated master pin rectangles, centroid per port, instance orientation applied',
                                  source_commit=g.get('source_commit')),
          blocks, links, inputs, a)


# ------------------------------------------------------------------------------------------------------------ HBM
def cmd_hbm(a):
    boxes = load_json(a.boxes); graph = load_json(a.graph)
    B = Builder()
    for n, v in boxes['boxes'].items():
        B.block(n, v.get('role'), v.get('role'), n, v['x'], v['y'], v['w'], v['h'])
    nodes = graph['nodes']

    def place(k, depth=0):
        if k in B.index: return B.index[k]
        v = nodes.get(k) or {}; geo = v.get('geometry') or {}
        if not isinstance(geo, dict) or depth > 3: return None
        w, h = (geo.get('outline_um') or [0, 0])[:2]
        xy = geo.get('absolute_xy_um') or geo.get('xy_um')
        if xy is None and geo.get('coordinate_frame') and geo.get('local_xy_um') is not None:
            f = place(geo['coordinate_frame'], depth + 1)
            if f is not None and (geo.get('orientation') in (None, 'R0')):
                xy = [B.x[f] + geo['local_xy_um'][0], B.y[f] + geo['local_xy_um'][1]]
        if xy is None or not w or not h: return None
        grp = k.split('/')[0]
        return B.block(k, v.get('master'), v.get('role') or 'node', grp, xy[0], xy[1], w, h)
    for e in graph['edges']:
        s, t = e['source'], e['sink']
        bs, bt = place(s[0]), place(t[0])
        note = e.get('binding')
        if e.get('bytes_per_row'): note = (note or '') + '; %s bytes/row' % e['bytes_per_row']
        B.link(e['name'], e.get('clock') or e.get('binding') or 'edge', e.get('bits'),
               [(bs, s[0] + '.' + s[1], None, None), (bt, t[0] + '.' + t[1], None, None)], True, note=note)
    # ends that do not place keep their names
    for L in B.links:
        L['ends'] = [(b, p, pt, pk) for b, p, pt, pk in L['ends']]
    blocks, links = B.finish()
    inputs = [dict(path=a.boxes_path or str(a.boxes), sha256=sha(a.boxes), role='whole-die rectangle candidate (boxes)', commit=a.source_commit),
              dict(path=a.graph_path or str(a.graph), sha256=sha(a.graph), role='current global graph (directed edges, bits, frames)', commit=a.source_commit)]
    write(a.out, a.id, meta_from(a, outline=boxes['die_outline_um'], scope='%s; adoption_allowed=%s; graph complete=%s' % (boxes.get('name'), boxes.get('adoption_allowed'), graph.get('complete')),
                                  registers='register stations not in this graph: stage counts unknown', stages_explicit=False,
                                  direction='source -> sink as declared by the global graph',
                                  pins='not published for this candidate: ends are the block outline points nearest the peer (box), a lower bound; unplaced ends kept by name'),
          blocks, links, inputs, a)


# ------------------------------------------------------------------------------------------------------------ explorer cache
EXPLORER_REG = {'relay', 'rly', 'stn', 'hstn', 'rstg', 'xstg', 'waypoint'}


def cmd_explorer(a):
    g = load_json(a.geom)
    I = g['inst']; masters = g['masters']; kinds = g.get('kinds') or []; regions = g.get('regions_names') or []
    n = len(I['name'])
    col = lambda k: I.get(k) or [None] * n
    B = Builder()
    for i, nm in enumerate(I['name']):
        mi, k, rg = col('m')[i], col('k')[i], col('r')[i]
        m = masters[mi]['name'] if isinstance(mi, int) and mi < len(masters) else None
        k = kinds[k] if isinstance(k, int) and k < len(kinds) else k
        rg = regions[rg] if isinstance(rg, int) and 0 <= rg < len(regions) else rg
        grp = re.sub(r'(_\d+)+$', '', nm) if rg in (None, 'corridor', 'channel', 'strip') else rg
        B.block(nm, m, k, grp, I['x'][i], I['y'][i], I['w'][i], I['h'][i], reg=k in EXPLORER_REG)
    classes = g.get('bus_classes') or []
    data, omitted = [], {}
    for j, bus in enumerate(g.get('buses') or []):
        cls, bits, ids = bus[:3]
        cls = classes[cls] if isinstance(cls, int) and cls < len(classes) else str(cls)
        if cls in CONTROL: continue
        ends = [(I['name'][i], None) for i in ids if isinstance(i, int) and 0 <= i < n]
        if len(ends) < 2: continue
        om = sum(1 for i in ids if isinstance(i, int) and i < 0)
        if om: omitted['bus-%d' % j] = om
        data.append(('bus-%d' % j, cls, bits if isinstance(bits, int) and bits > 0 else None, ends))
    reg = {B.names[i] for i in range(len(B.names)) if B.reg[i]}
    collapse(B, data, reg, lambda nm, p, bits: (None, None), False)
    for L in B.links:
        if L['id'] in omitted: L['note'] = '%d broadcast endpoints omitted by the cache' % omitted[L['id']]
    blocks, links = B.finish()
    inputs = [dict(path=a.geom_path or str(a.geom), sha256=sha(a.geom), role='Chip Explorer die cache (explorer_geom.py)', commit=g.get('commit'))]
    write(a.out, a.id, meta_from(a, outline=[g['W'], g['H']], scope='explorer recipe export %s (%s)' % (g.get('key'), g.get('recipe')),
                                  registers='relay/station instances of the recipe collapsed into their chains (stages = registers passed)', stages_explicit=True,
                                  direction='unknown (cache keeps instance indices only)',
                                  pins='not in the cache: ends are the block outline points nearest the peer (box); lengths are lower bounds'),
          blocks, links, inputs, a)


def cmd_import(a):
    """a record written directly by another tool (e.g. a GLOBAL-FP candidate): validated, re-measured, indexed"""
    rec = load_json(a.record)
    assert rec.get('schema') == SCHEMA, 'schema must be ' + SCHEMA
    B = rec['blocks']; n = len(B['name'])
    for k in ('name', 'master', 'kind', 'group', 'reg', 'x', 'y', 'w', 'h'):
        assert len(B[k]) == n, 'blocks.%s length' % k
    for l in rec['links']:
        for e in l['e']:
            assert -1 <= e[0] < n, 'link %s end block index' % l.get('i')
    for k in ('label', 'design', 'revision', 'outline'):
        assert k in rec, 'missing ' + k
    meta = {k: v for k, v in rec.items() if k not in ('schema', 'id', 'blocks', 'links', 'coverage', 'provenance', 'cut')}
    meta.setdefault('reach_um', 500.0)
    # re-measure every link on the record's own geometry (length, bit-um, crossings): one metric code path for all
    Bd = Builder()
    for k in range(n):
        Bd.block(B['name'][k], B['master'][k], B['kind'][k], B['group'][k], B['x'][k], B['y'][k], B['w'][k], B['h'][k], reg=bool(B['reg'][k]))
    for l in rec['links']:
        ends = [(e[0] if e[0] >= 0 else None, e[1], (e[2], e[3]) if e[2] is not None else None, e[4] if e[2] is not None else None) for e in l['e']]
        hops = [tuple(h) for h in l['h']] if l.get('h') else None
        Bd.link(l['i'], l.get('c'), l.get('b'), ends, bool(l.get('d')), hops=hops, stages=l.get('s'), note=l.get('n'),
                extra=dict(t=l.get('t'), cr=l.get('cr'), lat=l.get('lat')))
        if hops:
            Bd.links[-1]['path_um'] = l.get('L') if l.get('L') is not None else sum(abs(h[2] - h[0]) + abs(h[3] - h[1]) for h in hops)
    blocks, links = Bd.finish()
    inputs = (rec.get('provenance') or {}).get('inputs') or []
    inputs = inputs + [dict(path=str(a.record), sha256=sha(a.record), role='imported record')]
    write(a.out, a.id or rec['id'], meta, blocks, links, inputs, a)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    def common(p):
        p.add_argument('--id', required=True); p.add_argument('--out', required=True)
        p.add_argument('--label', required=True); p.add_argument('--design', required=True)
        p.add_argument('--token-designs', default='', help='token-explorer designs this die serves (comma list)')
        p.add_argument('--revision', required=True); p.add_argument('--role', default='canonical')
        p.add_argument('--reach', type=float, default=500.0); p.add_argument('--reach-source', default='')
        p.add_argument('--source-commit', default=None)
        p.add_argument('--candidate-of', default=None, help='base record id: marks this record a floorplan candidate of it')
        p.add_argument('--candidate-agent', default=None); p.add_argument('--candidate-name', default=None)
        p.add_argument('--candidate-note', default=None); p.add_argument('--candidate-log', default=None)
    p = sub.add_parser('s81'); common(p); p.add_argument('--plan', required=True); p.add_argument('--lef', required=True)
    p.add_argument('--extra', nargs='*')
    p = sub.add_parser('qwen'); common(p); p.add_argument('--geometry', required=True); p.add_argument('--geometry-path')
    p = sub.add_parser('hbm'); common(p); p.add_argument('--boxes', required=True); p.add_argument('--graph', required=True)
    p.add_argument('--boxes-path'); p.add_argument('--graph-path')
    p = sub.add_parser('explorer'); common(p); p.add_argument('--geom', required=True); p.add_argument('--geom-path')
    p = sub.add_parser('import', help='validate + measure + index a record written directly (schema above)')
    p.add_argument('--record', required=True); p.add_argument('--out', required=True); p.add_argument('--id')
    for k in ('candidate-of', 'candidate-agent', 'candidate-name', 'candidate-note', 'candidate-log'): p.add_argument('--' + k, default=None)
    a = ap.parse_args()
    dict(s81=cmd_s81, qwen=cmd_qwen, hbm=cmd_hbm, explorer=cmd_explorer)[a.cmd](a) if a.cmd != 'import' else cmd_import(a)


if __name__ == '__main__':
    main()
