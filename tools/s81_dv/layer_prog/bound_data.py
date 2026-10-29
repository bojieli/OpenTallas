#!/usr/bin/env python3
"""Bound data transports: re-age every legacy die link from ONE strict bind (TOK-S81-2, 10-28).

The data compiler (dv_layer_compile.py) reads die transport ages from the as-built die tree (die.v relay stations
st_<link>_<i>, landings ld_<link> with K strap, abutted 0-station links): Die.links[link].age_edges.  A strict bind
(tools/die_plan/bind.py) removes that as-built transport and re-emits every crossing as plan boundary flops + feed-
through stations + pads (+ clock landing cycles).  This module replaces each legacy link age with the age of the SAME
bits in the bound die, from the bind's own per-bit records; nothing is padded, normalised or defaulted.

Inputs (all from one bind out/ dir, sha-pinned in the report):
  bus_groups.json  landing[]: per sink leaf + source partition, per bit range: source pin, as-built register stages
                   (half-cycle relay stations count 1 stage each) and the bound depth in cycles (bind bitcyc)
  bind_latency.json buses[]: per plan lane its bound_stages (cross-check: every member's bound depth == its lane's)
  bind_names.json  bound leaf -> as-built leaf path (partition membership of every die-level instance)
  bind_report.json n_errors / errors / type_splits; provenance_bind.json manifest (must be the given manifest)
The as-built die.v of the legacy tree must be the manifest's netlist (sha256 equal), else nothing is re-aged.

Per legacy link (src die instances S, dst die instances D, n relay stations, landing K):
  CROSSING  bound bits whose source top is in S and sink top is in D (or the link's own retained landing ld_<link>):
            the as-built leaf-to-leaf stages are split as  n stations + (K+1 if the landing is removed) + x,  x >= 0 the
            non-transport register stages inside the die instances (the legacy die-port age does not include them).
            as-built leaf-to-leaf cycles = legacy age + x (landing removed) or n/2 + x (landing retained, its K+1 stays);
            bound age = legacy age + (bound depth - as-built cycles), one value over every bit of the link.
  INTRA     no crossing bit: every die instance of the link (endpoints, stations, landing) lies in ONE partition ->
            the as-built transport is inside that partition and stays: age unchanged.
Anything else is BLOCKED with the reason (no bits / mixed values / negative age / x < 0 / lane depth mismatch /
port ambiguity); a blocked link raises on any read of its age (fail closed), never 0.

Scope: die-level link ages only.  The priced p4l layer schedule (layer_schedule) and the intra-frame calendars keep
their own sources; the report says so.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

SCHEMA = 'opentallas.s81_dv.bound_data_links.v1'


class BoundBlocked(RuntimeError):
    """not a KeyError: a generic `except KeyError` fallback in a lowering must not swallow it"""


class BlockedLink(dict):
    """a legacy link whose bound age is not established: reading its age raises (never a silent 0 / legacy value)"""

    hits = None     # list shared with the die: every read is logged even if a lowering swallows the exception

    def __getitem__(self, k):
        if k == 'age_edges':
            if self.hits is not None:
                self.hits.append(super().get('name'))
            raise BoundBlocked(f"bound data link {self.get('name')}: {self.get('bound_blocked')}")
        return super().__getitem__(k)

    def get(self, k, d=None):
        if k == 'age_edges':
            return self['age_edges']
        return super().get(k, d)

    def __contains__(self, k):
        return k == 'age_edges' or super().__contains__(k)


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _top(path):
    return path.split('.')[0]


def load_bind(bound, manifest=None, root=None, *, diagnostic=False):
    """read + pin the bind records; strict unless diagnostic (then the bind's errors are carried, never cleared)"""
    bound = Path(bound)
    rep = json.loads((bound / 'bind_report.json').read_text())
    errs = int(rep.get('n_errors') or 0)
    clean = errs == 0 and not rep.get('errors') and not rep.get('type_splits')
    if not clean and not diagnostic:
        raise ValueError(f'bound data mode needs a clean strict bind: n_errors {errs}, '
                         f'type_splits {len(rep.get("type_splits") or [])}')
    prov = json.loads((bound / 'provenance_bind.json').read_text()).get('provenance', {})
    netlist_sha = None
    if manifest is not None:
        if prov.get('manifest') != manifest:
            raise ValueError(f'bind manifest {prov.get("manifest")} != selected {manifest}')
        m = json.loads((Path(root) / manifest).read_text())
        nl = m['netlist'] if isinstance(m['netlist'], list) else [m['netlist']]
        if len(nl) != 1:
            raise ValueError(f'manifest names {len(nl)} netlists; bound data needs exactly one die top')
        netlist_sha = file_sha(Path(root) / nl[0])
    groups = json.loads((bound / 'bus_groups.json').read_text())
    lat = json.loads((bound / 'bind_latency.json').read_text())
    names = json.loads((bound / 'bind_names.json').read_text())
    return dict(bound=bound, clean=clean, n_errors=errs, type_splits=len(rep.get('type_splits') or []),
                provenance=prov, netlist_sha256=netlist_sha, landing=groups['landing'], internal=groups.get('internal', []),
                image_selectors=rep.get('instance_path_params', []),
                lane_bound={b['lane']: b['bound_stages'] for b in lat['buses']}, names=names,
                sha256={f: file_sha(bound / f) for f in ('bind_report.json', 'bus_groups.json', 'bind_latency.json',
                                                         'bind_names.json', 'provenance_bind.json')})


def index_bits(B):
    """flat per-bit-range members: source/sink die tops + ports, as-built stages, bound depth, lane"""
    mem, lane_err = [], []
    for g in B['landing']:
        for m in g['members']:
            src = m['source']
            b0 = m['bound_stages']
            lane = m.get('lane')
            want = B['lane_bound'].get(lane)
            mem.append(dict(stop=_top(src), sport=src.rsplit('.', 1)[1], source=src, sink=g['sink'],
                            ktop=_top(g['sink']), kport=m['sink_port'], sink_bits=m['sink_bits'],
                            a=m['asbuilt_stages'], b=m.get('landed_stages', b0), b0=b0, lane=lane,
                            sink_part=g['sink_part'], src_part=g['src_part']))
            if lane not in ('UNPLANNED', 'spine', None) and want is not None and b0 < want:
                lane_err.append((lane, g['sink'], m['sink_port'], b0, want))
    return mem, lane_err


def partitions_of_tops(names):
    out = defaultdict(set)
    for bound, asb in names.items():
        out[_top(asb if asb.startswith('u_') or '.' in asb else asb)].add(bound.split('.')[0])
    return out


def _bits(m):
    return sum(hi - lo + 1 for lo, hi in m['sink_bits'])


def rebind_links(die, B, *, diagnostic=False):
    """re-age die.links in place from bind B (load_bind); returns the per-link report"""
    if B['netlist_sha256'] is not None and B['netlist_sha256'] != die.die_sha:
        raise ValueError(f'bind netlist {B["netlist_sha256"][:12]} is not the legacy tree die.v {die.die_sha[:12]}')
    mem, lane_err = index_bits(B)
    by_pair = defaultdict(list)
    for m in mem:
        by_pair[(m['stop'], m['ktop'])].append(m)
    tparts = partitions_of_tops(B['names'])
    st_of = defaultdict(list)
    for n in die.inst:
        if n.startswith('st_'):
            st_of[n[3:].rsplit('_', 1)[0]].append(n)
    def bundle_key(lk, L):
        # sub-lanes <stem>_l<i> of one bundle between the same die instances (their port sets may differ per lane)
        return (re.sub(r'_l\d+$', '', lk), frozenset(x[0] for x in L['src']), frozenset(x[0] for x in L['dst']))
    sib = defaultdict(list)
    for lk, L in die.links.items():
        sib[bundle_key(lk, L)].append(lk)
    inner = defaultdict(list)
    for m in B.get('internal') or []:
        inner[(_top(m['source']), _top(m['sink']))].append(m)
    def select(lk, L):
        S = {x[0] for x in L['src']}
        D = {x[0] for x in L['dst']}
        sp = {x[1] for x in L['src']}
        dp = {x[1] for x in L['dst']}
        land = L.get('landing')
        # crossing bits: sink at a die-level destination (landing removed) or at the retained landing tile
        cand = [(m, False) for s in S for d in D for m in by_pair.get((s, d), [])]
        if land:
            cand += [(m, True) for s in S for m in by_pair.get((s, land), [])]
        # port identity: the die-level port names when they reach the leaf; else the pair must be unambiguous
        exact = [(m, r) for m, r in cand if (r or m['kport'] in dp) and m['sport'] in sp]
        portk = [(m, r) for m, r in cand if (r or m['kport'] in dp)]
        return ((exact, 'ports') if exact else ((portk, 'sink_port') if portk else (cand, 'pair')))

    rows, new = {}, {}
    for lk, L in sorted(die.links.items()):
        S = {s for s, _ in L['src']}
        D = {d for d, _ in L['dst']}
        sp = {p for _, p in L['src']}
        dp = {p for _, p in L['dst']}
        land = L.get('landing')
        legacy = L['age_edges']
        n = L['stations']
        K = L['K'] if L['K'] is not None else L['E']
        landed = bool(land or L.get('internal_landing'))
        row = dict(link=lk, legacy_age=legacy, stations=n, K=K, landed=landed, src=sorted(S), dst=sorted(D))
        use, ident = select(lk, L)
        siblings = sib[bundle_key(lk, L)]
        if len(siblings) > 1:
            pool = {}
            for Lk in siblings:
                for m, r in select(Lk, die.links[Lk])[0]:
                    pool[id(m)] = (m, r and Lk == lk)
            use = list(pool.values())
        if use and len(siblings) > 1:
            # sub-lanes of one bundle (_l0/_l1/..) share the die ports and endpoint logic: find the ONE common
            # non-transport stage count x such that every sub-lane i owns the bits with as-built stages T_i + x
            # (T_i = its n stations [+ K+1 when the landing is removed]) and every bound bit is owned; else BLOCKED
            def T(Lk, r=False):
                Li = die.links[Lk]
                Ki = Li['K'] if Li['K'] is not None else Li['E']
                keep = r or Li.get('internal_landing') or not (Li.get('landing') or Li.get('internal_landing'))
                return Li['stations'] + (0 if keep else Ki + 1)
            Ts = {Lk: T(Lk) for Lk in siblings}
            xs_ok = [x for x in sorted({m['a'] - t for m, _ in use for t in Ts.values()})
                     if all(any(m['a'] == t + x for m, _ in use) for t in Ts.values())
                     and all(any(m['a'] == t + x for t in Ts.values()) for m, _ in use)]
            ident += f'+bundle({len(siblings)})'
            if len(xs_ok) != 1:
                use = []
                row.update(cls='CROSSING', identity=ident, status='BLOCKED',
                           reason=f'bundle of {len(siblings)} sub-lanes on the same ports: {len(xs_ok)} common '
                                  f'in-instance stage counts fit (need exactly 1) for transport stages {sorted(set(Ts.values()))}')
            else:
                use = [(m, r) for m, r in use if m['a'] == Ts[lk] + xs_ok[0]]
                row.update(bundle_x=xs_ok[0])
        if row.get('status'):
            pass
        elif not S or not D:
            row.update(cls='DEAD' if S else 'NOSRC', status='BLOCKED',
                       reason=f'legacy link without a die-level {"sink" if S else "source"} (src {sorted(S)} dst '
                              f'{sorted(D)}): no transport to re-age')
        elif not use:
            parts = set()
            for t in S | D:
                parts |= tparts.get(t, {'?' + t})
            row.update(partitions=sorted(parts))
            ch = [m for s_ in S for d in D for m in inner.get((s_, d), [])]
            if len(parts) == 1 and not any(p.startswith('?') for p in parts):
                # relays/landing dissolve into the partition as kept intra stages; bus_groups.internal lists every
                # intra edge whose kept depth differs from as-built (none -> unchanged)
                dz = {m['landed_stages'] - m['asbuilt_stages'] for m in ch}
                if len(dz) > 1:
                    row.update(cls='INTRA', status='BLOCKED', reason=f'intra edge depth changes differ {sorted(dz)}')
                else:
                    row.update(cls='INTRA', bound_age=legacy + (dz.pop() if dz else 0), status='PASS',
                               basis='both endpoints in one partition: as-built transport kept as intra stages'
                                     + (f' with bus_groups.internal change' if ch else ''))
            else:
                row.update(cls='NONE', status='BLOCKED',
                           reason=f'no bound crossing bits between {sorted(S)} and {sorted(D)} and not one partition '
                                  f'({sorted(parts)[:6]})')
        if row.get('status'):
            pass
        else:
            vals, xs, lanes, nb = set(), set(), set(), 0
            for m, retained in use:
                if retained or L.get('internal_landing'):
                    # the landing (die tile kept in the sink partition, or the x_frame lk landing inside the receiving
                    # frame) stays; the bit's sink leaf is its input: as-built = n stations + x, landing K+1 retained
                    x = m['a'] - n
                    age = legacy + m['b'] - (math.ceil(n / 2) + x)
                else:
                    x = m['a'] - n - ((K + 1) if landed else 0)
                    age = m['b'] - x
                xs.add(x)
                vals.add(age)
                lanes.add(m['lane'])
                nb += _bits(m)
            row.update(cls='CROSSING', identity=ident, bits=nb, lanes=sorted(lanes), x_stages=sorted(xs),
                       bound_values=sorted(vals), asbuilt_stages=sorted({m['a'] for m, _ in use}),
                       bound_depth=sorted({m['b'] for m, _ in use}))
            bad = [x for x in xs if x < 0]
            if bad:
                row.update(status='BLOCKED', reason=f'as-built stages below the legacy transport (x {sorted(xs)}): '
                                                    f'the bind path is not this link')
            elif len(vals) != 1:
                row.update(status='BLOCKED', reason=f'mixed bound ages over the link bits {sorted(vals)} '
                                                    f'(identity {ident}, lanes {sorted(lanes)[:4]})')
            else:
                v = vals.pop()
                if v < 0:
                    row.update(status='BLOCKED', reason=f'bound age {v} < 0: the bind removed {-v} in-instance '
                                                        f'stage(s) the unit model counts; unit constants must be re-derived')
                else:
                    row.update(status='PASS', bound_age=v)
        rows[lk] = row
        if row['status'] == 'PASS':
            new[lk] = dict(L, age_edges=row['bound_age'], legacy_age_edges=legacy, bound_cls=row['cls'])
        else:
            new[lk] = BlockedLink({k: v for k, v in L.items() if k != 'age_edges'}, name=lk,
                                  bound_blocked=row['reason'], legacy_age_edges=legacy)
    die.bound_blocked_hits = []
    for v in new.values():
        if isinstance(v, BlockedLink):
            v.hits = die.bound_blocked_hits
    die.links = new
    stat = defaultdict(int)
    for r in rows.values():
        stat[f"{r['cls']}_{r['status']}"] += 1
    changed = sum(1 for r in rows.values() if r['status'] == 'PASS' and r['bound_age'] != r['legacy_age'])
    rec = dict(schema=SCHEMA, verdict=('DIAGNOSTIC' if diagnostic or not B['clean'] else
                                       ('PASS' if all(r['status'] == 'PASS' for r in rows.values()) else 'BLOCKED')),
               bind_clean=B['clean'], bind_errors=B['n_errors'], bind_type_splits=B['type_splits'],
               bind_dir=str(B['bound']), bind_sha256=B['sha256'], bind_provenance=B['provenance'],
               die_v_sha256=die.die_sha, netlist_sha256=B['netlist_sha256'],
               counts=dict(stat), links=len(rows), changed=changed, lane_depth_below_lane=lane_err[:50],
               scope='die-level link ages only; the priced p4l layer schedule and intra-frame calendars keep their own '
                     'sources (not re-aged here)',
               rows=rows)
    return rec
