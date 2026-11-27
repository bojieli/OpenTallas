#!/usr/bin/env python3
"""tap_cohort_assign.py -- C-TAP-REACH per-cohort tap assignment (default OFF: a standalone tool, no flow calls it).

Why: neither the plan sink model nor the placed-bin nearest-tap model (tap_derive) predicts what CTS builds (k5 201 vs 482 um,
turn 194 vs 485 um); CTS clusters sinks by load, so a tap's assigned-sink box (OT_TAP_SPAN = W + H) can exceed 300 um.  The plan has
one mechanism that pins sinks to taps before CTS: clock.tap_group {re, fixed_taps} (gen_phys.tap_group_exports -> OT_TAP_GROUP_RE /
OT_TAP_GROUP_FIXED; capture 1 of `re` = cohort key; a key not in fixed_taps goes to the tap nearest its centroid).  This tool derives
fixed_taps from the PLACED sinks (sink_bins_from_place dump: net inst master x y, um; instance names are kept RAW, escapes included).

    tap_cohort_assign.py PLAN TYPE SINKS.tsv [--reach 250] [--span 300] [--cap 1200] [--min-cohort 2] [--add-taps ROUNDS]
                         [--density-radii R1,R2,..] [--tools DIR] [--out PLAN2] [--report R.json]

Cohorts.  key(inst) = the path before the first '/'; a name without '/' (flat '.' hierarchy) has no cohort unit and is a single, and a regex
that would capture such a descendant of a key is REFUSED (exit 4: the tool is for '/'-hierarchy types).  Only SAFE keys (gen_phys:
[A-Za-z0-9_./-]+, not a u_rrl_<n> reset relay, which must keep following its sinks) can be pinned; the rest are singles.  The group regex is
^(k1|k2|..)[/.] with the keys longest-first; EVERY instance is assigned to its cohort by that very regex (so model == what CTS sees);
a key with fewer than --min-cohort members after that is dropped, repeated until stable.
With --split-oversize (default off) a cohort whose own box W+H exceeds --span (not pinned by the plan) is SPLIT: demoted to singles on their nearest taps (reported as split_cohorts); no tap site can hold it whole.
Model, in order: (1) singles (ungrouped sinks) go to their TRUE nearest tap, as CTS does, no feasibility test; (2) pinned cohorts of the plan
(tap_group.fixed_taps) keep their tap and are only CHECKED; (3) the other cohorts, largest first, take the nearest feasible tap to their
centroid: every sink within --reach, tap box W+H <= --span, load <= --cap.  A cohort with no feasible tap is UNASSIGNED; with --add-taps
(explicit / grid / grid+explicit types) a tap is added per cluster of unassigned items and the pass repeats.  Exit 0 only when nothing is
unassigned, every pinned cohort is feasible and no tap box exceeds --span or --cap (default the plan's tap_max_sinks); later CTS passes (pinreg, chain /
pair / reset affinity, landing seam, relay cohort, reset split, hop latches) are NOT modelled and are listed in the report as unmodelled_passes; exit 2 unassigned, 3 pinned/over-span violations, 4 refused form, 5 reset freeze failed (nothing written unless --no-freeze).
Plan write (--out): fixed_taps merged (plan pins win), `re` extended only when the plan's own re has the form ^(a|b)[/.] (else refused);
a type that had no tap_group gets follow_re "" (group mode otherwise switches the u_rrl_ follower pass on, gen_phys 4612).
Compose with tap_reach_fix (adds taps for seats beyond the radius) when the report asks for new taps the mode cannot add.
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

SAFE = re.compile(r"[A-Za-z0-9_./-]+")
LITERAL = re.compile(r"(?:[A-Za-z0-9_/-]|\\[.-])+")      # a pure literal alternative: safe chars, escaped . or - only
RE_FORM = re.compile(r"^\^\(([^()]*)\)\[/\.\]$")


def read_sinks(path):
    rows = []
    for ln in Path(path).read_text().splitlines():
        p = ln.split("\t")
        if len(p) >= 5:
            rows.append((p[1], float(p[3]), float(p[4])))
    return rows


RELAY = re.compile(r"u_rrl_\d+$")      # reset relays follow their sinks (clock_taps.tcl ct_follow): never pinned


def raw_key(inst):
    """cohort key = the path before the first '/'.  A name without '/' (flat '.' hierarchy) has no safe cohort unit: it is a single."""
    return inst.split("/", 1)[0] if "/" in inst else inst


def group_re(keys):
    return "^(" + "|".join(re.escape(k) for k in sorted(keys, key=lambda k: (-len(k), k))) + ")[/.]"


def cohorts_of(sinks, min_cohort=2, forced=(), exclude=()):
    """-> {key: [(x, y, inst)]} by the final regex (longest key first) + the list of singles [(x, y, inst)]."""
    keys = set(forced)
    for inst, _, _ in sinks:
        k = raw_key(inst)
        if "/" in inst and SAFE.fullmatch(k) and not RELAY.fullmatch(k) and k not in exclude:
            keys.add(k)
    for _ in range(4):
        rx = re.compile(group_re(keys)) if keys else None
        coh = collections.defaultdict(list)
        for inst, x, y in sinks:
            m = rx.match(inst) if rx else None
            if m:
                coh[m.group(1)].append((x, y, inst))
        drop = {k for k in keys if k not in forced and len(coh.get(k, ())) < min_cohort}
        if not drop:
            break
        keys -= drop
    members = {i for v in coh.values() for _, _, i in v}
    singles = [(x, y, i) for i, x, y in sinks if i not in members]
    swallowed = [i for k, v in coh.items() for _, _, i in v if raw_key(i) != k]     # regex captures an instance outside its own '/' cohort
    return dict(coh), singles, swallowed


def box_wh(pts):
    return (max(x for x, _ in pts) - min(x for x, _ in pts)) + (max(y for _, y in pts) - min(y for _, y in pts)) if pts else 0.0


def assign(sinks, taps, reach=250.0, span=300.0, cap=1200, min_cohort=2, pinned=None, re_keys=(), split_oversize=False):
    """-> dict(fixed, singles, per_tap, unassigned, pinned_bad, single_far).  taps [(name, x, y)], pinned {key: tap}."""
    pinned = dict(pinned or {})
    forced_keys = list(pinned) + list(re_keys or ())
    coh, singles, swallowed = cohorts_of(sinks, min_cohort, forced=[k for k in forced_keys if SAFE.fullmatch(k)])
    split = []                                   # (only with split_oversize) an unpinned cohort whose OWN box W+H exceeds span cannot sit on one tap: demote it
    if split_oversize:
        excl = set()
        forced_set = set(forced_keys)
        for _ in range(4):                       # re-run the regex membership after every demotion: a shorter key may now capture the sinks
            bad = sorted(k for k in coh if k not in forced_set and k not in excl and box_wh([(x, y) for x, y, _ in coh[k]]) > span)
            if not bad:
                break
            for key in bad:
                split.append(dict(cohort=key, sinks=len(coh[key]), box_wh=round(box_wh([(x, y) for x, y, _ in coh[key]]), 1), insts=sorted(i for _, _, i in coh[key])))
            excl |= set(bad)
            coh, singles, swallowed = cohorts_of(sinks, min_cohort, forced=[k for k in forced_keys if SAFE.fullmatch(k)], exclude=excl)
    tapxy = {n: (x, y) for n, x, y in taps}
    box = {n: None for n in tapxy}

    def merged(name, members):
        b = box[name]
        xs = [x for x, _, _ in members]; ys = [y for _, y, _ in members]
        if b is None:
            return [min(xs), max(xs), min(ys), max(ys), len(members)]
        return [min(b[0], *xs), max(b[1], *xs), min(b[2], *ys), max(b[3], *ys), b[4] + len(members)]

    def far(name, members):
        tx, ty = tapxy[name]
        return any(abs(x - tx) + abs(y - ty) > reach for x, y, _ in members)

    def feasible(name, members):
        if far(name, members):
            return False
        b = merged(name, members)
        return b[4] <= cap and (b[1] - b[0]) + (b[3] - b[2]) <= span

    def put(name, members):
        box[name] = merged(name, members)

    fixed, unassigned, pinned_bad, single_far, single_tap = {}, [], [], [], {}
    for x, y, inst in sorted(singles, key=lambda s: s[2]):          # (1) singles on their true nearest tap
        n = min(tapxy, key=lambda t: (abs(tapxy[t][0] - x) + abs(tapxy[t][1] - y), tap_order(t)))
        put(n, [(x, y, inst)])
        single_tap[inst] = n
        if far(n, [(x, y, inst)]):
            single_far.append(inst)
    for key, tap in sorted(pinned.items()):                          # (2) pinned cohorts: kept, checked
        if tap not in tapxy:
            pinned_bad.append(dict(cohort=key, tap=tap, reason="tap not in the type's tap set"))
            continue
        if key not in coh:
            continue
        if far(tap, coh[key]):
            pinned_bad.append(dict(cohort=key, tap=tap, reason="a sink is beyond reach of its pinned tap"))
        put(tap, coh[key])
        fixed[key] = tap
    todo = sorted((k for k in coh if k not in fixed), key=lambda k: (-len(coh[k]), -box_wh([(x, y) for x, y, _ in coh[k]]), k))
    for key in todo:                                                 # (3) the rest, largest first
        m = coh[key]
        cx, cy = sum(x for x, _, _ in m) / len(m), sum(y for _, y, _ in m) / len(m)
        order = sorted(tapxy, key=lambda n: (abs(tapxy[n][0] - cx) + abs(tapxy[n][1] - cy), tap_order(n)))
        pick = next((n for n in order if feasible(n, m)), None)
        if pick is None:
            unassigned.append(dict(cohort=key, sinks=len(m), box_wh=round(box_wh([(x, y) for x, y, _ in m]), 1)))
            continue
        put(pick, m)
        fixed[key] = pick
    over = {n: round((b[1] - b[0]) + (b[3] - b[2]), 1) for n, b in box.items() if b and (b[1] - b[0]) + (b[3] - b[2]) > span}
    per_tap = {n: dict(load=b[4], box_wh=round((b[1] - b[0]) + (b[3] - b[2]), 1)) for n, b in box.items() if b}
    over_cap = {n: b[4] for n, b in box.items() if b and b[4] > cap}
    return dict(fixed=fixed, singles=single_tap, split_cohorts=split, members={k: v for k, v in coh.items()}, swallowed=swallowed, over_cap=over_cap, per_tap=per_tap, unassigned=unassigned, pinned_bad=pinned_bad,
                single_far=single_far, over_span=over, cohorts=len(coh), unpinnable=sum(1 for i, _, _ in sinks if not SAFE.fullmatch(raw_key(i))))


def propose_sites(sinks, unassigned, taps, reach, legalize, members=None):
    """one new tap per cluster of unassigned items (farthest-first; within 0.6*reach of a site proposed this round -> next round).
    A cohort's site is its median sink point; a single (cohort = instance name) its own point."""
    pos = collections.defaultdict(list)
    for inst, x, y in sinks:
        pos[inst].append((x, y))
    for k, v in (members or {}).items():                       # a cohort's points = its regex members
        pos[k] = [(x, y) for x, y, _ in v]
    out, taken = [], [(x, y) for _, x, y in taps]
    for u in sorted(unassigned, key=lambda u: -u["sinks"]):   # stable: callers pass a deterministic farthest-first order
        p = pos[u["cohort"]]
        mx, my = sorted(q[0] for q in p)[len(p) // 2], sorted(q[1] for q in p)[len(p) // 2]
        if any(abs(mx - x) + abs(my - y) <= 0.6 * reach for x, y in out):
            continue
        x, y = legalize(mx, my, taken + out)
        out.append((round(x, 3), round(y, 3)))
    return out


def overspan_items(sinks, taps, res):
    """singles sit on their true nearest tap (CTS), so a tap whose box is over span is cured by a NEW tap near its far singles:
    for every over-span tap, its singles farther than half the tap's box from it (farthest first, at most 8) become items."""
    xy = {n: (x, y) for n, x, y in taps}
    pos = {i: (x, y) for i, x, y in sinks}
    out = []
    for tap in res["over_span"]:
        mine = sorted((i for i, t in res["singles"].items() if t == tap),
                      key=lambda i: -(abs(pos[i][0] - xy[tap][0]) + abs(pos[i][1] - xy[tap][1])))
        out += [dict(cohort=i, sinks=1) for i in mine[:8]]
    return out


def split_report(split, singles):
    """per split cohort: the taps its sinks ended on, the share on the majority tap, and a PROXY for related launch/capture pairs cut by the
    split: name-adjacent instances (sorted order, e.g. consecutive bit/stage flops) that sit on different taps.  The real related pairs need the
    netlist (UNMEASURED here); a cohort exists because its flops are related, so any cut pair trades span for related-pair skew."""
    out = []
    for e in split:
        taps = [singles.get(i) for i in e["insts"]]
        cnt = collections.Counter(t for t in taps if t)
        cut = sum(1 for a, b in zip(taps, taps[1:]) if a != b)
        out.append(dict(cohort=e["cohort"], sinks=e["sinks"], box_wh=e["box_wh"], taps_used=len(cnt),
                        majority_tap_share=round(max(cnt.values()) / max(1, e["sinks"]), 3) if cnt else 0.0,
                        adjacent_pairs_on_different_taps_PROXY=cut, adjacent_pairs=max(0, len(taps) - 1), related_pairs="UNMEASURED (needs netlist)",
                        alternative="reshape the cohort's seat so its own box W+H <= span (plan side: PART for u_cland_*, CASEAM for stations/rings/bins); not done by this tool"))
    return out


def tap_order(name):
    """tie-break key: 'clk' = 0, clk_t<n> = n (numeric, so a renumbering across a digit boundary cannot flip a tie), others last by name"""
    m = re.fullmatch(r"clk(?:_t(\d+))?", name)
    return (0, int(m.group(1) or 0), name) if m else (1, 0, name)


def next_tap_index(taps):
    n = [int(m.group(1)) for t, _, _ in taps for m in [re.fullmatch(r"clk_t(\d+)", t)] if m]
    return (max(n) + 1) if n else len(taps)


class Refused(Exception):
    pass


def tap_group_of(clock, fixed):
    """-> new tap_group.  Plan pins win; re is extended only from the form ^(a|b)[/.]; a fresh group gets follow_re ''."""
    old = clock.get("tap_group")
    merged = dict(fixed)
    if old:
        m = RE_FORM.match(old.get("re", ""))
        if not m:
            raise Refused(f"existing tap_group.re {old.get('re')!r} is not of the form ^(a|b)[/.]: refusing to extend it")
        merged.update(old.get("fixed_taps") or {})
        keys = {k for k in re.split(r"(?<!\\)\|", m.group(1)) if k} | set(merged)
        keys = {re.sub(r"\\(.)", r"\1", k) for k in keys}
        group = dict(old)
    else:
        keys = set(merged)
        group = {"follow_re": ""}
    if not keys:
        raise Refused("nothing to pin: not writing an empty tap_group")
    bad = [k for k in keys if not SAFE.fullmatch(k)]
    if bad or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t) for t in merged.values()):
        raise Refused(f"unsafe group or tap name: {bad[:3]}")
    group["re"] = group_re(keys)
    group["fixed_taps"] = {k: merged[k] for k in sorted(merged)}
    if "tap_cohort_assign" not in group.get("note", ""):
        group["note"] = (group.get("note", "") + " | C-TAP-REACH tap_cohort_assign").strip(" |")
    return group


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("type"); ap.add_argument("sinks")
    ap.add_argument("--reach", type=float, default=250.0); ap.add_argument("--span", type=float, default=300.0)
    ap.add_argument("--cap", type=int, default=None, help="per-tap load cap (default: the type's clock.tap_max_sinks, else 1200)"); ap.add_argument("--min-cohort", type=int, default=2)
    ap.add_argument("--split-oversize", action="store_true",
                    help="default OFF: an unpinned cohort whose own box W+H exceeds --span is demoted to singles on their nearest taps; this cuts related pairs "
                         "(see split_cohorts in the report) - the alternative is reshaping the cohort's seat")
    ap.add_argument("--no-freeze", action="store_true",
                    help="opt out of the RESET-KEY freeze (logged in the report and on stderr): by default, when taps are appended, the BASE taps are first "
                         "recorded as type.reset.consumer_sites_um via reach_fix._freeze_reset_consumers so no reset relay moves and the bound reset RTL stays valid")
    ap.add_argument("--out"); ap.add_argument("--report")
    ap.add_argument("--tools", help="tools/die_plan dir to import schema / tap_split from (default: beside this file); density types read their sink bins relative to that tree")
    ap.add_argument("--density-radii", metavar="R1,R2,...",
                    help="density types: try each clock.tap_radius_um (largest first) on a copy of the plan, take schema.tap_grid and run the same pass; first radius with nothing unassigned wins")
    ap.add_argument("--add-taps", type=int, default=0, metavar="ROUNDS",
                    help="explicit / grid / grid+explicit types: add a tap per cluster of unassigned items (legalized as tap_derive does) and re-assign, up to ROUNDS times")
    a = ap.parse_args(argv)
    here = Path(a.tools).resolve() if a.tools else Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    import schema
    import tap_split
    raw = json.loads(Path(a.plan).read_text())
    clock = raw["partition_types"][a.type]["clock"]
    mode = clock.get("tap_mode", "grid")
    if mode not in ("explicit", "grid", "grid+explicit", "density") or raw["partition_types"][a.type].get("hard"):
        print(f"REFUSED: tap_mode {mode!r} / hard type is not modelled", file=sys.stderr)
        return 4
    plan = schema.Plan(raw, str(Path(a.plan).resolve()))
    if mode == "density":
        taps = [(n, float(x), float(y)) for n, x, y in schema.tap_grid(plan, a.type)]
    else:
        taps, _ = tap_split.type_taps(schema, plan, clock, a.type)
    sinks = read_sinks(a.sinks)
    if not taps:
        print("REFUSED: the type has no taps", file=sys.stderr)
        return 4
    tg = clock.get("tap_group") or {}
    pinned = tg.get("fixed_taps") or {}
    re_keys = []
    if tg:
        m = RE_FORM.match(tg.get("re", ""))
        if not m:
            print(f"REFUSED: existing tap_group.re {tg.get('re')!r} is not of the form ^(a|b)[/.]; the model cannot reproduce it", file=sys.stderr)
            return 4
        alts = [k for k in re.split(r"(?<!\\)\|", m.group(1)) if k]
        if any(not LITERAL.fullmatch(k) for k in alts):
            print(f"REFUSED: existing tap_group.re has non-literal alternatives {[k for k in alts if not LITERAL.fullmatch(k)][:3]}; the model treats keys as literals", file=sys.stderr)
            return 4
        re_keys = [re.sub(r"\\(.)", r"\1", k) for k in alts]
    cap = a.cap if a.cap is not None else int(clock.get("tap_max_sinks") or 1200)
    a.cap = cap
    unmodelled = sorted(k for k in ("pinreg_taps", "tap_chain_affinity", "tap_landing_seam", "tap_relay_cohort", "tap_reset_split",
                                     "tap_reset_affinity", "tap_pair_affinity") if clock.get(k))
    kw = dict(reach=a.reach, span=a.span, cap=cap, min_cohort=a.min_cohort, pinned=pinned, re_keys=re_keys, split_oversize=a.split_oversize)
    res = assign(sinks, taps, **kw)
    radius, added = None, []
    if a.density_radii and mode == "density" and res["unassigned"]:
        import copy
        for r in sorted((float(v) for v in a.density_radii.split(",")), reverse=True):
            raw2 = copy.deepcopy(raw)
            raw2["partition_types"][a.type]["clock"]["tap_radius_um"] = r
            plan2 = schema.Plan(raw2, str(Path(a.plan).resolve()))
            taps2 = [(n, float(x), float(y)) for n, x, y in schema.tap_grid(plan2, a.type)]
            r2 = assign(sinks, taps2, **dict(kw, reach=min(a.reach, r + 50)))
            print(f"density radius {r}: taps {len(taps2)} unassigned {len(r2['unassigned'])} (reach {min(a.reach, r + 50)})", file=sys.stderr)
            if not r2["unassigned"]:
                taps, res, radius = taps2, r2, r
                break
    if a.add_taps and (res["unassigned"] or res["over_span"] or res["single_far"]) and mode != "density":
        tile = plan.types[a.type]
        explicit = mode == "explicit"
        core = [(x, y) for _, x, y, _ in schema.core_taps(plan, a.type)] if explicit else []

        def legalize(x, y, taken):
            if explicit:
                return tap_split.explicit_legalize(tile, x, y, taken + core)
            return schema.tap_clear(tile, x, y, taken, strict=True)[:2]
        for _ in range(a.add_taps):
            items = list(res["unassigned"]) + overspan_items(sinks, taps, res) + [dict(cohort=i, sinks=1) for i in res["single_far"]]
            if not items:
                break
            new = propose_sites(sinks, items, taps, a.reach, legalize, res["members"])
            if not new:
                break
            base = next_tap_index(taps)
            taps = taps + [(f"clk_t{base + i}", x, y) for i, (x, y) in enumerate(new)]
            added += [dict(name=f"clk_t{base + i}", xy=[x, y]) for i, (x, y) in enumerate(new)]
            res = assign(sinks, taps, **kw)
    if added:
        # drop added taps that ended up with no sink (empty taps are a CTS padding problem) and RENUMBER the survivors consecutively
        # (the bind needs consecutive clk_t<n>); the geometry is unchanged, so the assignment is re-run and must give the same verdict
        used = set(res["per_tap"])
        keep = [t for t in added if t["name"] in used]
        if len(keep) != len(added):
            base0 = next_tap_index(taps[: len(taps) - len(added)])
            ren = {t["name"]: f"clk_t{base0 + i}" for i, t in enumerate(keep)}
            keep = [dict(name=ren[t["name"]], xy=t["xy"]) for t in keep]
            taps = [t for t in taps[: len(taps) - len(added)]] + [(t["name"], t["xy"][0], t["xy"][1]) for t in keep]
            res2 = assign(sinks, taps, **kw)
            assert (len(res2["unassigned"]), sorted(res2["over_span"]), len(res2["single_far"]), len(res2["over_cap"])) == \
                   (len(res["unassigned"]), sorted(ren.get(n, n) for n in res["over_span"]), len(res["single_far"]), len(res["over_cap"])), "renumber changed the verdict"
            res = res2
        added = keep
    rep = dict(type=a.type, mode=mode, reach_used=(min(a.reach, radius + 50) if radius is not None else a.reach),
               unmodelled_always=["tap_relay_cohort (default on for s81), r_dly_lockup chain affinity, tap_post_merge_min_sinks / tap_cap_cascade / tap_spill_um, hop-latch capture, "
                                  "follower pass of an existing group without follow_re, macro clock pins under a pinned key (the sink dump skips isBlock masters)"], taps=len(taps), added_taps=added, tap_radius_um=radius, sinks=len(sinks), cohorts=res["cohorts"],
               pinned=len(res["fixed"]), singles=len(res["singles"]), split_cohorts=split_report(res["split_cohorts"], res["singles"]), unpinnable_sinks=res["unpinnable"], unassigned=res["unassigned"],
               pinned_bad=res["pinned_bad"], over_cap=res["over_cap"], swallowed_sinks=len(res["swallowed"]), unmodelled_passes=unmodelled, single_beyond_reach=len(res["single_far"]), over_span=res["over_span"],
               max_box_wh=max((v["box_wh"] for v in res["per_tap"].values()), default=0.0), per_tap=res["per_tap"],
               caps=dict(reach=a.reach, span=a.span, cap=a.cap))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("per_tap",)}))
    if res["swallowed"]:
        print(f"REFUSED: the group regex would also capture {len(res['swallowed'])} sinks outside their own '/' cohort (flat names)", file=sys.stderr)
        return 4
    if res["unassigned"]:
        print("UNASSIGNED cohorts: the type needs a new tap site; nothing written", file=sys.stderr)
        return 2
    if res["pinned_bad"] or res["over_span"] or res["single_far"] or res["over_cap"]:
        print("VIOLATIONS (pinned cohort infeasible / tap box over span / over cap / single beyond reach); nothing written", file=sys.stderr)
        return 3
    if a.out:
        tg = None
        if res["fixed"] or clock.get("tap_group"):                 # nothing to pin and no group yet: only the added taps are written
            try:
                tg = tap_group_of(clock, res["fixed"])
            except Refused as exc:
                print(f"REFUSED: {exc}", file=sys.stderr)
                return 4
        freeze = None
        if added and not a.no_freeze:
            import copy
            import reach_fix as RF
            import row_normalize as RN
            tree = Path(a.tools).resolve().parent.parent if a.tools else Path(__file__).resolve().parent.parent.parent
            t0 = copy.deepcopy(raw["partition_types"][a.type]); rec0 = {"changes": []}
            with RN.in_tree(tree):
                RF._freeze_reset_consumers(plan, a.type, t0, rec0)                  # BEFORE the taps are appended: it reads the BASE taps
            sites = (t0.get("reset") or {}).get("consumer_sites_um")
            if sites:
                raw["partition_types"][a.type].setdefault("reset", {})["consumer_sites_um"] = sites
            freeze = dict(frozen=bool(sites), sites=len(sites or []), record=rec0)
            if rec0.get("notes"):                          # the stock step could not read the base taps: appended taps would move the reset tree
                print(f"FREEZE FAILED ({rec0['notes']}): nothing written; fix the plan or pass --no-freeze (the reset tree may then move)", file=sys.stderr)
                if a.report:
                    rp = json.loads(Path(a.report).read_text()); rp["reset_freeze"] = freeze; Path(a.report).write_text(json.dumps(rp, indent=1) + "\n")
                return 5
        elif added:
            print("NO-FREEZE: taps are appended without recording reset.consumer_sites_um; the reset tree may move (landing / DERIVEDNAME findings)", file=sys.stderr)
            freeze = dict(frozen=False, opted_out=True)
        ck = raw["partition_types"][a.type]["clock"]
        if radius is not None:
            ck["tap_radius_um"] = radius
        if added:
            key = "taps" if mode == "explicit" else "added_taps"
            ck[key] = list(ck.get(key) or []) + added
            if mode == "grid":
                ck["tap_mode"] = "grid+explicit"
        if tg is not None:
            ck["tap_group"] = tg
        if a.report and freeze is not None:
            rp = json.loads(Path(a.report).read_text()); rp["reset_freeze"] = freeze; Path(a.report).write_text(json.dumps(rp, indent=1) + "\n")
        Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
