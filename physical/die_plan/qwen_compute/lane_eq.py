"""QC 10-24 (owner-accepted capacity plan, QC-TOK proposal 19:04): equal lane depth into a hardened type.

A partition type is hardened once, so its R8 landing pads are a TYPE property: every instance of a sink type must see
the same natural depth on a lane family (same destination type + bus), else the instances need different pads (G0 [r8]
"R8 type <t>: instances need different landing pads").  The capacity plan routes the slice fw -> ctl lane x_fw_ctl_p1
E: fw -> su_l1 -> su_c -> sc -> ctl (9 cycles) and W: fw -> stm -> sc -> ctl (6 cycles) into ONE type sle_ctl.

equalise(plan) pads the shorter lanes of every such family up to the family maximum with ft STATIONS (registers spread
along the route, not landing pads at the sink): each extra station goes to a crossed (type, slot) whose every lane in
the plan has the same deficit (a slot is a type property too), the one with the longest estimated hop per station.  The
station count and the flop count equal the pads they replace; the type count and the lanes stay the same.
Families into CB types are left to the CB16 landing pads (bind/cb16_pads.py, owner-accepted CB16 alignment).
Run BEFORE ft_regs (which places the station sites off hard cores and may add stations for routed hops; the caller
re-runs equalise afterwards until nothing moves)."""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import schema  # noqa: E402

SKIP_DST_PREFIX = ("cb",)      # CB16 legs: aligned by the CB16 landing pads (owner decision 1, 10-24)


def _families(P):
    fam = collections.defaultdict(list)
    for lid, ln in P.lanes.items():
        b = P.ports[ln["ports"][-1]]
        if b["dst"]["part"] == schema.DIE_PART:
            continue
        tn = P.parts[b["dst"]["part"]]["type"]
        if tn.startswith(SKIP_DST_PREFIX):
            continue
        fam[(tn, b["dst"]["bus"])].append(lid)
    return fam


def _hop_len(P, a, b):
    pa, pb = P.port_point(a), P.port_point(b)
    return abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])


def equalise(raw, log=print):
    """pad short lanes of every unequal family with ft stations (in place).  Returns a report dict."""
    rep = dict(families_unequal=0, added=[], unfixed=[])
    for _ in range(200):
        P = schema.Plan(raw)
        nat = {lid: P.lane_natural(lid)["cycles"] for lid in P.lanes}
        deficit = {}
        for key, lids in _families(P).items():
            m = max(nat[l] for l in lids)
            for l in lids:
                if nat[l] < m:
                    deficit[l] = (m - nat[l], key)
        if not deficit:
            break
        rep["families_unequal"] = max(rep["families_unequal"], len({k for _, k in deficit.values()}))
        through = collections.defaultdict(set)          # (type, slot) -> lanes crossing it
        cross = {}
        for lid in P.lanes:
            cross[lid] = [(P.parts[p]["type"], s, a, b) for p, s, a, b in P.lane_crossings(lid) if s]
            for tn, s, _, _ in cross[lid]:
                through[(tn, s)].add(lid)
        moved = False
        for lid, (d, key) in sorted(deficit.items()):
            best = None
            for tn, s, a, b in cross[lid]:
                if any(deficit.get(o, (0, None))[0] != d for o in through[(tn, s)]):
                    continue
                slot = next(x for x in P.types[tn]["ft_slots"] if x["name"] == s)
                per = _hop_len(P, a, b) / (int(slot.get("stations", 1)) + 1)
                if best is None or per > best[0]:
                    best = (per, tn, s, slot)
            if best is None:
                rep["unfixed"].append(dict(lane=lid, deficit=d, family=list(key)))
                continue
            _, tn, s, slot = best
            k = int(slot.get("stations", 1))
            if slot.get("regs_um"):
                regs = [tuple(r) for r in slot["regs_um"]]
                i = max(range(len(regs) - 1), key=lambda j: abs(regs[j + 1][0] - regs[j][0]) + abs(regs[j + 1][1] - regs[j][1])) \
                    if len(regs) > 1 else 0
                q = regs[i + 1] if i + 1 < len(regs) else regs[i]
                regs.insert(i + 1, (round((regs[i][0] + q[0]) / 2, 3), round((regs[i][1] + q[1]) / 2, 3)))
                slot["regs_um"] = [list(r) for r in regs]
            slot["stations"] = k + 1
            rep["added"].append(dict(slot=f"{tn}.{s}", stations_from=k, stations_to=k + 1, family=list(key),
                                     lanes=sorted(through[(tn, s)])))
            log(f"lane_eq: {tn}.{s} stations {k} -> {k + 1} (family {key[0]}.{key[1]}, deficit {d}, "
                f"{len(through[(tn, s)])} lanes)")
            moved = True
            break                                   # re-evaluate deficits after every change (slots are shared)
        if not moved:
            break
    P = schema.Plan(raw)
    nat = {lid: P.lane_natural(lid)["cycles"] for lid in P.lanes}
    rep["families_unequal_after"] = sorted({f"{k[0]}.{k[1]}" for k, lids in _families(P).items()
                                            if len({nat[l] for l in lids}) > 1})
    return rep


if __name__ == "__main__":
    path = Path(sys.argv[1])
    raw = json.loads(path.read_text())
    print("lane_eq:", json.dumps(equalise(raw)))
    if "--inplace" in sys.argv:
        path.write_text(json.dumps(raw, indent=1) + "\n")
