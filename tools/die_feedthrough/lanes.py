"""Lane extraction from a die connectivity dump: relay chains between endpoint blocks.

A LANE GROUP is the set of relay chains from one (source block, bus) to one (sink block, bus).  Each relay master's
data path is a pairing of its input bus to its output bus(es) (i->o, a->b, d->q*, y->b; else a unique equal-width
pair), clock / forwarded-clock / reset / enable pins are not data.  Chains are followed through relays until a
non-relay block, a die port or a non-buffer std cell (CELL:<master>) is reached.
"""
import re
import sys
from collections import defaultdict

from dies import CLOCK_BUS_RE, RESET_BUS_RE

NAMED_PAIRS = (("i", "o"), ("a", "b"), ("y", "b"), ("d", "q"), ("d", "q0"), ("d", "q1"), ("in", "out"),
               ("din", "dout"))
SIDE_BUS_RE = re.compile(r"^(ea|eb|en|fault|tie_hi|tie_lo|k\d|s|ck_s|ckf|ck_o)$")
MAX_PATHS = 400_000


def relay_pairs(master):
    """-> list of (in_bus, out_bus) data pairs of a relay master ([] = not a pass-through stage)."""
    b = master.buses
    pairs = [(i, o) for i, o in NAMED_PAIRS if i in b and o in b and b[i].dir == "INPUT" and b[o].dir == "OUTPUT"]
    if pairs:
        return pairs

    def data(bus):
        return not (CLOCK_BUS_RE.match(bus.name) or RESET_BUS_RE.match(bus.name) or SIDE_BUS_RE.match(bus.name)
                    or bus.sig == "CLOCK")
    ins = [x for x in b.values() if x.dir == "INPUT" and data(x)]
    outs = [x for x in b.values() if x.dir == "OUTPUT" and data(x)]
    if len(ins) == 1 and len(outs) == 1 and ins[0].nbits == outs[0].nbits:
        return [(ins[0].name, outs[0].name)]
    return []


def extract(dump, relay_re, land_re=None, rst_re=r"rst"):
    rre = re.compile(relay_re)
    lre = re.compile(land_re) if land_re else None
    sre = re.compile(rst_re)
    insts = dump.insts
    relay_map = {}       # master -> {in_bus: [out_bus]}
    unpaired = []
    for mn, m in dump.masters.items():
        if rre.search(mn):
            pr = relay_pairs(m)
            if not pr:
                unpaired.append(mn)
                continue
            d = defaultdict(list)
            for i, o in pr:
                d[i].append(o)
            relay_map[mn] = d

    def is_relay(inst):
        i = insts.get(inst)
        return i is not None and i.master in relay_map

    # data edges (src_inst, src_bus) -> [(dst_inst, dst_bus, bits, nbuf_max)]
    out_edges = defaultdict(list)
    has_in = set()
    for si, sb, di, db, bits, kmax, ksum, st in dump.bundles:
        if st == "CLOCK" or CLOCK_BUS_RE.match(db) or CLOCK_BUS_RE.match(sb):
            continue
        if is_relay(di) and db not in relay_map[insts[di].master]:
            continue      # reset / enable / side pin of a relay: not a lane bit
        if is_relay(si) and sb not in {o for v in relay_map[insts[si].master].values() for o in v}:
            continue
        out_edges[(si, sb)].append((di, db, bits, kmax))
        if is_relay(di):
            has_in.add(di)

    # memoised DAG walk: node = (relay inst, out bus) -> {sink (inst, bus): entry}; entry = [lasts {last_hop: bits},
    # max stages after node, min stages, next node on the longest chain, nbuf max]
    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))
    memo = {}
    active = set()
    visited = set()

    def sinks(node):
        r = memo.get(node)
        if r is not None:
            return r
        if node in active:          # combinational loop through relays: cut it
            return {}
        active.add(node)
        inst = node[0]
        res = {}
        for di, db, b, k in out_edges.get(node, ()):
            if is_relay(di):
                visited.add(di)
                for ob in relay_map[insts[di].master].get(db, ()):
                    for sk, e in sinks((di, ob)).items():
                        cur = res.get(sk)
                        capped = {lk: min(lb, b) for lk, lb in e[0].items()}   # bits = min edge width on the path
                        if cur is None:
                            res[sk] = [capped, e[1] + 1, e[2] + 1, (di, ob), max(e[4], k)]
                        else:
                            for lk, lb in capped.items():
                                cur[0][lk] = max(cur[0].get(lk, 0), lb)
                            if e[1] + 1 > cur[1]:
                                cur[1], cur[3] = e[1] + 1, (di, ob)
                            cur[2] = min(cur[2], e[2] + 1)
                            cur[4] = max(cur[4], k, e[4])
            else:
                sk = (di, db)
                cur = res.get(sk)
                if cur is None:
                    res[sk] = [{inst: b}, 0, 0, None, k]
                else:
                    cur[0][inst] = cur[0].get(inst, 0) + b if inst not in cur[0] else max(cur[0][inst], b)
                    cur[4] = max(cur[4], k)
        active.discard(node)
        memo[node] = res
        return res

    def chain_of(node, sk):
        out = []
        while node is not None:
            e = memo.get(node, {}).get(sk)
            if e is None:
                break
            node = e[3]
            if node is not None:
                out.append(node[0])
        return tuple(out)

    groups = []

    def emit(start_inst, start_bus, head=()):
        for sk, e in sinks((start_inst, start_bus)).items():
            chain = tuple(head) + chain_of((start_inst, start_bus), sk)
            g = dict(src=start_inst, src_bus=start_bus, dst=sk[0], dst_bus=sk[1], bits=sum(e[0].values()),
                     chains=len(e[0]), stages_max=e[1] + len(head), stages_min=e[2] + len(head), nbuf_max=e[4],
                     path=chain, rst=any(sre.search(insts[c].master) for c in chain),
                     lands=sum(1 for c in chain if lre is not None and lre.search(insts[c].master)))
            groups.append(g)

    starts = sorted({(si, sb) for (si, sb) in out_edges if not is_relay(si)})
    for si, sb in starts:
        emit(si, sb)
    # chains whose head relay is driven by something the dump does not expand (std-cell flop, hi-fanout net)
    orphan_heads = 0
    for name, inst in insts.items():
        if inst.master in relay_map and name not in has_in and name not in visited:
            orphan_heads += 1
            visited.add(name)
            for ib, obs in relay_map[inst.master].items():
                for ob in obs:
                    emit(name, ob, (name,))
    npaths = sum(g["chains"] for g in groups)
    truncated = False
    n_relays = sum(1 for i in insts.values() if i.master in relay_map)
    stats = dict(relay_masters=len(relay_map), unpaired_relay_masters=sorted(unpaired)[:50],
                 n_unpaired_relay_masters=len(unpaired), n_relays=n_relays, n_relays_on_lanes=len(visited),
                 paths=npaths, truncated=truncated, orphan_heads=orphan_heads, groups=len(groups))
    return groups, relay_map, stats
