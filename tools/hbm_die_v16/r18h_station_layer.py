#!/usr/bin/env python3
"""HBMc/CHAIN 10-22 r18h (STEWARD-HBMc reach-check decision): contract-level station layer for the r18g plan-level
reach misses (d4g_reach_check cause=not_inserted: the planned positions are already over reach), applied to the PRE-FOREST
contract (S5X contract_pre.json) so the S7 GEN places the new stations and the S8 reset forest covers them.

    r18h_station_layer.py IN_contract.json OUT_contract.json --reach-all all_xy.json --manifest case_b/manifest.json
                          [--sfu-r 30] [--phy-rowv-direct] --report R.json

Parts (each listed per group in the report, with its cycle delta for STEWARD-TOK / TOKEN2):
  B1  --sfu-r R: every SFU LG chain sfr_<q><k>_{f,b} extended to R stages (all 32 chains, equal R; the H-SU rule) and every
      sfucore_<q> LG_PATH = R + 1 (one parameter set for all four cores).  New stages copy the chain's own master; the
      GEN places relay chains fresh on the core -> leaf path every run (prior-place skips hbfd_rly), evenly spaced.
  A   --phy-rowv-direct: phy_<q>.row_v[b] driven directly by its controller ctl_<q>_pNN.row_v (age 0, as row_op /
      row_bank / row_row / col_*), the relay branch that served only the PHY is removed; the sfault branch is kept
      unchanged.  Off by default (binding waits for the TOKEN2 directed check).
  S   stations: every remaining not_inserted bus gets k = ceil(span / reach) - 1 plain registered stations
      (hbfd_rly_<W>_<flow>, ck / rs on the edge's domain root, the S8 forest re-homes the reset) homed evenly on its
      measured pin-to-pin path ('home (x, y) um', bounded GEN placement).  Equal age is kept per relay ROW (rfNNNN):
        entry   buses into a row: every entry of the row gets the row's max entry need
        exit    buses out of a row: every exit of the row gets the same total (needed stations on the hop, the rest
                as pads at the driver end), so all sinks of the row move by the same number of edges
        load    rows (and direct buses) that feed one multi-driver load port are joined (union-find) and padded to the
                component's shift, so a word assembled from several rows keeps one age
      Excluded and reported: SFU LG chains (B1), PHY row_v (A), xq bd -> eg bq_d (cluster-internal word: placement fix).
"""
import argparse, collections, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'hbm_die_v15'))
import full_die_v16 as F  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_lockstep as CL  # noqa: E402

ROW = re.compile(r'^(rf\d+)_')
SRC = 'rtl/hbm_accel/die_glue/hbfd_rly_masters.sv'
DEPS = ['rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']
SRC_TW = 'rtl/hbm_accel/die_glue/hbfd_exact_tail_classes.sv'
DEPS_TW = ['rtl/hbm_accel/die_glue/hbfd_rly_masters.sv', 'rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']
REGION = 'r18h_stations'


def lef_size(master):
    w, d = master.split('_')[2], master.split('_')[3]
    for f in (ROOT / 'physical/ref_tile').glob(f'hbfd_rly_{w}_{d.lower()}/views/{master}/{master}.lef'):
        m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', f.read_text())
        return float(m.group(1)), float(m.group(2))
    raise SystemExit(f'no LEF for {master}')


def flow(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) >= abs(dy):
        return 'WE' if dx >= 0 else 'EW'
    return 'SN' if dy >= 0 else 'NS'


class Layer:
    def __init__(self, c):
        self.c = c; self.I = c['instances']; self.rtl = F.Rtl(); self.n = 0; self.tiles = 0
        self.sizes = {}; self.ports = {}

    def size(self, m):
        if m not in self.sizes:
            self.sizes[m] = lef_size(m)
        return self.sizes[m]

    def add_inst(self, name, master, note, domain, source=SRC, deps=DEPS, params=None):
        assert name not in self.I, name
        params = params or {}
        pk = (master, source, json.dumps(params, sort_keys=True))
        if pk not in self.ports:
            self.ports[pk] = self.rtl.ports(master, source, params)
        self.I[name] = dict(master=master, source=source, params=params, slot=None, owner='HBMc/CHAIN r18h', note=note,
                            rtl_deps=list(deps), region=REGION, ports=json.loads(json.dumps(self.ports[pk])))
        self.c['masters'][master] = self.c['masters'].get(master, 0) + 1
        for kind, p in (('clock', 'ck'), ('reset', 'rs')):
            self.c['clock_resets'].append(dict(instance=name, port=p, bits=1, domain=domain, kind=kind,
                                               source=['hb_ckgen', F.DOM[domain][0 if kind == 'clock' else 1]],
                                               note='r18h station layer'))
        self.tiles += 1

    def edges_from_bits(self, bits, dst, dport, dlo, clock, basis):
        """bits: list of (inst, port, bit) driving dst.dport[dlo + j]; emits contiguous-run edges."""
        out = []; j = 0
        while j < len(bits):
            si, sp, sb = bits[j]; k = j
            while k + 1 < len(bits) and bits[k + 1] == (si, sp, sb + (k + 1 - j)):
                k += 1
            n = k - j + 1
            self.n += 1
            out.append(dict(name=f'r18h_e{self.n}', bits=n, source=[si, sp, sb, sb + n], sink=[dst, dport, dlo + j, dlo + j + n],
                            clock=clock, ready_or_credit=False, allowed_exception=None, basis=basis, region=REGION))
            j = k + 1
        return out

    def insert(self, gid, sinks, k, path, clock, label, pads_at_driver=0):
        """sinks: [(src_bit (i,p,b), dst_bit (i,p,b))]; k stations (the first pads_at_driver of them at path[0], the rest
        evenly on path[0] -> path[1]).  Returns new edges (old ones are removed by the caller)."""
        n = len(sinks); fl = flow(*path)
        # exact-width tiles (no spare bits -> no new unread bits): full hbfd_rly_624_<flow> tiles, the remainder on the
        # run's exact tail class hbfd_rly_{48|624}_<flow>_tw #(TW) (hbfd_exact_tail_classes.sv, as the relay layer's tails)
        tiles = []; lo = 0
        while n - lo > 624:
            tiles.append((f'hbfd_rly_624_{fl}', SRC, DEPS, {}, lo, lo + 624)); lo += 624
        r = n - lo
        base = 48 if r <= 48 else 624
        tiles.append((f'hbfd_rly_{base}_{fl}_tw', SRC_TW, DEPS_TW, {'TW': r}, lo, n))
        ntile = len(tiles)
        cur = [s for s, _ in sinks]      # current driver of each bus bit
        E = []
        moving = k - pads_at_driver
        for j in range(k):
            if j < pads_at_driver:
                cx, cy = path[0]
            else:
                f = (j - pads_at_driver + 1) / (moving + 1)
                cx = path[0][0] + (path[1][0] - path[0][0]) * f; cy = path[0][1] + (path[1][1] - path[0][1]) * f
            nxt = []
            for t, (master, src_, deps_, params_, lo, hi) in enumerate(tiles):
                name = f'rh{gid:04d}_s{j:02d}_t{t}'
                tw, th = self.size(re.sub(r'_tw$', '', master))
                x0 = max(0.0, cx - tw / 2 + (t - (ntile - 1) / 2) * tw); y0 = max(0.0, cy - th / 2)
                self.add_inst(name, master, f'r18h station {j + 1}/{k} ({label}); tile {t}/{ntile}; home ({x0:.3f}, {y0:.3f}) um',
                              clock, source=src_, deps=deps_, params=dict(params_))
                assert self.I[name]['ports']['i']['bits'] == hi - lo, (name, master, params_)
                E += self.edges_from_bits(cur[lo:hi], name, 'i', 0, clock, f'r18h station {label}')
                nxt += [(name, 'o', b) for b in range(hi - lo)]
            cur = nxt
        # last stage -> loads
        by = collections.defaultdict(list)
        for (s, d), c_ in zip(sinks, cur):
            by[(d[0], d[1])].append((d[2], c_))
        for (di, dp), lst in by.items():
            lst.sort()
            # contiguous dst runs
            run = []
            for b, c_ in lst:
                if run and b != run[-1][0] + 1:
                    E += self.edges_from_bits([x[1] for x in run], di, dp, run[0][0], clock, f'r18h station {label}'); run = []
                run.append((b, c_))
            if run:
                E += self.edges_from_bits([x[1] for x in run], di, dp, run[0][0], clock, f'r18h station {label}')
        return E


def bus_bits(edges):
    out = []
    for e in edges:
        si, sp, slo, shi = e['source']; di, dp, dlo, dhi = e['sink']
        out += [((si, sp, slo + j), (di, dp, dlo + j)) for j in range(shi - slo)]
    return out


def sfu_extend(c, L, R, rep):
    I = c['instances']; E = c['edges']
    rx = re.compile(r'^(sfr_(?:SW|SE|NW|NE)[0-3]_[fb])(\d{2})$')
    chains = collections.defaultdict(list)
    for n in I:
        m = rx.match(n)
        if m:
            chains[m.group(1)].append(int(m.group(2)))
    assert len(chains) == 32, len(chains)
    r0 = {len(v) for v in chains.values()}
    assert r0 == {max(v) + 1 for v in chains.values()} and len(r0) == 1, r0
    r0 = r0.pop()
    assert R >= r0, (R, r0)
    new_edges = []
    drop = set()
    for g, idx in sorted(chains.items()):
        last = f'{g}{r0 - 1:02d}'; proto = I[f'{g}00']
        tail = [e for e in E if e['source'][0] == last]
        assert tail and all(e['source'][1] == 'o' for e in tail), g
        dom = next(x['domain'] for x in c['clock_resets'] if x['instance'] == last and x['kind'] == 'clock')
        width = I[last]['ports']['o']['bits']
        prev = last
        for s in range(r0, R):
            n = f'{g}{s:02d}'
            I[n] = json.loads(json.dumps({k: v for k, v in proto.items()}))
            I[n]['slot'] = None
            I[n]['note'] = f'r18h B1 SFU LG relay stage {s} of R{R} (LG_PATH {R + 1}); same master as {g}00'
            c['masters'][proto['master']] = c['masters'].get(proto['master'], 0) + 1
            for kind, p in (('clock', 'ck'), ('reset', 'rs')):
                old = next(x for x in c['clock_resets'] if x['instance'] == last and x['port'] == p)
                c['clock_resets'].append(dict(old, instance=n))
            new_edges.append(dict(name=f'r18h_{prev}_{n}', bits=width, source=[prev, 'o', 0, width], sink=[n, 'i', 0, width],
                                  clock=dom, ready_or_credit=False, allowed_exception=None,
                                  basis=f'r18h B1 SFU LG chain R{R} (registered stage, compiler LG_PATH {R + 1})', region='su_sfu'))
            prev = n
        for e in tail:
            e['source'] = [prev] + e['source'][1:]
    E += new_edges
    for q in ('SW', 'SE', 'NW', 'NE'):
        I[f'sfucore_{q}']['params']['LG_PATH'] = R + 1
        I[f'sfucore_{q}']['note'] = (I[f'sfucore_{q}'].get('note') or '') + f' | r18h B1: LG_PATH {r0 + 1} -> {R + 1} (R{R} chains)'
    rep['B1'] = dict(chains=len(chains), r_from=r0, r_to=R, lg_path_from=r0 + 1, lg_path_to=R + 1, added_stages=len(chains) * (R - r0),
                     cycle_delta=f'+{R - r0} edges each way per SFU LG access (+{2 * (R - r0)} per VM round trip; bridge READ_RETURN/'
                                 f'WRITE_RETURN + {2 * (R - r0)})')


def phy_rowv_direct(c, rep):
    """phy_<q>.row_v bit <- its controller's row_v; remove the relay stations that served only that bit."""
    I = c['instances']; E = c['edges']
    drv = {}
    for e in E:
        si, sp, slo, shi = e['source']; di, dp, dlo, dhi = e['sink']
        for j in range(shi - slo):
            drv[(di, dp, dlo + j)] = (si, sp, slo + j)
    cons = collections.defaultdict(set)
    for e in E:
        cons[e['source'][0]].add(e['sink'][0])
    rewired, removed = [], set()
    for n, v in I.items():
        if not n.startswith('phy_') or 'row_v' not in v['ports']:
            continue
        for b in range(v['ports']['row_v']['bits']):
            path = []; s = drv.get((n, 'row_v', b))
            while s and ROW.match(s[0]):
                path.append(s[0]); s = drv.get((s[0], 'i', s[2]))
            if not s or not re.match(r'ctl_(SW|SE|NW|NE)_p\d\d$', s[0]) or s[1] != 'row_v':
                raise SystemExit(f'A: {n}.row_v[{b}] root {s} is not a controller row_v')
            rewired.append((n, b, s, len(path)))
            # stations serving only this PHY branch: walk from the PHY up while the station feeds only the previous one
            prev = n
            for st in path:
                if not cons[st] <= {prev}:
                    break
                removed.add(st); prev = st
    keep = []
    for e in E:
        if e['source'][0] in removed or e['sink'][0] in removed:
            continue
        if e['sink'][0].startswith('phy_') and e['sink'][1] == 'row_v':
            continue
        keep.append(e)
    for n, b, s, _ in rewired:
        keep.append(dict(name=f'r18h_rowv_{n}_{b}', bits=1, source=[s[0], s[1], s[2], s[2] + 1], sink=[n, 'row_v', b, b + 1],
                         clock='hbm', ready_or_credit=False, allowed_exception=None,
                         basis='r18h A: PHY row_v direct from its controller (age 0, as row_op/row_bank/row_row/col_*)', region='phy'))
    c['edges'] = keep
    for st in removed:
        m = I[st]['master']; c['masters'][m] -= 1
        if not c['masters'][m]:
            del c['masters'][m]
        del I[st]
    c['clock_resets'] = [x for x in c['clock_resets'] if x['instance'] not in removed]
    depths = collections.Counter(d for *_, d in rewired)
    rep['A'] = dict(bits=len(rewired), removed_stations=len(removed), old_depths=dict(depths),
                    cycle_delta='row_v at the PHY: -depth edges (old relay depth) -> same edge as row_op/row_bank/row_row')


def stations(c, L, fails, reach, rep):
    E = c['edges']; I = c['instances']
    by_key = collections.defaultdict(list)
    for e in E:
        by_key[(e['source'][0], e['source'][1], e['sink'][0], e['sink'][1])].append(e)
    excl = collections.Counter(); todo = []
    for x in fails:
        if x.get('cause') != 'not_inserted' or x['cls'] == 'reset':
            continue
        d, l = x['bus'].split(' -> ')
        di, dp = d.rsplit('.', 1); li, lp = l.rsplit('.', 1)
        if re.match(r'(sfr_|sfu)', di) or re.match(r'(sfr_|sfu)', li):
            excl['B1_sfu_lg'] += 1; continue
        if li.startswith('phy_'):
            excl['A_phy_rowv'] += 1; continue
        if dp == 'bq_d' and li.startswith('xq_'):
            excl['xq_bq_d_placement'] += 1; continue
        if x['cls'] == 'fwd':
            excl['fwd_half_cycle_lane'] += 1; continue
        if (di, dp, li, lp) not in by_key:
            raise SystemExit(f'S: bus {x["bus"]} not in the contract')
        todo.append(dict(key=(di, dp, li, lp), k=math.ceil(x['span_um'] / reach) - 1, dxy=x['dxy'], lxy=x['lxy'], span=x['span_um']))
    # anchors: entry (into row), exit (out of row), bus (no row)
    rowk = collections.defaultdict(lambda: dict(entry=0, exit=0))
    need = {}
    for t in todo:
        di, dp, li, lp = t['key']
        rd, rl = ROW.match(di), ROW.match(li)
        if rl and not (rd and rd.group(1) == rl.group(1)):
            t['anchor'] = ('entry', rl.group(1)); rowk[rl.group(1)]['entry'] = max(rowk[rl.group(1)]['entry'], t['k'])
        elif rd and not rl:
            t['anchor'] = ('exit', rd.group(1)); rowk[rd.group(1)]['exit'] = max(rowk[rd.group(1)]['exit'], t['k'])
        elif rd and rl:
            # intra-row hop: stations on the hop; the row's exits NOT downstream of it get the same number as pads
            t['anchor'] = ('intra', rd.group(1)); rowk[rd.group(1)].setdefault('intra', []).append(t['key'])
            rowk[rd.group(1)]['exit'] = max(rowk[rd.group(1)]['exit'], t['k'])
        else:
            t['anchor'] = ('bus', t['key'])
        need[t['key']] = t
    # every row edge: entries (non-row -> row station data input) and exits (row station 'o' -> non-row)
    entries = collections.defaultdict(list); exits = collections.defaultdict(list)
    for key, es in by_key.items():
        si, sp, di, dp = key
        rs, rd = ROW.match(si), ROW.match(di)
        if rd and not (rs and rs.group(1) == rd.group(1)):
            entries[rd.group(1)].append(key)
        if rs and not (rd and rd.group(1) == rs.group(1)) and sp in ('o', 'b'):
            exits[rs.group(1)].append(key)
    # union-find over sources sharing a multi-driver (non-row) load port
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)
    feeders = collections.defaultdict(set)   # (load inst, port) -> {source ids}
    src_of = {}
    for key, es in by_key.items():
        si, sp, di, dp = key
        if ROW.match(di):
            continue
        rs = ROW.match(si)
        sid = ('row', rs.group(1)) if rs else ('bus', key)
        feeders[(di, dp)].add(sid)
    for lp_, sids in feeders.items():
        sids = sorted(sids, key=str)
        for s in sids[1:]:
            union(sids[0], s)
    shift = collections.defaultdict(int)
    for r, v in rowk.items():
        shift[find(('row', r))] = max(shift[find(('row', r))], v['entry'] + v['exit'])
    for key, t in need.items():
        if t['anchor'][0] == 'bus':
            shift[find(('bus', key))] = max(shift[find(('bus', key))], t['k'])
    # members of shifted components: every source of the component moves by the component shift
    members = collections.defaultdict(set)
    for lp_, sids in feeders.items():
        for s in sids:
            if shift.get(find(s)):
                members[find(s)].add(s)
    for r in rowk:
        members[find(('row', r))].add(('row', r))
    by_key_src = collections.defaultdict(list)
    for key in by_key:
        by_key_src[key[0]].append(key)
    pl = L.manifest
    gid = 0; new_E = []; drop = set(); groups = []

    def centre(n):
        v = pl.get(n)
        return (v['x'] + v['w'] / 2, v['y'] + v['h'] / 2) if v else None

    def do(key, k, pads, label):
        nonlocal gid
        es = by_key[key]
        si, sp, di, dp = key
        t = need.get(key)
        path = (t['dxy'], t['lxy']) if t else ((centre(si) or centre(di)), (centre(di) or centre(si)))
        if path[0] is None:
            raise SystemExit(f'S: no position for {key}')
        gid += 1
        clock = es[0].get('clock') or 'stream'
        if clock not in F.DOM:
            raise SystemExit(f'S: {key} clock {clock} has no domain root')
        new_E.extend(L.insert(gid, bus_bits(es), k, path, clock, label, pads_at_driver=pads))
        drop.update(id(e) for e in es)
        groups.append(dict(gid=gid, bus=f'{si}.{sp} -> {di}.{dp}', stations=k, pads=pads, label=label,
                           span_um=t['span'] if t else None, bits=sum(e['bits'] for e in es)))
    done = set()
    for root, mem in sorted(members.items(), key=lambda kv: str(kv[0])):
        T = shift.get(root, 0)
        if not T:
            continue
        for s in sorted(mem, key=str):
            if s[0] == 'row':
                r = s[1]; ke = rowk[r]['entry'] if r in rowk else 0
                for key in entries.get(r, []) if ke else []:
                    if key in done:
                        continue
                    t = need.get(key); kk = t['k'] if t else 0
                    do(key, ke, ke - kk, f'row {r} entry'); done.add(key)
                rest = T - ke
                down = collections.Counter()   # station -> stations already added upstream inside the row (intra hops)
                for ikey in rowk.get(r, {}).get('intra', []) if r in rowk else []:
                    ki = need[ikey]['k']
                    do(ikey, ki, 0, f'row {r} intra hop'); done.add(ikey)
                    seen = {ikey[2]}; q = [ikey[2]]
                    while q:
                        x_ = q.pop()
                        for (a_, ap_, b_, bp_) in by_key_src.get(x_, []):
                            if ROW.match(b_) and ROW.match(b_).group(1) == r and b_ not in seen:
                                seen.add(b_); q.append(b_)
                    for x_ in seen:
                        down[x_] = max(down[x_], ki)
                for key in exits.get(r, []) if rest else []:
                    if key in done:
                        continue
                    t = need.get(key); kk = t['k'] if t else 0
                    m_ = rest - down[key[0]]
                    if m_ <= 0:
                        continue
                    do(key, m_, m_ - kk, f'row {r} exit (component shift {T})'); done.add(key)
            else:
                key = s[1]
                if key in done:
                    continue
                t = need.get(key); kk = t['k'] if t else 0
                do(key, T, T - kk, f'direct bus (component shift {T})'); done.add(key)
    c['edges'] = [e for e in E if id(e) not in drop] + new_E
    left = [k for k in need if k not in done]
    if left:
        raise SystemExit(f'S: {len(left)} needed buses not covered, e.g. {left[:3]}')
    comp = collections.Counter()
    for root, mem in members.items():
        if shift.get(root):
            comp[shift[root]] += 1
    rep['S'] = dict(buses_needed=len(need), excluded=dict(excl), groups=len(groups), tiles=L.tiles,
                    station_stages=sum(g['stations'] for g in groups), pad_stages=sum(g['pads'] for g in groups),
                    components_by_shift=dict(sorted(comp.items())),
                    components=[dict(root=str(r), shift=shift[r], members=sorted(str(m) for m in mem)[:40], n=len(mem))
                                for r, mem in members.items() if shift.get(r)],
                    group_list=groups)


def equalize(c, L, base_trace, rep):
    """Lockstep post-pass: every load port (non-relay instance input) must move by ONE depth delta vs the base contract.
    Bits that lag the port's max delta get pad stations on their last hop (at the load), so the word keeps one age.
    PHY row_v is exempt (part A moves it to age 0 on purpose: its delta differs per bit, its new age is uniform)."""
    tn = CL.trace(c)
    port = collections.defaultdict(dict)
    for k, (r0, d0) in base_trace.items():
        v = tn.get(k)
        if v is not None:
            port[(k[0], k[1])][k[2]] = v[1] - d0
    drv_edge = {}
    for e in c['edges']:
        di, dp, dlo, dhi = e['sink']
        for j in range(dhi - dlo):
            drv_edge[(di, dp, dlo + j)] = (id(e), e['source'][0], e['source'][1], e['source'][2] + j, e.get('clock'))
    eid = {id(e): e for e in c['edges']}
    pl = L.manifest; fixed = []; drop = set(); newE = []; gid = 9000
    for (di, dp), bits in sorted(port.items()):
        if len(set(bits.values())) < 2 or (di.startswith('phy_') and dp == 'row_v'):
            continue
        M = max(bits.values())
        grp = collections.defaultdict(list)
        for b, d in sorted(bits.items()):
            if d < M:
                ei, si, sp, sb, clk = drv_edge[(di, dp, b)]
                grp[(si, sp, M - d, clk)].append(((si, sp, sb), (di, dp, b), ei))
        v = pl.get(di); cxy = (v['x'] + v['w'] / 2, v['y'] + v['h'] / 2) if v else None
        for (si, sp, k, clk), lst in sorted(grp.items(), key=lambda t: str(t[0])):
            gid += 1
            sv = pl.get(si); sxy = (sv['x'] + sv['w'] / 2, sv['y'] + sv['h'] / 2) if sv else cxy
            path = (sxy or cxy, sxy or cxy)
            newE.extend(L.insert(gid, [(a, b) for a, b, _ in lst], k, path, clk or 'stream', f'lockstep pad {di}.{dp} +{k}', pads_at_driver=k))
            for a, b, ei in lst:
                drop.add((ei, b))
            fixed.append(dict(port=f'{di}.{dp}', source=f'{si}.{sp}', bits=len(lst), pads=k))
    if fixed:
        E2 = []
        cut = collections.defaultdict(set)
        for ei, b in drop:
            cut[ei].add(b)
        for e in c['edges']:
            if id(e) not in cut:
                E2.append(e); continue
            si, sp, slo, shi = e['source']; di, dp, dlo, dhi = e['sink']
            keep = [j for j in range(dhi - dlo) if (di, dp, dlo + j) not in cut[id(e)]]
            run = []
            for j in keep + [None]:
                if run and (j is None or j != run[-1] + 1):
                    a0, a1 = run[0], run[-1] + 1
                    E2.append(dict(e, name=f"{e['name']}_k{a0}", bits=a1 - a0, source=[si, sp, slo + a0, slo + a1], sink=[di, dp, dlo + a0, dlo + a1]))
                    run = []
                if j is not None:
                    run.append(j)
        c['edges'] = E2 + newE
    rep['lockstep_pads'] = dict(ports=len({f['port'] for f in fixed}), groups=len(fixed), stages=sum(f['pads'] for f in fixed), list=fixed)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('contract'); ap.add_argument('out')
    ap.add_argument('--reach-all', required=True); ap.add_argument('--manifest', required=True)
    ap.add_argument('--reach', type=float, default=405.0)
    ap.add_argument('--sfu-r', type=int, default=0)
    ap.add_argument('--phy-rowv-direct', action='store_true')
    ap.add_argument('--no-stations', action='store_true')
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = json.loads(Path(a.contract).read_text())
    L = Layer(c); L.manifest = json.loads(Path(a.manifest).read_text())['placement']
    rep = dict(schema='opentallas.hbm.r18h_station_layer.v1', contract=a.contract, reach_all=a.reach_all, reach_um=a.reach)
    n0 = (len(c['instances']), len(c['edges']))
    if a.sfu_r:
        sfu_extend(c, L, a.sfu_r, rep)
    if a.phy_rowv_direct:
        phy_rowv_direct(c, rep)
    base_trace = CL.trace(json.loads(Path(a.contract).read_text()))
    if not a.no_stations:
        stations(c, L, json.loads(Path(a.reach_all).read_text()), a.reach, rep)
    equalize(c, L, base_trace, rep)
    c['summary']['instances'] = len(c['instances'])
    note = f"r18h station layer (r18h_station_layer.py): {json.dumps({k: v for k, v in rep.items() if k in ('B1', 'A')})}"
    if isinstance(c.get('notes'), list):
        c['notes'].append(note)
    rep['instances'] = [n0[0], len(c['instances'])]; rep['edges'] = [n0[1], len(c['edges'])]
    Path(a.out).write_text(json.dumps(c))
    Path(a.report).write_text(json.dumps(rep, indent=1))
    s = rep.get('S', {})
    print('R18H_LAYER', json.dumps(dict(B1=rep.get('B1', {}).get('cycle_delta'), A=rep.get('A', {}).get('bits'),
                                        S={k: s.get(k) for k in ('buses_needed', 'groups', 'tiles', 'station_stages', 'pad_stages',
                                                                 'components_by_shift', 'excluded')},
                                        instances=rep['instances'], edges=rep['edges'])))


if __name__ == '__main__':
    main()
