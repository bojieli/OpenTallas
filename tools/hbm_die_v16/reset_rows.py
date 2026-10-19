#!/usr/bin/env python3
"""HBM-RSTROW 10-19 (coordinator 0jp, Proposal A): reset carried along each relay row.

A relay row = the data graph of hbfd_rly_<W>_<flow> stations (o -> i edges between relays).  Every station whose rs is
bound to hb_ckgen por_<dom> is in a row.  Row HEADS (no relay upstream) stay reset-forest sinks; every other station
takes rs from the rso output of its BFS parent (its upstream relay of minimum data depth), so the release walks the row in
lockstep with the data.  A station with a row successor is remastered to hbfd_rly_<W>_<flow>_rr (same stage + one row
reset flop rso, rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv: rso releases 1 edge after rs); row tails keep their base master
(no open rso output).

Release-age contract (ideal common-phase edge model, as the forest): head fed at age A, station at data depth k releases
rso at A + k + 1 and its stage at A + k + S (S = 3 for the registered-reset-relay classes: W > 256 or RS_RELAY=1, else 0).
Producer data (producer = a block / landing released at the domain age D, or later) reaches depth k no earlier than
D + 1 + k, so the row is exact when A + S <= D + 1 for every station of the head's subtree: the head's forest target is
A = D + off with off = min(0, 1 - max S) (-2 when any station has S = 3).  Earlier releases only pass producer reset-state
outputs.  Stations whose rs is NOT a por binding (e.g. hcx_* driven by hc rstb_w) are not rows; they act as producers.
"""
import collections
import re

BASE = re.compile(r'^hbfd_rly_(\d+)_(WE|EW|SN|NS)$')
RR_SRC = 'rtl/hbm_accel/die_glue/hbfd_rly_rr_masters.sv'
RR_DEPS = ['rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv', 'rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']
# rtl/hbm_accel/die_glue/hbfd_rly_masters.sv: classes with ot_hbm_rly RS_RELAY=1 (W <= 256) -> stage release lag 3
RS_RELAY_BASE = {'hbfd_rly_136_NS', 'hbfd_rly_136_SN', 'hbfd_rly_136_EW', 'hbfd_rly_136_WE'}


def stage_lag(master):
    m = BASE.match(master)
    w = int(m.group(1))
    return 3 if (w > 256 or master in RS_RELAY_BASE) else 0


def plan_rows(c):
    """-> dict(heads={inst: off}, parent={inst: parent}, depth={inst: k}, lag={inst: S}, remaster=[...], stats={...})"""
    I = c['instances']
    por = {x['instance']: x for x in c['clock_resets']
           if x['kind'] == 'reset' and x['port'] == 'rs' and x['source'][0] == 'hb_ckgen'}
    R = {n for n, v in I.items() if BASE.match(v['master']) and n in por}
    up, dn = collections.defaultdict(set), collections.defaultdict(set)
    for e in c['edges']:
        si, sp, di, dp = e['source'][0], e['source'][1], e['sink'][0], e['sink'][1]
        if si in R and di in R and dp == 'i':
            if sp != 'o':
                raise ValueError(f'relay row edge from {si}.{sp} (expected o)')
            if por[si]['source'] != por[di]['source']:
                raise ValueError(f'relay row crosses reset domains: {si} -> {di}')
            up[di].add(si)
            dn[si].add(di)
    heads = sorted(r for r in R if not up[r])
    depth, parent, root = {}, {}, {}
    q = collections.deque()
    for h in heads:
        depth[h], root[h] = 0, h
        q.append(h)
    while q:
        x = q.popleft()
        for y in sorted(dn[x]):
            if y not in depth:
                depth[y], parent[y], root[y] = depth[x] + 1, x, root[x]
                q.append(y)
    if len(depth) != len(R):
        raise ValueError(f'{len(R) - len(depth)} relay stations on relay-only cycles (no producer)')
    lag = {r: stage_lag(I[r]['master']) for r in R}
    worst = collections.defaultdict(int)
    for r in R:
        worst[root[r]] = max(worst[root[r]], lag[r])
    off = {h: min(0, 1 - worst[h]) for h in heads}
    adj = collections.defaultdict(list)
    for y, x in parent.items():
        adj[x].append(y)
        adj[y].append(x)
    # feed fallbacks (a head whose rs has no reachable leaf home, e.g. a row starting inside a 28 um channel): the
    # stations along the row's heaviest branch, shallowest first; finalize() re-roots the row's reset tree there
    sub = collections.Counter()
    for r in sorted(depth, key=depth.get, reverse=True):
        sub[r] += 1
        if r in parent:
            sub[parent[r]] += sub[r]
    kids_of = collections.defaultdict(list)
    for y, x in parent.items():
        kids_of[x].append(y)
    alts = {}
    for h in heads:
        path, x = [], h
        while kids_of[x] and len(path) < 16:
            x = max(sorted(kids_of[x]), key=lambda k: sub[k])
            path.append(x)
        alts[h] = path
    size = collections.Counter(root.values())
    stats = dict(stations=len(R), heads=len(heads), chained=len(parent), max_depth=max(depth.values(), default=0),
                 merges=sum(1 for r in R if len(up[r]) > 1), max_row_stations=max(size.values(), default=0),
                 head_offsets=dict(collections.Counter(off.values())),
                 domains=dict(collections.Counter(por[h]['source'][1] for h in heads)))
    rows = dict(heads=off, parent=parent, depth=depth, lag=lag, root=root, adj=adj, alts=alts, stats=stats,
                masters={r: I[r]['master'] for r in R})
    fin = finalize(rows, {})
    stats.update(remastered=len(fin['remaster']), tails_base_master=len(R) - len(fin['remaster']),
                 rr_masters=dict(collections.Counter(x['master'] for x in fin['remaster'])))
    return rows


def tree_dist(rows, f):
    """reset-tree distance from station f over its row (undirected BFS tree) -> {station: (dist, reset parent)}"""
    out = {f: (0, None)}
    q = collections.deque([f])
    while q:
        x = q.popleft()
        for y in sorted(rows['adj'][x]):
            if y not in out:
                out[y] = (out[x][0] + 1, x)
                q.append(y)
    return out


def feed_offset(rows, f):
    """target offset (<= 0) of a forest leaf feeding station f: every station x of the row releases its stage at
    A + dist(f, x) + S_x <= D + 1 + depth(x)"""
    t = tree_dist(rows, f)
    return min(0, min(1 + rows['depth'][x] - rows['lag'][x] - d for x, (d, _) in t.items()))


def finalize(rows, feeds):
    """feeds {head: feed station} (default the head) -> reset parent map, feed list, remaster list"""
    rparent, feed_of = {}, {}
    for h in rows['heads']:
        f = feeds.get(h, h)
        for x, (d, p) in tree_dist(rows, f).items():
            feed_of[x] = f
            if p is not None:
                rparent[x] = p
    drivers = sorted(set(rparent.values()))
    remaster = [dict(inst=r, old=rows['masters'][r], master=rows['masters'][r] + '_rr', source=RR_SRC,
                     rtl_deps=list(RR_DEPS)) for r in drivers]
    return dict(rparent=rparent, feed_of=feed_of, feeds=sorted(set(feed_of.values())), remaster=remaster)


def check_release(rows, fin, feed_age, domain_age):
    """independent edge-model check: every station releases its stage by D + 1 + depth (feed_age: {feed: A},
    domain_age: {head: D}); rs age = forest leaf age at a feed, else the reset parent's rso age + 1."""
    bad, age = [], {}

    def rs_age(r):
        if r not in age:
            p = fin['rparent'].get(r)
            age[r] = feed_age[r] if p is None else rs_age(p) + 1
        return age[r]
    for r in sorted(rows['depth'], key=rows['depth'].get):
        rs_age(r)
        D = domain_age[rows['root'][r]]
        if age[r] + rows['lag'][r] > D + 1 + rows['depth'][r]:
            bad.append((r, age[r] + rows['lag'][r], D + 1 + rows['depth'][r]))
    return age, bad
