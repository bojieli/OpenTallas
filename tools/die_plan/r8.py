"""R8 bus-coherent latency (COORD 10-23 15:28; STEWARD-TOKh xt1 0/64+0/64 on the bound Qwen compute top).

The plan cuts as-built same-cycle words into crossings of unequal depth: u_tap.hw reached heads hc0..hc3 at
+6/+4/+2/+4 over the b_hw forwarding chain while its direct x_tap bits came +5/+4/+2/+3, so the column go's staggered
171-174 instead of all at 151.  R8:
  (1) every as-built bus (valid + data + forwarded bits) lands as ONE group: equal added delay on every bit,
  (2) replicated consumers of one source get equal delays (pad to the slowest replica),
  (3) the as-built valid/data relationship stays: no bit may land before a bit that was ahead of it as built.

Input = BINDER2's bus_groups.json (bind.py Binder.bus_groups(), from the as-built netlist bound to this plan):
  landing[]  per sink leaf and source partition: members {sink_port, sink_bits, source, asbuilt_stages, bound_stages
             (depth through the plan lanes), landed_stages (after the binder's own landing pads), lane};
  replica[]  per source pin: the sink partitions that got it at the same as-built depth, with their bound depths.

A member's OFFSET = depth - asbuilt_stages (the cycles the plan adds).  R8 holds when every member of a landing group
and every member fed by one replica set has the same offset: the compiler then absorbs one uniform shift per bus and
every as-built relationship (valid vs data, head vs head) is kept, so (3) follows from (1).  Equal-offset classes are
the connected components of {landing groups} + {replica sets}; each member is padded to its class's largest offset.
Pads sit at the sink landing (after the sink partition's in boundary flop, only on the bits that leaf consumes), so a
forwarded bit is never delayed for the partitions further down its chain (lane pads cannot fix a forwarding chain:
tap->hc2->hc1->hc0 needs hc2 +4, hc1 +2, hc0 +0 on the same lanes).

    python3 tools/die_plan/r8.py pads  PLAN.json BUS_GROUPS.json [--out DIR] [--replica all|type]
        -> DIR/<die>_r8_landing.json (pad per member = what the binder realises as ot_dp_dly landing pads; the
           compiler reads `members[].landed`), summary: classes, padded bits, pad flops, depth before -> after
    python3 tools/die_plan/r8.py check PLAN.json BUS_GROUPS.json [--landing FILE] [--replica all|type]
        G0 R8: ERROR on unequal offsets in a landing group, unequal offsets across a replica set, an as-built order
        inversion (a bit landing before one that led it as built), and a replicated partition TYPE whose instances need
        different pads (types are hardened once: split the type or re-plan the cut).  Depth checked = the landing
        file's `landed` when given (the planned pads), else bus_groups `landed_stages` (what the bound top has).

--replica all (default) equalises every broadcast at one as-built depth; `type` only sinks of one partition type.

LANDED BUNDLES (COORD rule 10-23, S81-P9-R8EQ; all dies): an as-built bundle whose lanes land in ONE forwarded-clock
landing ring with ONE K strap (ot_s81_land / dsfd_dvland_* / the frame dsfd_cfifo_crs4 lanes) has ONE as-built depth:
the ring reads the word of forwarded edge m - R0 - K + G, so the per-lane relay flight (half-cycle HC1 stations,
counted as stages by the binder) is absorbed inside the landing window and the lanes are word-aligned at the ring
output.  R8 therefore pads such a bundle to one group depth, not per lane (per-lane pads would re-create a lane tear).
The rule holds only while the per-lane as-built skew stays under the landing window margin: (max - min stages) x
--landed-stage-cycles <= --landed-window - 1 cycles; a bundle over the margin keeps its per-lane depths (pads) and is an
R8 check ERROR (the as-built bundle could not land coherently: re-plan or rule).  A member is in a landed bundle when
its bus group member has `landed_bundle: true` (binder) or its plan lane id matches --landed RX.  Members are bundled
per landing group (sink leaf, source partition).

    --landed RX (repeatable)  --landed-window D (ring depth, default 4)  --landed-stage-cycles C (default 0.5 = HC1)
    --landed-over-margin keep|collapse (default keep = ERROR + per-lane pads; collapse = WARN, one depth: a ruling)
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

SCHEMA = "opentallas.die_plan.r8_landing.v1"


def nbits(rs):
    return sum(b - a + 1 for a, b in rs)


def mkey(g, m):
    """stable member id: sink leaf . port [bits] <- source [bits]"""
    sb = ",".join(f"{a}:{b}" for a, b in m["sink_bits"])
    return f"{g['sink']}.{m['sink_port']}[{sb}]<-{m['source']}@{m.get('asbuilt_lane_stages', m['asbuilt_stages'])}"


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[max(a, b)] = min(a, b)


LANDED = dict(rx=[], window=4, stage_cycles=0.5, over="keep")


def landed_bundles(bg, rx=None, window=None, stage_cycles=None):
    """LANDED BUNDLES rule (module doc): returns (bus_groups copy with each in-margin landed bundle's members at ONE
    as-built depth = the bundle maximum, original per-lane depth kept as `asbuilt_lane_stages`, list of findings
    [dict(sink, src_part, skew_stages, skew_cycles, margin, ok)])."""
    rx = LANDED["rx"] if rx is None else [re.compile(x) if isinstance(x, str) else x for x in rx]
    window = LANDED["window"] if window is None else window
    stage_cycles = LANDED["stage_cycles"] if stage_cycles is None else stage_cycles
    out = json.loads(json.dumps(bg))
    found = []
    for g in out.get("landing", []):
        ms = [m for m in g["members"] if not is_async(m) and (
            m.get("landed_bundle") or (m.get("lane") and any(x.search(m["lane"]) for x in rx)))]
        if len(ms) < 2:
            continue
        lo, hi = min(m["asbuilt_stages"] for m in ms), max(m["asbuilt_stages"] for m in ms)
        skew = (hi - lo) * stage_cycles
        ok = skew <= window - 1
        found.append(dict(sink=g["sink"], src_part=g["src_part"], members=len(ms), skew_stages=hi - lo,
                          skew_cycles=skew, margin=window - 1, ok=ok, collapsed=ok or LANDED["over"] == "collapse"))
        if (ok or LANDED["over"] == "collapse") and hi != lo:
            for m in ms:
                m["asbuilt_lane_stages"] = m["asbuilt_stages"]
                m["asbuilt_stages"] = hi
    return out, found


RESET_RX = re.compile(r"(?i)(^|_)[a-z]?(rst|reset|por)(_?n|_b)?$|(^|_)[a-z]?(rst|reset)_n_")
# --exempt RX (BINDER3 10-23, KV-P5 15:57 proposal): extra pins outside R8, e.g. sticky FAULT / health flags
# (`(^|_)(fault|flt)$` on the source pin): a set-and-hold flag has no static-schedule term, so its as-built offset to
# the data of the same leaf is not a functional invariant (unioning it with kreq re-padded the K request per frame).
EXEMPT = []


def is_async(m):
    """R8 does not apply: a reset-spine member (bind asbuilt.reset_spines: async assert, released by the sink's own
    synchroniser) or a reset bit on a lane (sink port or source pin named *rst_n / reset / por): reset release is
    counted by the plan's reset epoch (schema reset.release = counted), not by the as-built relay depth."""
    if m.get("lane") == "spine":
        return True
    pin = m["source"].rpartition(".")[2]
    if any(x.search(pin) or x.search(m["sink_port"]) for x in EXEMPT):
        return True
    return bool(RESET_RX.search(m["sink_port"]) or RESET_RX.search(pin))


def bus_key(g, m, bus):
    """the as-built bus a member belongs to: `part` = every input of one sink leaf from one source partition
    (BINDER2's landing group), `leaf` = from one source LEAF (one source module's valid + data + forwarded bits)."""
    # bus_sub (optional, set by a die's bus-group prep, e.g. KV r8_invariant_split.py): pins of one source leaf whose
    # as-built relative offset is NOT the same in every instance of the sink type were never one functional bus
    sub = (m["bus_sub"],) if m.get("bus_sub") else ()
    if m.get("bus_join"):
        # bind.py bus_join (TOK-QK/C 10-24): one as-built port split over partitions (split macro halves) and/or a
        # re-homed glue join of crossing bits with its consumer = ONE bus across source partitions
        return ("join", m["bus_join"]) + sub
    if bus == "leaf":
        return (g["sink"], g["src_part"], m["source"].rpartition(".")[0]) + sub
    return (g["sink"], g["src_part"]) + sub


def nodes(bg, bus="part"):
    """flat member list [(bus key, group, member)] without async reset-spine members"""
    return [(bus_key(g, m, bus), g, m) for g in bg["landing"] for m in g["members"] if not is_async(m)]


def part_types(raw):
    return {p["name"]: p["type"] for p in raw["partitions"]}


def classes(bg, raw, replica="all", bus="part"):
    """union-find over members: one landing group = one class; a replica set joins the members (in every listed sink
    partition) fed by its source pin at its as-built depth.  Returns (node list, UF, replica links used)."""
    N = nodes(bg, bus)
    uf = UF(len(N))
    first = {}
    by_src = defaultdict(list)            # (source pin, sink part, asbuilt) -> node ids
    for i, (gi, g, m) in enumerate(N):
        if gi in first:
            uf.union(first[gi], i)
        else:
            first[gi] = i
        by_src[(m["source"], g["sink_part"], m["asbuilt_stages"])].append(i)
    pt = part_types(raw)
    used = 0
    for r in bg.get("replica", []):
        parts = r["sink_parts"]
        if replica == "type":
            bytype = defaultdict(list)
            for p in parts:
                bytype[pt.get(p, p)].append(p)
            sets = [ps for ps in bytype.values() if len(ps) > 1]
        else:
            sets = [parts]
        for ps in sets:
            ids = [i for p in ps for i in by_src.get((r["source"], p, r["asbuilt_stages"]), [])]
            if len({N[i][1]["sink_part"] for i in ids}) > 1:
                used += 1
            for i in ids[1:]:
                uf.union(ids[0], i)
    return N, uf, used


def _depth(m, landing):
    return m["bound_stages"] if landing is None else landing


def solve(bg, raw, replica="all", bus="part"):
    """pads so every class lands at one offset (the class maximum); landed bundles first get one as-built depth."""
    bg = landed_bundles(bg)[0]
    N, uf, used = classes(bg, raw, replica, bus)
    off = [m["bound_stages"] - m["asbuilt_stages"] for _, _, m in N]
    cmax = defaultdict(lambda: -10 ** 9)
    for i in range(len(N)):
        c = uf.find(i)
        cmax[c] = max(cmax[c], off[i])
    mem = []
    for i, (gi, g, m) in enumerate(N):
        pad = cmax[uf.find(i)] - off[i]
        mem.append(dict(id=mkey(g, m), sink=g["sink"], sink_part=g["sink_part"], src_part=g["src_part"],
                        sink_port=m["sink_port"], sink_bits=m["sink_bits"], source=m["source"],
                        asbuilt=m["asbuilt_stages"], bound=m["bound_stages"], pad=pad,
                        **({"asbuilt_lane": m["asbuilt_lane_stages"]} if "asbuilt_lane_stages" in m else {}),
                        landed=m["bound_stages"] + pad, cls=uf.find(i), lane=m.get("lane")))
    return mem, used


def summary(bg, mem, used):
    bits = [nbits(m["sink_bits"]) for m in mem]
    ncls = len({m["cls"] for m in mem})
    return dict(members=len(mem), classes=ncls, replica_links=used,
                padded_members=sum(1 for m in mem if m["pad"]),
                padded_bits=sum(b for m, b in zip(mem, bits) if m["pad"]),
                pad_flops=sum(b * m["pad"] for m, b in zip(mem, bits)),
                max_pad=max((m["pad"] for m in mem), default=0),
                max_depth_before=max((m["bound"] for m in mem), default=0),
                max_depth_after=max((m["landed"] for m in mem), default=0),
                max_offset_before=max((m["bound"] - m["asbuilt"] for m in mem), default=0),
                max_offset_after=max((m["landed"] - m["asbuilt"] for m in mem), default=0),
                binder_landed_max=max((m["landed_stages"] for g in bg["landing"] for m in g["members"]), default=0))


def type_norm(raw):
    """per partition: (type, regex that blanks the instance's distinguishing name tokens in a sink path)."""
    pt = part_types(raw)
    inst = defaultdict(list)
    for p, t in pt.items():
        inst[t].append(p)
    out = {}
    for t, ps in inst.items():
        toks = [p.split("_") for p in ps]
        L = max(len(x) for x in toks)
        vary = {k for k in range(L) if len({x[k] if k < len(x) else None for x in toks}) > 1}
        for p, x in zip(ps, toks):
            ws = sorted({x[k] for k in vary if k < len(x) and x[k]}, key=len, reverse=True)
            rx = re.compile("|".join(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])" for w in ws)) if ws else None
            out[p] = (t, rx, len(ps))
    return out


def check(bg, raw, landing=None, replica="all", bus="part", limit=40):
    """G0 R8: [(severity, message)] + stats.  landing = {member id: landed depth} or None (use landed_stages)."""
    bg, landed_found = landed_bundles(bg)
    N, uf, used = classes(bg, raw, replica, bus)
    msgs = []

    def dep(g, m):
        if landing is not None:
            return landing.get(mkey(g, m), m["bound_stages"])
        return m.get("landed_stages", m["bound_stages"])
    # (1) bus groups: one offset; (3) no as-built order inversion
    bad_g = inv = 0
    buses = _group(N, lambda n: n[0])
    for k, ns in buses.items():
        g = ns[0][1]
        ms = [m for _, _, m in ns]
        offs = {dep(g, m) - m["asbuilt_stages"] for m in ms}
        if len(offs) > 1:
            bad_g += 1
            if bad_g <= limit:
                d = sorted({(m["sink_port"], m["asbuilt_stages"], dep(g, m)) for m in ms})
                msgs.append(("ERROR", f"R8 bus group {g['sink']} <- {g['src_part']} ({g['sink_part']}): unequal added "
                             f"delay {sorted(offs)}; (port, as-built, landed) {d[:6]}"))
        for a in ms:
            hit = next((b for b in ms if a["asbuilt_stages"] < b["asbuilt_stages"] and dep(g, a) > dep(g, b)), None)
            if hit is not None:
                inv += 1
                if inv <= limit:
                    msgs.append(("ERROR", f"R8 order inversion {g['sink']} ({g['sink_part']}): {a['sink_port']} led "
                                 f"{hit['sink_port']} as built ({a['asbuilt_stages']} < {hit['asbuilt_stages']}) but "
                                 f"lands after it ({dep(g, a)} > {dep(g, hit)})"))
    # (2) replica sets: every sink partition fed at one as-built depth lands at one offset
    by_src = defaultdict(list)
    for gi, g, m in N:
        by_src[(m["source"], g["sink_part"], m["asbuilt_stages"])].append(dep(g, m) - m["asbuilt_stages"])
    pt = part_types(raw)
    bad_r = 0
    for r in bg.get("replica", []):
        parts = r["sink_parts"]
        sets = [parts] if replica == "all" else [
            ps for ps in _group(parts, lambda p: pt.get(p, p)).values() if len(ps) > 1]
        for ps in sets:
            per = {p: sorted(set(by_src.get((r["source"], p, r["asbuilt_stages"]), []))) for p in ps}
            if len({x for v in per.values() for x in v}) > 1:
                bad_r += 1
                if bad_r <= limit:
                    msgs.append(("ERROR", f"R8 replica {r['source']} (as-built {r['asbuilt_stages']}): unequal added "
                                 f"delay per sink partition {per}"))
    # types hardened once: instances of one type need identical landing pads
    bad_t = 0
    if True:
        tn = type_norm(raw)
        want = defaultdict(lambda: defaultdict(set))
        for gi, g, m in N:
            t, rx, n = tn.get(g["sink_part"], (g["sink_part"], None, 1))
            if n < 2:
                continue
            norm = (rx.sub("*", g["sink"]) if rx else g["sink"], m["sink_port"], str(m["sink_bits"]),
                    rx.sub("*", m["source"]) if rx else m["source"], m["asbuilt_stages"])
            want[t][norm].add(dep(g, m) - m["bound_stages"])
        for t, d in sorted(want.items()):
            conf = {k: sorted(v) for k, v in d.items() if len(v) > 1}
            if conf:
                bad_t += 1
                k, v = next(iter(sorted(conf.items())))
                msgs.append(("ERROR", f"R8 type {t}: instances need different landing pads at {len(conf)} sites "
                             f"(e.g. {k[0]}.{k[1]} <- {k[3]}: pads {v}); a type is hardened once: split the type or "
                             "re-plan the cut so the replicas see equal lane depth"))
    nl = len(landed_found)
    over = [f for f in landed_found if not f["ok"]]
    for f in over[:limit]:
        msgs.append(("WARN" if f["collapsed"] else "ERROR", f"R8 landed bundle {f['sink']} <- {f['src_part']}: as-built per-lane skew "
                     f"{f['skew_stages']} stages = {f['skew_cycles']} cycles > landing window margin {f['margin']} "
                     + ("(collapsed by --landed-over-margin collapse: the as-built bundle could not land coherently, "
                        "the plan delivers it word-aligned)" if f["collapsed"] else
                        "(kept per-lane; the as-built bundle cannot land coherently: re-plan or rule)")))
    stats = dict(groups=len(buses), groups_unequal=bad_g, inversions=inv,
                 landed_bundles=nl, landed_over_margin=len(over),
                 replica_sets=len(bg.get("replica", [])), replica_unequal=bad_r, types_conflicting=bad_t,
                 replica_mode=replica, bus_mode=bus, async_skipped=sum(
                     1 for g in bg["landing"] for m in g["members"] if is_async(m)), depth_source="landing file" if landing is not None else "bus_groups landed_stages")
    return msgs, stats


def _group(xs, key):
    out = defaultdict(list)
    for x in xs:
        out[key(x)].append(x)
    return out


def bg_digest(bg):
    return hashlib.sha256(json.dumps(bg, sort_keys=True).encode()).hexdigest()[:16]


def load_landing(path):
    js = json.loads(Path(path).read_text())
    return {m["id"]: m["landed"] for m in js["members"]}, js


def rebase(bg, bind_lat, plan_tab):
    """bus groups bound on an older plan -> the plan being priced: each member's bound depth moves by its lane's cycle
    change (plan_tab[lane].cycles - the bind's plan_cycles for that lane, bind_latency.json `buses`).  As-built depths
    are the netlist's and do not move.  Returns (bus groups copy, stats); members whose lane is in neither table keep
    their bound depth (counted)."""
    was = {b["lane"]: b["plan_cycles"] for b in bind_lat.get("buses", []) if b.get("lane") is not None}
    out = json.loads(json.dumps(bg))
    st = dict(members=0, moved=0, kept_no_lane=0, max_shift=0, min_shift=0)
    for g in out.get("landing", []):
        for m in g["members"]:
            st["members"] += 1
            ln = m.get("lane")
            if ln not in was or ln not in plan_tab:
                st["kept_no_lane"] += 1
                continue
            d = plan_tab[ln]["cycles"] - was[ln]
            m["bound_stages"] += d
            st["moved"] += bool(d)
            st["max_shift"], st["min_shift"] = max(st["max_shift"], d), min(st["min_shift"], d)
    return out, st


def lane_fold(members, lanes):
    """R8 landing pads folded per plan lane: {lane: dict(r8_pad, r8_pad_min, r8_members, r8_padded)}.  A lane's word is
    usable when its LAST member lands, so the lane's pad = the largest member pad on it (members of one lane share its
    bound depth: landed = lane cycles + pad).  Lanes not in `lanes` (UNPLANNED bind paths) come back as `other`."""
    out, other = {}, {}
    for m in members:
        ln = m.get("lane")
        if ln is None:
            continue
        d = (out if ln in lanes else other).setdefault(ln, dict(r8_pad=0, r8_pad_min=None, r8_members=0, r8_padded=0))
        d["r8_pad"] = max(d["r8_pad"], m["pad"])
        d["r8_pad_min"] = m["pad"] if d["r8_pad_min"] is None else min(d["r8_pad_min"], m["pad"])
        d["r8_members"] += 1
        d["r8_padded"] += bool(m["pad"])
    return out, other


def configure(exempt=(), landed=(), window=4, stage_cycles=0.5, over="keep"):
    """set the module options (the CLI flags of `pads` / `check`)"""
    EXEMPT[:] = [re.compile(x) for x in exempt]
    LANDED.update(rx=[re.compile(x) for x in landed], window=window, stage_cycles=stage_cycles, over=over)


def write_pads(raw, bg, out_dir, replica="all", bus="part"):
    mem, used = solve(bg, raw, replica, bus)
    sm = summary(bg, mem, used)
    lf = landed_bundles(bg)[1]
    sm.update(landed_bundles=len(lf), landed_over_margin=sum(1 for f in lf if not f["ok"]))
    die = raw["die"]["name"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for m in mem:
        m.pop("cls")
    js = dict(schema=SCHEMA, die=die, replica=replica, bus=bus, exempt=[x.pattern for x in EXEMPT], bus_groups_die=bg.get("die"),
              landed=dict(rx=[x.pattern for x in LANDED["rx"]], window=LANDED["window"],
                          stage_cycles=LANDED["stage_cycles"], over_margin=LANDED["over"]),
              bus_groups_digest=bg_digest(bg),
              note="R8 landing pads (tools/die_plan/r8.py): pad = cycles added at the sink landing (after the sink "
                   "partition's in boundary flop, on the bits that leaf consumes) so every bus group and replica set "
                   "lands at ONE added delay; landed = bound + pad is the depth the compiler schedules",
              summary=sm, members=mem)
    p = out_dir / f"{die}_r8_landing.json"
    p.write_text(json.dumps(js, indent=0) + "\n")
    return p, sm


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("pads", "check"):
        a = sub.add_parser(n)
        a.add_argument("plan")
        a.add_argument("bus_groups")
        a.add_argument("--replica", choices=("all", "type"), default="all")
        a.add_argument("--bus", choices=("part", "leaf"), default="part")
        a.add_argument("--exempt", action="append", default=[],
                       help="regex on the source pin / sink port name: members outside R8 (sticky fault flags)")
        a.add_argument("--landed", action="append", default=[],
                       help="regex on the member's plan lane id: lanes of a forwarded-clock landed bundle (one K)")
        a.add_argument("--landed-window", type=int, default=4, help="landing ring depth D (window D cycles)")
        a.add_argument("--landed-stage-cycles", type=float, default=0.5,
                       help="cycles per as-built relay stage of a landed lane (HC1 half-cycle stations: 0.5)")
        a.add_argument("--landed-over-margin", choices=("keep", "collapse"), default="keep",
                       help="a landed bundle over the window margin: keep per-lane depths (ERROR) or collapse (WARN)")
        if n == "pads":
            a.add_argument("--out")
        else:
            a.add_argument("--landing")
            a.add_argument("--json")
    a = ap.parse_args(argv)
    configure(a.exempt, a.landed, a.landed_window, a.landed_stage_cycles, a.landed_over_margin)
    raw = S.load(a.plan)
    bg = json.loads(Path(a.bus_groups).read_text())
    if a.cmd == "pads":
        p, sm = write_pads(raw, bg, a.out or str(Path(a.plan).resolve().parent / "gen"), a.replica, a.bus)
        print(f"{p}: {json.dumps(sm)}")
        return 0
    landing = load_landing(a.landing)[0] if a.landing else None
    msgs, st = check(bg, raw, landing, a.replica, a.bus)
    for sev, m in msgs:
        print(f"{sev} {m}")
    ok = not any(s == "ERROR" for s, _ in msgs)
    print(f"R8 {'PASS' if ok else 'FAIL'} {json.dumps(st)}")
    if a.json:
        Path(a.json).write_text(json.dumps(dict(pass_=ok, stats=st, messages=[m for _, m in msgs]), indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
