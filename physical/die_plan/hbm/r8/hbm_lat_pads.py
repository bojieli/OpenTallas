"""DIE-HBM-92-LAT 11-08: HBM R8 landing pads + fixed-latency loop equalisation (F1 of the HBM latency event).

The HBM bind (plan 1108d+, bind_d) lands as-built 0-stage buses with plan lanes of unequal depth (273 torn buses,
r8.py check: 303 unequal groups + 157 unequal replica sets), and many HBM consumers capture a response a FIXED number
of edges after their request (LG tap / SU VM bank leaf READ_RETURN, SFU VM bridge READ_RETURN, hc_q DONE_LAT /
RD_CAPTURE, ...).  This tool writes ONE r8 landing table (tools/die_plan/r8.py schema, read by bind.py
asbuilt.land_align = "r8") that, beyond R8 proper, makes every such consumer's round trip a single number:

  1. R8 classes (r8.classes, default --replica type --bus part = every input of one sink leaf from one source
     partition lands at one added delay; replicas of one partition type equal) -- the KV/S81 recipe;
  2. contract `joins`: member sets that must land at ONE added delay although they are in different R8 groups
     (e.g. per local group: calendar lg_local_read/write legs == every client's request leg into the LG taps,
     so the tap's as-built "local select arrives with its request" relationship is kept);
     every leg named by a loop is also joined (a leg = one added delay);
  3. contract `loops`: families of round trips that share ONE consumer parameter (e.g. the SFU VM bridge's
     READ_RETURN serves all four local groups): RT_i = sum of its legs' added delays; every loop short of the family
     maximum gets the deficit on its `pad` leg (default: last leg = the return), iterated to a fixpoint.

Pads only ever ADD stages at the sink landing (after the sink partition's in boundary flop): the result is the
smallest uniform added depth consistent with the present plan lanes (no lane gets shorter; reach per cycle is the
plan's).  The table is consumed unchanged by bind.py (R8_STALE / R8_UNCOVERED checks) and by r8.py check.

    python3 hbm_lat_pads.py PLAN.json BUS_GROUPS.json CONTRACT.json --out DIR [--tools TOOLS_DIE_PLAN]
        -> DIR/<die>_r8_landing.json (+ summary.loops: per family / loop the added RT and the parameter delta)
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def load_r8(tools):
    sys.path.insert(0, str(Path(tools).resolve()))
    import r8 as R8  # noqa: E402
    import schema as S  # noqa: E402
    return R8, S


def compile_sel(s):
    return (re.compile(s["sink"]), re.compile(s.get("port", ".*")), re.compile(s.get("src", ".*")))


def match(sel, g, m):
    a, b, c = sel
    return bool(a.fullmatch(g["sink"]) and b.fullmatch(m["sink_port"]) and c.fullmatch(m["source"].rpartition(".")[0]))


def expand(contract):
    """contract templates: {"for": {"q": ["NW","NE"], "k": [0,1,2,3]}, ...} rows are expanded with str.format on every
    string (python format fields {q}, {k}, {b0}={2k}, {b1}={2k+1})."""
    class Keep(dict):
        def __missing__(self, k):
            return "{" + k + "}"

    def subst(x, env):
        if isinstance(x, str):
            return x.format_map(Keep(env))
        if isinstance(x, list):
            return [subst(y, env) for y in x]
        if isinstance(x, dict):
            return {k: subst(v, env) for k, v in x.items() if k != "for"}
        return x

    def envs(spec):
        out = [{}]
        for k, vs in spec.items():
            out = [dict(e, **{k: v}) for e in out for v in vs]
        for e in out:
            if "k" in e:
                e.update(b0=2 * int(e["k"]), b1=2 * int(e["k"]) + 1)
        return out

    def rows(xs):
        res = []
        for r in xs:
            if "for" in r:
                res += [subst(r, e) for e in envs(r["for"])]
            else:
                res.append(r)
        return res
    legs = {}
    for r in rows(contract.get("legs", [])):
        legs[r["name"]] = r
    joins = rows(contract.get("joins", []))
    fams = []
    for f in rows(contract.get("families", [])):
        f = dict(f)
        if "loops_for" in f:
            spec = f.pop("loops_for")
            tmpl = f.pop("loop")
            f["loops"] = [subst(tmpl, dict(e, **{k: v for k, v in f.get("env", {}).items()})) for e in envs(spec)]
        fams.append(f)
    return legs, joins, fams


def apply_splits(bg, contract):
    """contract `splits`: [{name, sel}] -> members matched get bus_sub = name (r8.bus_key): an R8 landing group
    (sink leaf, source partition) is split where two unrelated as-built buses share a sink leaf and a source partition
    (e.g. an LG tap's calendar select and its VM bank return, both from the hub)."""
    bg = json.loads(json.dumps(bg))
    n = defaultdict(int)
    for sp in contract.get("splits", []):
        sels = [compile_sel(x) for x in (sp["sel"] if isinstance(sp["sel"], list) else [sp["sel"]])]
        for g in bg["landing"]:
            for m in g["members"]:
                if any(match(x, g, m) for x in sels):
                    m["bus_sub"] = sp["name"]
                    n[sp["name"]] += 1
    return bg, dict(n)


def solve(bg, raw, contract, R8, replica="type", bus="part"):
    bg, nsplit = apply_splits(bg, contract)
    bg = R8.landed_bundles(bg)[0]
    N, uf, used = R8.classes(bg, raw, replica, bus)
    legs, joins, fams = expand(contract)
    errors = []
    sel_cache = {}

    def nodes_of(selspec, what):
        key = json.dumps(selspec, sort_keys=True)
        if key not in sel_cache:
            sels = [compile_sel(s) for s in (selspec if isinstance(selspec, list) else [selspec])]
            sel_cache[key] = [i for i, (_, g, m) in enumerate(N) if any(match(s, g, m) for s in sels)]
        ids = sel_cache[key]
        if not ids:
            errors.append(f"{what}: selector matches no crossing member: {selspec}")
        return ids
    leg_ids = {n: nodes_of(r["sel"], f"leg {n}") for n, r in legs.items()}
    # a leg = one added delay; a join = one added delay over all its legs / selectors
    for n, ids in leg_ids.items():
        for i in ids[1:]:
            uf.union(ids[0], i)
    for j in joins:
        ids = []
        for x in j["members"]:
            ids += leg_ids[x] if isinstance(x, str) else nodes_of(x, f"join {j['name']}")
        for i in ids[1:]:
            uf.union(ids[0], i)
    off = [m["bound_stages"] - m["asbuilt_stages"] for _, _, m in N]
    extra = defaultdict(int)

    def cmax():
        c = defaultdict(lambda: -10 ** 9)
        for i in range(len(N)):
            r = uf.find(i)
            c[r] = max(c[r], off[i])
        return {r: v + extra[r] for r, v in c.items()}

    def leg_add(cm, name):
        ids = leg_ids[name]
        return cm[uf.find(ids[0])] if ids else None
    rounds = 0
    while True:
        rounds += 1
        cm = cmax()
        moved = False
        for f in fams:
            rts = [sum(leg_add(cm, x) or 0 for x in lp["legs"]) for lp in f["loops"]]
            tgt = max(rts)
            for lp, rt in zip(f["loops"], rts):
                if rt < tgt:
                    pl = lp.get("pad", lp["legs"][-1])
                    extra[uf.find(leg_ids[pl][0])] += tgt - rt
                    moved = True
        if not moved or rounds > 50:
            break
    if rounds > 50:
        errors.append("loop equalisation did not converge")
    cm = cmax()
    mem = []
    for i, (gi, g, m) in enumerate(N):
        c = uf.find(i)
        pad = cm[c] - off[i]
        mem.append(dict(id=R8.mkey(g, m), sink=g["sink"], sink_part=g["sink_part"], src_part=g["src_part"],
                        sink_port=m["sink_port"], sink_bits=m["sink_bits"], source=m["source"],
                        asbuilt=m.get("asbuilt_lane_stages", m["asbuilt_stages"]), bound=m["bound_stages"], pad=pad,
                        **({"asbuilt_lane": m["asbuilt_lane_stages"]} if "asbuilt_lane_stages" in m else {}),
                        **({"asbuilt_group": m["asbuilt_stages"]}
                           if m.get("asbuilt_lane_stages", m["asbuilt_stages"]) != m["asbuilt_stages"] else {}),
                        landed=m["bound_stages"] + pad, cls=c, lane=m.get("lane")))
    rep = []
    for f in fams:
        lps = []
        for lp in f["loops"]:
            adds = {x: leg_add(cm, x) for x in lp["legs"]}
            lps.append(dict(name=lp["name"], legs=adds, rt_added=sum(v or 0 for v in adds.values())))
        rep.append(dict(family=f["name"], consumer=f.get("consumer"), params=f.get("params"),
                        rt_added=sorted({x["rt_added"] for x in lps}), loops=lps))
    legrep = {n: leg_add(cm, n) for n in legs}
    return mem, used, rep, legrep, errors, rounds, nsplit


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("bus_groups")
    ap.add_argument("contract")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tools", default=str(Path(__file__).resolve().parents[4] / "tools" / "die_plan"))
    ap.add_argument("--replica", choices=("all", "type"), default="type")
    ap.add_argument("--bus", choices=("part", "leaf"), default="part")
    a = ap.parse_args(argv)
    R8, S = load_r8(a.tools)
    raw = S.load(a.plan)
    bg = json.loads(Path(a.bus_groups).read_text())
    contract = json.loads(Path(a.contract).read_text())
    mem, used, rep, legrep, errors, rounds, nsplit = solve(bg, raw, contract, R8, a.replica, a.bus)
    sm = R8.summary(bg, mem, used)
    sm.update(loop_rounds=rounds, split_members=nsplit, classes=len({m["cls"] for m in mem}))
    for m in mem:
        m.pop("cls")
    die = raw["die"]["name"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    js = dict(schema=R8.SCHEMA, die=die, replica=a.replica, bus=a.bus, exempt=[], bus_groups_die=bg.get("die"),
              landed=dict(rx=[], window=4, stage_cycles=0.5, over_margin="keep"),
              bus_groups_digest=R8.bg_digest(bg), contract=contract.get("name"),
              note="HBM R8 landing pads + fixed-latency loop equalisation (physical/die_plan/hbm/r8/hbm_lat_pads.py): "
                   "pad = cycles added at the sink landing; landed = bound + pad",
              summary=sm, loops=rep, legs=legrep, errors=errors, members=mem)
    (out / "bus_groups_split.json").write_text(json.dumps(apply_splits(bg, contract)[0], indent=0) + "\n")
    p = out / f"{die}_r8_landing.json"
    p.write_text(json.dumps(js, indent=0) + "\n")
    print(f"{p}: {json.dumps(sm)}")
    for r in rep:
        print(f"LOOP {r['family']}: rt_added {r['rt_added']} " +
              " ".join(f"{x['name']}={x['rt_added']}{list(x['legs'].values())}" for x in r["loops"]))
    for e in errors:
        print(f"ERROR {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
