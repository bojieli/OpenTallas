#!/usr/bin/env python3
"""derived_drop.py -- PRE classes RSTREACH + DERIVEDNAME (PRECHECK-DERIVED-DROP, COORD 11-23 21:36; FABLE-RC-KV 21:36 ask).

A re-floor, grow or tap rewrite re-solves a type's reset tree / tap table, but the DERIVED plan sections that point into it
(clock.landing_raw_branches, START stage raw resets, landing_local_resets, internal_stations launch / capture names) are not
re-derived by the same step.  Three such drops in one night, each found a bind or a kit later:
  KV A3g (grow +112.32 um): landing_raw_branches stage chains of kv3_io_ft_v1 / kv3_hroot no longer a D-chain of the
      re-solved tree (rst_n_t15 now hangs on rst_rl_58): 2 EMIT errors after a 1080 s bind.
  KV pv (re-floors stripped landing_raw_branches on 15 of 16 pv types with FSTART flops): one relay chain, all 11 stages on
      one site, drives the 11 FSTART face flops over ~2 mm: -721 ps at post-hook CTS (kv3_pv_v3 u_rrl_54).
  S81 c7a step 14 (svc_tap_inv rewrote clock taps on 8 svc_lo types): START raw_reset pointers still name the old taps,
      raw hops up to 2233 um (t1 30, t6 4, t7 43, rs_w 6 over 405).  G0 R-REACH-5 saw them only as WARNINGs.

RSTREACH (FAIL; generic, every die, plan-only):
  a. every START stage raw reset and landing_local_resets raw (reach_rules.raw_hops, the G0 R-REACH-5 measure) exists in the
     plan's reset tree and lies within its edge reach (405 um same edge, 180 um half cycle);
  b. every type with FSTART flops (landing_contract cland_fstart_out_<bus>) has its raw reset within reach of each of them:
     - with clock.landing_raw_branches: each branch's hops base relay -> copies -> its FSTART pin <= 405 um; the FSTART pins
       no branch covers stay on the one cland_start_raw net and are judged as in the next case;
     - without (or for the uncovered pins): the one cland_start_raw relay must reach all of them, so their L1 enclosing
       radius must be <= 405 um; with --elab-dir (a bind of this plan) the bound relay site is used instead (exact), and a
       co-sited chain (all stages on one site) is named.
  The generator default is 300 um (cbc_rules.reset_hop_cap_um); the FAIL line is the CHECK reach 405 (cbc REACH_GATE_UM), so a
  bound plan's recorded reach keeps passing.
DERIVEDNAME (FAIL; generic): every derived name resolves in the current floorplan:
  a. relay / tap names (rst_rl_<k>, rst_n_t<i>, rr_t<i>, clk_t<i>) referenced by the clock section (tap tables and
     collector_tree excluded: they define names) are emitted by the type's reset tree / tap table;
  b. landing_raw_branches are what landing_remap --resets rstnode (LANDREMAP-RSTNODE, the fix) leaves unchanged: run on a copy
     with the remap base (rule 1: finals renumbered since the base) and always rule 2 (each chain a literal D-chain of the
     re-solved tree, the bind's RawBranches EMIT check); anything the pass would change is STALE (COORD ruling 11-23);
  c. branch consumers fstart:<bus> / writer:<bus>:<i> / reader:<bus>:<i>, START branch keys and landing_contract bands name
     an existing FSTART pin / START stage / band;
  d. internal_stations launch / capture 'core:<inst>' and 'leaf <inst>' name an instance of the type's hard_cores / contents.

ENTRYFOOT (WARN, report-only per COORD r703 11-24 -- ENTRYFOOT_LEVEL; generic, PRE-QC-GENCHECK 11-23): an early core tap naming a hard core's clock_entry_access pin emits exactly the
  access footprint (top partition layer, 1e-6 um, on track) -- QC CB-R3 moved u_t00/u_t01 + footprints, not taps clk_c0/clk_c2:
  kit GEN died; with a baseline, every early core tap follows its moved hard core by the same delta; STALE-EXPORT-TAP: every
  forwarded-clock output's source_clock_port tap lies within 300 um of its pin (KV A5: 1457 of 2769 over).  See above CLASSES.

Cost: one reset-tree solve per type that needs one (cached, shared by both classes); OT_DERIVED_BUDGET_S (default 900) bounds
the total, types past it are WARN ... not checked.  OT_DERIVED_TYPES=a,b limits the types.  --skip RSTREACH / DERIVEDNAME.

    python3 -I tools/die_plan/derived_drop.py --plan PLAN [--tree TREE] [--elab-dir BIND_OUT] [--classes RSTREACH,DERIVEDNAME,ENTRYFOOT]
    exit 0 = no FAIL, 1 = FAIL lines, 2 = bad input
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REACH_UM = 405.0             # cbc_rules.REACH_GATE_UM / reach_rules.REACH_UM: the CHECK reach of a registered hop
GEN_UM = 300.0               # cbc_rules.RESET_HOP_CAP_UM: generator default (reported, not judged)
EPS = 0.5
MAX_LIST = 4
RELAY = re.compile(r"^(rst_rl_|rst_n_t|rr_t)(\d+)$")
TAP = re.compile(r"^clk_t\d+$")
SKIP_KEYS = ("collector_tree", "taps", "added_taps", "core_taps")
CONS = re.compile(r"^(origin|fstart:(\w+)|(reader|writer):(\w+):(\d+))$")
FS = "cland_fstart_out_"
BOUND_REL = re.compile(r"ot_dp_rrelay\s+(\w+)\s*\(\.clk\(clk\),\s*\.d\((\w+)\),\s*\.q\((\w+)\)\);\s*//[^\n]*?depth (\d+) "
                       r"@ \(([-\d.]+), ([-\d.]+)\)")


def man(a, b):
    return abs(float(a[0]) - float(b[0])) + abs(float(a[1]) - float(b[1]))


def l1_radius(pts):
    """smallest r such that one point lies within Manhattan distance r of every point (rotated-axis half range)"""
    if len(pts) < 2:
        return 0.0
    u = [p[0] + p[1] for p in pts]
    v = [p[0] - p[1] for p in pts]
    return max(max(u) - min(u), max(v) - min(v)) / 2.0


def fstart_pins(t):
    lc = ((t.get("clock") or {}).get("landing_contract") or {})
    return {p["name"][len(FS):]: tuple(p["xy_um"]) for p in lc.get("pins") or []
            if isinstance(p, dict) and str(p.get("name", "")).startswith(FS) and isinstance(p.get("xy_um"), list)}


def name_refs(t):
    """{plan path: name} of every relay / tap name the clock section references (defining tables excluded)"""
    out = {}

    def walk(o, path):
        items = o.items() if isinstance(o, dict) else enumerate(o) if isinstance(o, list) else ()
        for k, v in items:
            if k in SKIP_KEYS:
                continue
            if isinstance(v, str) and (RELAY.match(v) or TAP.match(v)):
                out[f"{path}/{k}"] = v
            else:
                walk(v, f"{path}/{k}")
    walk((t or {}).get("clock") or {}, "clock")
    return out


class Solver:
    """per-type reset tree / tap table / raw hop answers of the plan as written (cached); tests inject a fake"""

    def __init__(self, raw, plan_path, tree=None):
        self.raw, self.plan_path, self.root = raw, plan_path, tree
        self._P, self._c = None, {}

    def _plan(self):
        if self._P is None:
            sys.path.insert(0, str(HERE))
            import schema
            self._P = schema.Plan(self.raw, Path(self.plan_path).parent / "die_plan.json")
        return self._P

    def _run(self, fn):
        sys.path.insert(0, str(HERE))
        import plan_gate_pre as G
        return G._in_tree(self.root, fn)

    def relays(self, tn):
        """{q: (d, (x, y))} of the type's solved reset tree"""
        if ("r", tn) not in self._c:
            import reset_tree as RT
            T = self._run(lambda: RT.for_type(self._plan(), tn))
            self._c[("t", tn)] = T
            self._c[("r", tn)] = {x["q"]: (x.get("d"), tuple(float(c) for c in x.get("xy") or (0, 0))) for x in T["relays"]}
        return self._c[("r", tn)]

    def tree(self, tn):
        """the full solved reset tree {relays: [{q, d, xy, kind, ...}], ...} (landing_remap's tree form)"""
        self.relays(tn)
        return self._c[("t", tn)]

    def taps(self, tn):
        if ("k", tn) not in self._c:
            import schema
            self._c[("k", tn)] = self._run(lambda: {p[0] for p in schema.tap_grid(self._plan(), tn)})
        return self._c[("k", tn)]

    def broadcast(self):
        if "bc" not in self._c:
            import reset_tree as RT
            try:
                self._c["bc"] = bool(RT.start_broadcast(self._plan()))
            except Exception:  # noqa: BLE001
                self._c["bc"] = None
        return self._c["bc"]

    def repaired(self, tn):
        """plan paths ('clock/<section>/...') the bind re-picks itself (reset_anchor.repicked_paths, the predicate LANDREMAP and
        the bind share: every landing_local_resets raw; every START / local rst_rl_<k> of a type with reset_tree_anchor)"""
        if ("p", tn) not in self._c:
            import reset_anchor as RA
            root = Path(self.root).resolve() if self.root and Path(self.root).is_dir() else HERE.parents[1]
            try:
                paths, _err = self._run(lambda: RA.repicked_paths(tn, self.raw["partition_types"][tn], self.tree(tn), root))
            except Exception:  # noqa: BLE001 - nothing known to be repaired: judge every reference
                paths = set()
            self._c[("p", tn)] = set(paths or ())
        return self._c[("p", tn)]

    def wf_parent(self):
        """{partition: (parent partition, parent rst_o site)} of the current die reset wavefront solve (reset_tree.wf_solve)"""
        import reset_tree as RT
        sol = self._run(lambda: RT.wf_solve(self._plan()))
        return {p: (None if pr is None else (pr[0], pr[1])) for p, pr in sol["parent"].items()}

    def entry_rows(self, tn):
        """ENTRYFOOT a.: [{port, inst, pin, xy, box, foot, top, on_track}] of every early core tap naming a hard core's
        clock_entry_access pin, with the utility pin box the kit generator emits for it (gen_phys._pin_box, core_tap_rows)"""
        import gen_phys as GP
        import schema

        def go():
            P = self._plan()
            lb = P.layer_budget["partition_signal_max"]
            top, L = int(lb[1:]), P.layers[lb]
            taps = {n: (x, y) for n, x, y, _ in schema.core_taps(P, tn)}
            rows = GP.core_tap_rows(P, tn)
            out = []
            for c in P.types[tn].get("hard_cores") or []:
                acc = c.get("clock_entry_access")
                if not acc:
                    continue
                for n, i, pin, _, _ in rows:
                    if n in taps and GP._core_is(c, i) and pin == acc.get("pin"):
                        x, y = taps[n]
                        k = ((x if L["dir"] == "V" else y) - L["offset_um"]) / L["pitch_um"]
                        out.append(dict(port=n, inst=c["inst"], pin=pin, xy=(x, y), box=[float(v) for v in GP._pin_box(P, tn, n, x, y)],
                                        foot=(acc.get("footprints_um") or {}).get(f"M{top}") or [], top=top,
                                        on_track=abs(k - round(k)) <= 1e-6))
            return out
        return self._run(go)

    def grid(self, tn):
        """{tap: (x, y)} of the type's current tap grid (schema.tap_grid, reach_rules R-REACH-4's grid)"""
        if ("g", tn) not in self._c:
            import schema
            self._c[("g", tn)] = self._run(lambda: {n: (float(x), float(y)) for n, x, y in schema.tap_grid(self._plan(), tn)})
        return self._c[("g", tn)]

    def raw_hops(self, tn):
        """reach_rules.raw_hops: [(where, raw, 'same'|'half'|'missing', hop um|None, limit um)]"""
        import reach_rules as R
        T = self._c.get(("t", tn))
        return self._run(lambda: R.raw_hops(self._plan(), self.raw["partition_types"][tn], tn, tree=T))


NOFACE = "noface"


def bound_start_raw(bind_rtl, tn):
    """(raw relay q, [(q, (x, y))] chain root->raw) of cland_start_raw in the bound RTL; NOFACE when the bound type has no
    FSTART face flops (cland_fstart_out_* = cland_start wires: a relay-origin / split variant, e.g. KV kv3_pv*e); None = unknown"""
    if not bind_rtl:
        return None
    for f in (Path(bind_rtl) / f"{tn}_part.sv", Path(bind_rtl) / f"{tn}.sv"):
        if f.exists():
            text = f.read_text(errors="replace")
            if "u_cland_fstart_" not in text:
                return NOFACE
            m = re.search(r"assign cland_start_raw = (\w+);", text)
            if not m:
                return None
            by_q = {q: (d, (float(x), float(y))) for _, d, q, _dep, x, y in BOUND_REL.findall(text)}
            raw = m.group(1)
            if raw not in by_q:
                return None
            chain = [raw]
            while by_q[chain[-1]][0] in by_q and len(chain) < 256:
                chain.append(by_q[chain[-1]][0])
            return raw, [(q, by_q[q][1]) for q in chain[::-1]]
    return None


def hop_path(where, t):
    """reach_rules.raw_hops 'where' -> the plan path spelling of reset_anchor.ref_paths"""
    kind, _, rest = where.partition(":")
    if kind == "local_reset":
        for i, lr in enumerate(((t.get("clock") or {}).get("landing_local_resets")) or []):
            if isinstance(lr, dict) and str(lr.get("name")) == rest:
                return f"clock/landing_local_resets/{i}/raw"
        return None
    bus, _, i = rest.rpartition(":")
    return f"clock/landing_{kind}/branches/{bus}/stages/{i}/raw_reset"


def _repaired(S, tn):
    f = getattr(S, "repaired", None)
    return f(tn) if f else set()


def rstreach_type(tn, t, S, bind_rtl=None, reach=REACH_UM):
    out = []
    # a. START / local raw reset hops (R-REACH-5 measure); a reference the bind re-picks itself (GATE-AGREE-R1 predicate,
    #    e.g. every landing_local_resets raw: LOCAL-RESET-RAW-1) is WARN, as in LANDREMAP-ADVISORY
    hops = S.raw_hops(tn)
    bad_hops = [h for h in hops if h[2] == "missing" or (h[3] is not None and h[3] > h[4] + EPS)]
    rp = _repaired(S, tn) if bad_hops else set()
    soft = [h for h in bad_hops if hop_path(h[0], t) in rp]
    # rr_t<i> (MISSION-role raw wavefront copies): reach_rules resolves them on reset_tree.start_relays, which does not hold
    # every copy the bind emits (QC C1b slw_su_c: 13 'missing' rr_t names, strict bind clean) -> estimator only
    rrt = [h for h in bad_hops if h not in soft and str(h[1]).startswith("rr_t")]
    if rrt:
        w = max(rrt, key=lambda h: h[3] or 0)
        out.append(f"WARN RSTREACH {tn}: {len(rrt)} START raw rr_t reference(s) missing / over reach on the start_relays model "
                   f"(e.g. {w[0]} <- {w[1]}{'' if w[3] is None else f' {w[3]:.0f} um'}); rr_t copies are judged by the strict bind")
        soft = soft + rrt
    if soft:
        out.append(f"WARN RSTREACH {tn}: {len(soft)} START / local reset raw reference(s) missing or over reach that the bind "
                   f"re-picks itself (e.g. {soft[0][0]} <- {soft[0][1]}); re-derive to keep kits byte-stable")
    hops = [h for h in hops if h not in soft]
    miss = [h for h in hops if h[2] == "missing"]
    over = sorted((h for h in hops if h[3] is not None and h[3] > h[4] + EPS), key=lambda h: -h[3])
    if miss:
        ex = "; ".join(f"{h[0]} <- {h[1]}" for h in miss[:MAX_LIST])
        out.append(f"FAIL RSTREACH {tn}: {len(miss)} START / local reset raw net(s) not in the type's reset tree ({ex}); "
                   f"re-point them after the tap / tree change: reach_rules.py fix --rules 1 (or the row's own START tool)")
    if over:
        ex = "; ".join(f"{h[0]} <- {h[1]} {h[3]:.0f} um" for h in over[:MAX_LIST])
        out.append(f"FAIL RSTREACH {tn}: {len(over)} START / local reset raw hop(s) over the reset reach (limit "
                   f"{over[0][4]:g} um; worst {ex}): the raw pointers still aim at the old taps / relays; re-derive them "
                   f"(reach_rules.py fix --rules 1, or the START tool of the row that moved the taps)")
    # b. FSTART raw reset coverage
    fs = fstart_pins(t)
    if not fs:
        return out
    bound = bound_start_raw(bind_rtl, tn)
    if bound == NOFACE:
        return out
    branches = [b for b in ((t.get("clock") or {}).get("landing_raw_branches") or []) if isinstance(b, dict)]
    covered, far = set(), []
    rel = S.relays(tn) if branches else {}
    for b in branches:
        pins = [c.split(":", 1)[1] for c in b.get("consumers") or [] if str(c).startswith("fstart:")]
        covered.update(pins)
        pts = [st.get("xy_um") for st in b.get("stages") or []]
        base = rel.get(b.get("base"))
        chain = ([base[1]] if base else []) + [tuple(p) for p in pts if isinstance(p, list)]
        for pn in pins:
            if pn not in fs or not chain:
                continue
            legs = [man(a, c) for a, c in zip(chain, chain[1:] + [fs[pn]])]
            h = max(legs)
            if h > reach + EPS:
                cos = len(chain) > 1 and len({(round(p[0], 2), round(p[1], 2)) for p in chain}) == 1
                k = legs.index(h)
                leg = ("base " + str(b.get("base")) + " -> copy 0") if base and k == 0 else \
                      ("last copy -> pin" if k == len(legs) - 1 else f"copy {k - (1 if base else 0)} -> {k + (0 if base else 1)}")
                far.append((h, b.get("name"), pn, cos, len(chain), leg))
    if far:
        far.sort(key=lambda r: -r[0])
        ex = "; ".join(f"{n} -> fstart:{p} {h:.0f} um at {lg}" + (f" (all {k} stages co-sited)" if c else "")
                       for h, n, p, c, k, lg in far[:MAX_LIST])
        out.append(f"FAIL RSTREACH {tn}: {len(far)} landing_raw_branches hop(s) to FSTART flops over {reach:g} um ({ex}); "
                   f"re-derive the branches on the current floorplan: kv_start_corridor_event.py raw --bind-rtl <strict bind>")
    rest = {k: v for k, v in fs.items() if k not in covered}
    if not rest:
        return out
    if bound:
        raw, chain = bound
        src = chain[-1][1]
        d = sorted(((man(src, xy), k) for k, xy in rest.items()), reverse=True)
        cos = sum(1 for _, xy in chain if (round(xy[0], 2), round(xy[1], 2)) == (round(src[0], 2), round(src[1], 2)))
        if d[0][0] > reach + EPS:
            n = sum(1 for h, _ in d if h > reach + EPS)
            out.append(f"FAIL RSTREACH {tn}: cland_start_raw = {raw} at ({src[0]:g}, {src[1]:g}) (bound; {cos} of "
                       f"{len(chain)} chain stages on that site) drives {n} of {len(rest)} FSTART flop pin(s) over {reach:g} um "
                       f"(worst fstart:{d[0][1]} {d[0][0]:.0f} um) and no landing_raw_branches covers them: add / re-derive "
                       f"clock.landing_raw_branches (kv_start_corridor_event.py raw, same depth, 0 cycles)")
        return out
    r = l1_radius(list(rest.values()))
    if r > reach + EPS:
        # plan-only: whether the bind emits FSTART face flops (vs cland_start wires) is a bind-role fact -> WARN; with a bind
        # of the type (--elab-dir, <plan dir>/bind_of_record) the bound case above is the FAIL
        what = "has no clock.landing_raw_branches" if not branches else f"leaves {len(rest)} of {len(fs)} uncovered"
        ex = ", ".join(sorted(rest)[:3])
        out.append(f"WARN RSTREACH {tn}: {len(rest)} FSTART pin(s) span an L1 radius of {r:.0f} um > {reach:g} um and the type "
                   f"{what} (e.g. {ex}); if they are face flops on the one cland_start_raw relay, no single site reaches "
                   f"them -- give PRE --elab-dir <bind of this or the base plan> to decide (FAIL), or re-derive the branches")
    return out


def rstnode_stale(tn, t, S, base_raw=None, BS=None):
    """FAIL lines when landing_remap's reset-node pass (rule 1 with the base plan, rule 2 always) would change the type's
    landing_raw_branches; a landing_remap without the pass falls back to the literal D-chain test on the solved tree"""
    import copy
    try:
        import landing_remap as LR
        LR.rstnode_apply, LR.rstnode_plan  # noqa: B018 - older trees lack the pass
    except (ImportError, AttributeError):
        LR = None
    branches = (t.get("clock") or {}).get("landing_raw_branches") or []
    if LR is None:
        rel, broken = S.relays(tn), []
        for b in branches:
            prev = b.get("base")
            for i, st in enumerate(b.get("stages") or []):
                cur = st.get("original")
                if cur in rel and prev in rel and rel[cur][0] != prev:
                    broken.append(f"{b.get('name')}.stages.{i} {cur}: D = {rel[cur][0]}, branch says {prev}")
                prev = cur
        return [f"FAIL DERIVEDNAME {tn}: {len(broken)} landing_raw_branches stage(s) are no longer a literal D-chain of the "
                f"re-solved reset tree ({'; '.join(broken[:MAX_LIST])}); landing_remap --resets rstnode BASE PLAN OUT"] if broken else []
    new_view = {"partition_types": {tn: t}}
    mp, unres = {}, []
    if base_raw and BS is not None:
        maps, _trees, unres, _sk = LR.rstnode_plan(base_raw, new_view, [tn],
                                                   lambda r, k: S.tree(k) if r is new_view else BS.tree(k))
        mp = maps.get(tn, {})
    tc = copy.deepcopy(t)
    ch, bad = LR.rstnode_apply(tc, mp, S.tree(tn))
    out = []
    if mp or ch or bad:
        ren = "; ".join(f"{a} -> {b}" for a, b in sorted({v for v in mp.values()})[:MAX_LIST])
        ex = "; ".join(f"{c['name']}: {c['was'][0]}..{c['was'][-1]} -> {c['now'][0]}..{c['now'][-1]}" for c in ch[:MAX_LIST])
        bx = "; ".join(f"{x.get('name')} {x.get('final')} ({x.get('why')})" for x in bad[:MAX_LIST])
        out.append(f"FAIL DERIVEDNAME {tn}: stale landing_raw_branches -- landing_remap --resets rstnode would rename "
                   f"{len(mp)} final(s) ({ren or '-'}), rebuild {len(ch)} chain(s) over the re-solved tree ({ex or '-'})"
                   + (f", and cannot resolve {len(bad)} ({bx})" if bad else "")
                   + "; fix: python3 -I tools/die_plan/landing_remap.py BASE PLAN OUT --resets rstnode")
    if unres:
        out.append(f"WARN DERIVEDNAME {tn}: {len(unres)} reset-node final(s) with no unique node at the base site "
                   f"({'; '.join(str(x.get('name')) for x in unres[:MAX_LIST])}): needs a branch row, not a rename")
    return out


def derivedname_type(tn, t, S, base_raw=None, BS=None):
    out = []
    ck = t.get("clock") or {}
    refs = name_refs(t)
    branches = [b for b in (ck.get("landing_raw_branches") or []) if isinstance(b, dict)]
    rel = taps = None
    if any(RELAY.match(v) for v in refs.values()) or branches:
        rel = S.relays(tn)
    if any(TAP.match(v) for v in refs.values()):
        taps = S.taps(tn)
    bad, rp = [], None
    for p, v in sorted(refs.items()):
        m = RELAY.match(v)
        if m:
            ok = v in rel or (m.group(1) == "rr_t" and (f"rst_n_t{m.group(2)}" in rel))
        else:
            ok = v in taps
        if not ok:
            bad.append((p, v))
    if bad:
        rp = _repaired(S, tn)
        # collector_children / collector_local_sources nodes are re-solved by the bind's collector pass (QC C1b sle_su_c,
        # slw_su_c bound with such names): reported, not FAIL
        soft = [(p, v) for p, v in bad if p in rp or "/landing_contract/collector_" in p or v.startswith("rr_t")]
        bad = [x for x in bad if x not in soft]
        if soft:
            out.append(f"WARN DERIVEDNAME {tn}: {len(soft)} referenced relay name(s) gone from the tree that the bind re-picks / "
                       f"re-solves itself (e.g. {soft[0][0]} = {soft[0][1]})")
    if bad:
        ex = "; ".join(f"{p} = {v}" for p, v in bad[:MAX_LIST])
        out.append(f"FAIL DERIVEDNAME {tn}: {len(bad)} of {len(refs)} referenced relay / tap name(s) not emitted by the "
                   f"type's current reset tree / tap table ({ex}); run landing_remap --resets anchor (TREE's tools)")
    # b. raw branch chains: the oracle is the fix itself (COORD 11-23: landing_remap --resets rstnode, LANDREMAP-RSTNODE
    #    29d2fff35c): run its reset-node pass on a copy of the type; anything it would change is STALE
    if branches:
        out += rstnode_stale(tn, t, S, base_raw, BS)
    # c. consumers / START keys / bands
    fs = fstart_pins(t)
    lc = ck.get("landing_contract") or {}
    bands = set((lc.get("bands") or {}).keys())
    ws = (ck.get("landing_writer_start") or {}).get("branches") or {}
    rs = (ck.get("landing_reader_start") or {}).get("branches") or {}
    dang = []
    for b in branches:
        for c in b.get("consumers") or []:
            m = CONS.match(str(c))
            if not m:
                continue
            if m.group(2) and m.group(2) not in fs:
                dang.append(f"{b.get('name')} {c} (no {FS}{m.group(2)} pin)")
            elif m.group(3):
                br = (ws if m.group(3) == "writer" else rs).get(m.group(4))
                if not isinstance(br, dict) or int(m.group(5)) >= len(br.get("stages") or []):
                    dang.append(f"{b.get('name')} {c} (no such START stage)")
    for k in ws:
        if fs and k not in fs:
            dang.append(f"landing_writer_start.{k} (no {FS}{k} pin)")
    for k in rs:
        if bands and k not in bands:
            dang.append(f"landing_reader_start.{k} (no landing band {k})")
    if dang:
        out.append(f"FAIL DERIVEDNAME {tn}: {len(dang)} derived landing reference(s) name a pin / stage / band the current "
                   f"floorplan lacks ({'; '.join(dang[:MAX_LIST])})")
    # d. station launch / capture instances
    insts = {c.get("inst") for c in (t.get("hard_cores") or []) + (t.get("contents") or []) if isinstance(c, dict)}
    miss, leaf = [], []
    for i, r in enumerate(t.get("internal_stations") or []):
        if not isinstance(r, dict):
            continue
        for key in ("launch", "capture"):
            v = r.get(key)
            if not isinstance(v, str):
                continue
            m = re.match(r"^(core:|leaf\s+)(\w+)$", v.strip())
            if m and insts and m.group(2) not in insts:
                (miss if m.group(1) == "core:" else leaf).append(f"internal_stations.{i}.{key} = {v} ({r.get('conn')})")
    if miss:
        out.append(f"FAIL DERIVEDNAME {tn}: {len(miss)} station end(s) name a hard core the type no longer has "
                   f"({'; '.join(miss[:MAX_LIST])}); re-derive the stations after the re-floor")
    if leaf:      # a leaf may be an RTL instance the plan does not list in contents: estimator only
        out.append(f"WARN DERIVEDNAME {tn}: {len(leaf)} station end(s) name a leaf that is not in the type's contents / hard_cores "
                   f"({'; '.join(leaf[:2])}); check it is an instance of the bound RTL")
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# ENTRYFOOT (PRE-QC-GENCHECK 11-23, QC-CB-PROBE 23:18): QC CB-R3 street row moved u_t00/u_t01 (x 103.68 -> 60.48) and their
# clock_entry_access footprints, but not the early core taps clk_c0/clk_c2 (x 332.704 / 332.576 stayed).  Strict bind and
# LATCHECK passed; kit GEN died in lef_clock_entry.validate_access ("entry footprint differs from actual emitted utility pin").
#   a. every early core tap that names a hard core's clock_entry_access pin: the utility pin box the generator emits for it
#      (gen_phys._pin_box at the tap xy) equals the access footprint on the top partition layer (1e-6 um), and the tap sits on
#      a preferred routing track (gen_phys.core_tap_pins "explicit entry off preferred routing track");
#   b. with a baseline plan: a hard core whose origin moved (same orient) moves every early core tap that names it by the same
#      delta (any die; the derived tap follows its core).
ENTRY_EPS = 1e-6
FOLLOW_EPS = 0.05          # um: a snapped tap may land up to a track off the exact delta


def _core_tap_names(t):
    ck = (t or {}).get("clock") or {}
    if ck.get("core_taps") != "early":
        return []
    out, k = [], 0
    for tp in ck.get("taps") or []:
        if isinstance(tp, dict) and tp.get("kind") == "core":
            out.append((f"clk_c{k}", tp))
            k += 1
    return out


def _tap_inst(name, insts):
    for i in sorted(insts, key=len, reverse=True):
        if name == i or str(name).startswith(i + "."):
            return i
    return None


def entry_types(raw):
    """types with early core taps on a hard core that declares clock_entry_access"""
    out = []
    for tn, t in sorted(((raw or {}).get("partition_types") or {}).items()):
        if isinstance(t, dict) and _core_tap_names(t) and any(
                isinstance(c, dict) and c.get("clock_entry_access") for c in t.get("hard_cores") or []):
            out.append(tn)
    return out


def entryfoot_type(tn, S):
    """ENTRYFOOT a. lines of one type (S.entry_rows(tn): [{port, inst, pin, xy, box, foot, top, on_track}])"""
    out = []
    for r in S.entry_rows(tn):
        foot = r.get("foot") or []
        box = r["box"]
        x, y = r["xy"]
        if len(foot) != 1:
            out.append(f"FAIL ENTRYFOOT {tn}: {r['port']} ({r['inst']}.{r['pin']}) clock_entry_access has {len(foot)} M{r['top']} "
                       f"footprint boxes (needs exactly 1 = the emitted utility pin); kit GEN refuses it")
            continue
        d = [round(a - b, 6) + 0.0 for a, b in zip(box, foot[0])]
        if any(abs(v) > ENTRY_EPS for v in d):
            fx, fy = (foot[0][0] + foot[0][2]) / 2, (foot[0][1] + foot[0][3]) / 2
            out.append(f"FAIL ENTRYFOOT {tn}: {r['port']} ({r['inst']}.{r['pin']}) tap xy [{x:g},{y:g}] emits M{r['top']} pin box "
                       f"[{', '.join(f'{v:g}' for v in box)}] but the clock_entry_access footprint is "
                       f"[{', '.join(f'{v:g}' for v in foot[0])}] (d {d[0]:+g},{d[1]:+g} um); kit GEN dies 'entry footprint "
                       f"differs from actual emitted utility pin' -- move the tap to the footprint centre "
                       f"[{fx:g},{fy:g}] (or re-derive the footprint), the core and its tap move together")
        elif not r.get("on_track", True):
            out.append(f"FAIL ENTRYFOOT {tn}: {r['port']} ({r['inst']}.{r['pin']}) tap xy [{x:g},{y:g}] is off the preferred "
                       f"M{r['top']} routing track; kit GEN refuses an explicit entry off track")
    return out


def tapfollow_findings(raw, base_raw, only=None):
    """ENTRYFOOT b. (pure): core moved since the baseline, its early core tap did not move with it"""
    if not base_raw:
        return []
    out = []
    bt = base_raw.get("partition_types") or {}
    for tn, t in sorted(((raw or {}).get("partition_types") or {}).items()):
        b = bt.get(tn)
        if not isinstance(t, dict) or not isinstance(b, dict) or (only and tn not in only):
            continue
        cores = {c["inst"]: c for c in t.get("hard_cores") or [] if isinstance(c, dict) and c.get("inst")}
        bcores = {c["inst"]: c for c in b.get("hard_cores") or [] if isinstance(c, dict) and c.get("inst")}
        btaps = {tp.get("name"): tp for _, tp in _core_tap_names(b)}
        bad = []
        for port, tp in _core_tap_names(t):
            i = _tap_inst(tp.get("name"), cores)
            c, bc, btp = cores.get(i), bcores.get(i), btaps.get(tp.get("name"))
            if not (c and bc and btp and c.get("origin_um") and bc.get("origin_um") and tp.get("xy") and btp.get("xy")):
                continue
            if (c.get("orient") or "R0") != (bc.get("orient") or "R0") or c.get("outline_um") != bc.get("outline_um"):
                continue
            dc = [float(a) - float(z) for a, z in zip(c["origin_um"], bc["origin_um"])]
            if max(abs(v) for v in dc) <= FOLLOW_EPS:
                continue
            dt = [float(a) - float(z) for a, z in zip(tp["xy"], btp["xy"])]
            if any(abs(u - v) > FOLLOW_EPS for u, v in zip(dc, dt)):
                bad.append(f"{port} {tp.get('name')}: core moved ({dc[0]:+g},{dc[1]:+g}) tap moved ({dt[0]:+g},{dt[1]:+g})")
        if bad:
            out.append(f"FAIL ENTRYFOOT {tn}: {len(bad)} early core tap(s) did not follow their moved hard core since the "
                       f"baseline ({'; '.join(bad[:MAX_LIST])}); shift each tap xy by its core's delta")
    return out


def entryfoot_findings(raw, S, base_raw=None, only=None):
    out = []
    for tn in entry_types(raw):
        if only and tn not in only:
            continue
        try:
            out += entryfoot_type(tn, S)
        except Exception as e:  # noqa: BLE001 - the kit generator names its own error; never a silent pass
            out.append(f"WARN ENTRYFOOT {tn}: not checked ({type(e).__name__}: {str(e)[:160]})")
    return out + tapfollow_findings(raw, base_raw, only)


# STALE EXPORT TAP (ENTRYFOOT c., COORD 11-23 23:4x; KV-SENDER-SKEW / FABLE-RC-KV 23:28-23:31): KV A5 -- 66 of 67 late forwarded
# clock exports keep the export buffer at the source_clock_port chosen at first landing compose, 320-1942 um from the port after
# the taps were regrown / renumbered (2-12 repeaters, fclk 294-964 ps vs data 132-411).  Every landing_contract clock output's
# source tap lies within EXPORT_HOP_UM of its pin (FAIL above; reach_rules R-REACH-4 measure, fix: reach_rules.py fix --rules 4
# or FWDCLK-1 repoint at 150 um).  A source tap that no longer exists is FAIL; so is a pin whose source is already the
# nearest tap but over the limit (own line: add a tap or move the pin).
EXPORT_HOP_UM = 300.0


def export_pins(t):
    lc = ((t or {}).get("clock") or {}).get("landing_contract") or {}
    return [q for q in lc.get("pins") or [] if isinstance(q, dict) and q.get("kind") == "clock" and q.get("dir") == "out"
            and q.get("source_clock_port") is not None and q.get("xy_um")]


def exporttap_type(tn, t, grid, limit=EXPORT_HOP_UM):
    """(lines, n_over, n_pins) of one type; grid = {tap: (x, y)} (schema.tap_grid)"""
    pins = export_pins(t)
    if not pins:
        return [], 0, 0
    taps = [n for n in grid if n != "clk"] or list(grid)
    stale, dang, nofix = [], [], []
    for q in pins:
        s, xy = q["source_clock_port"], q["xy_um"]
        near = min(taps, key=lambda n: (man(grid[n], xy), n)) if taps else None
        h1 = man(grid[near], xy) if near else float("inf")
        if s not in grid:
            dang.append(f"{q.get('name')} <- {s} (gone; nearest {near} {h1:.0f} um)")
            continue
        h0 = man(grid[s], xy)
        if h0 <= limit + EPS:
            continue
        if h1 < h0 - EPS:      # a nearer tap exists (maybe itself over the limit): the source is stale
            stale.append((h0, f"{q.get('name')} <- {s} {h0:.0f} um (nearest {near} {h1:.0f} um)"))
        else:
            nofix.append(f"{q.get('name')} <- {s} {h0:.0f} um (nearest {near} {h1:.0f} um)")
    out = []
    if stale or dang:
        stale.sort(reverse=True)
        ex = [x for _, x in stale] + dang
        out.append(f"FAIL ENTRYFOOT {tn}: STALE-EXPORT-TAP {len(stale)} of {len(pins)} forwarded-clock output(s) take a source "
                   f"tap more than {limit:g} um from their pin" + (f", {len(dang)} a tap that no longer exists" if dang else "")
                   + f" ({'; '.join(ex[:MAX_LIST])}); re-point source_clock_port to the nearest tap (reach_rules.py fix "
                     f"--rules 4 / FWDCLK-1 repoint)")
    if nofix:
        out.append(f"FAIL ENTRYFOOT {tn}: STALE-EXPORT-TAP {len(nofix)} forwarded-clock output(s) over {limit:g} um with no nearer "
                   f"tap ({'; '.join(nofix[:2])}); add a tap or move the pin")
    return out, len(stale) + len(dang) + len(nofix), len(pins)


def exporttap_findings(raw, S, only=None, limit=EXPORT_HOP_UM, budget=None):
    """budget = seconds (tap grids of a big die cost minutes: S81 561 s); types past it are WARN ... not checked"""
    t0, left = time.time(), []
    types = (raw or {}).get("partition_types") or {}
    uses = {}
    for p in ((raw or {}).get("partitions") or []):
        if isinstance(p, dict) and p.get("type"):
            uses[p["type"]] = uses.get(p["type"], 0) + 1
    out, over, pins, iover, ipins = [], 0, 0, 0, 0
    for tn, t in sorted(types.items()):
        if not isinstance(t, dict) or (only and tn not in only) or not export_pins(t):
            continue
        if budget is not None and time.time() - t0 > budget:
            left.append(tn)
            continue
        try:
            lines, n, m = exporttap_type(tn, t, S.grid(tn), limit)
        except Exception as e:  # noqa: BLE001
            out.append(f"WARN ENTRYFOOT {tn}: STALE-EXPORT-TAP not checked ({type(e).__name__}: {str(e)[:160]})")
            continue
        out += lines
        k = uses.get(tn, 1)
        over, pins, iover, ipins = over + n, pins + m, iover + n * k, ipins + m * k
    if left:
        out.append(f"WARN ENTRYFOOT STALE-EXPORT-TAP: {len(left)} type(s) not checked (budget {budget:.0f} s, OT_DERIVED_BUDGET_S): "
                   f"{', '.join(left[:6])}")
    if pins:
        out.append(f"LIST ENTRYFOOT STALE-EXPORT-TAP die: {over} of {pins} forwarded-clock output pins (type level; {iover} of "
                   f"{ipins} placed) have a source hop over {limit:g} um")
    return out


CLASSES = ("RSTREACH", "DERIVEDNAME", "ENTRYFOOT")
ENTRYFOOT_LEVEL = "WARN"   # ENTRYFOOT-WARN-1124 (COORD r703: new checks report-only; it refused QC-CB-PROBE rebind3 + KV-ALLFIX
                          # launch): every ENTRYFOOT / STALE-EXPORT-TAP FAIL prints at this level; COORD promotes by editing it


def die_relay_findings(raw, S):
    """DERIVEDNAME die level (S81 c8 24_tgr5 ba9b277a852b: 38 reset.die_relays carried from B1, parents no longer the solved
    wavefront parents, reach_relay_plan raised in the tail): every reset.die_relays row's parent / site = the current
    wavefront solve (the check reset_tree._die_relay_rows makes when the tree is built)"""
    drl = ((raw or {}).get("reset") or {}).get("die_relays") or {}
    if not drl or not hasattr(S, "wf_parent"):
        return []
    try:
        par = S.wf_parent()
    except Exception as e:  # noqa: BLE001
        return [f"WARN DERIVEDNAME die: reset.die_relays not checked (wavefront solve: {type(e).__name__}: {str(e)[:160]})"]
    bad = []
    for p, d in sorted(drl.items()):
        pr = par.get(p)
        if pr is None or [pr[0], pr[1]] != [d.get("parent"), d.get("site")]:
            bad.append(f"{p}: declared {d.get('parent')}/{d.get('site')}, solve {None if pr is None else f'{pr[0]}/{pr[1]}'}")
    if not bad:
        return []
    return [f"FAIL DERIVEDNAME die: {len(bad)} of {len(drl)} reset.die_relays name a parent that is not the current wavefront "
            f"solve's ({'; '.join(bad[:MAX_LIST])}); the bind / reach_relay_plan refuse them -- re-plan: reach_relay_plan.py "
            f"(or drop reset.die_relays before the tail rebuilds them)"]


def default_bind_rtl(plan_path, elab_dir=None):
    """bound RTL dir used to tell FSTART face flops and the bound cland_start_raw site: --elab-dir, $OT_DERIVED_BIND_RTL,
    else <plan dir>/bind_of_record (the tree's last bind; the face-flop role does not change with a re-floor)"""
    for d in (elab_dir, os.environ.get("OT_DERIVED_BIND_RTL"), Path(plan_path).parent / "bind_of_record"):
        if d and Path(d).is_dir():
            return Path(d) / "rtl" if (Path(d) / "rtl").is_dir() else Path(d)
    return None


def derived_todo(raw):
    """the (type, block) pairs findings() checks per type"""
    types = (raw or {}).get("partition_types") or {}
    only = set(filter(None, os.environ.get("OT_DERIVED_TYPES", "").split(",")))
    return [(tn, t) for tn, t in sorted(types.items()) if isinstance(t, dict) and not t.get("hard")
            and (not only or tn in only) and ((t.get("clock") or {}).get("landing_contract") or name_refs(t)
                                              or t.get("internal_stations"))]


def _raw_hop_reads(t, broadcast):
    """reach_rules.raw_hops solves the type's reset tree when a START / local raw names rst_rl_<k> (or rr_t<k> on a START broadcast
    plan); broadcast() -> reset_tree.start_broadcast of the plan, asked only when an rr_t raw exists"""
    import reach_rules as R
    items = [(st.get("raw_reset"), st.get("xy_um")) for _k, _b, _i, st in R._start_stages(t)]
    items += [(lr.get("raw"), lr.get("xy_um")) for lr in ((t.get("clock") or {}).get("landing_local_resets") or [])
              if isinstance(lr, dict)]
    for raw, xy in items:
        m = R._RAW.match(str(raw or ""))
        if not m or not isinstance(xy, list) or len(xy) != 2:
            continue
        if m.group(1) == "rst_rl_" or (m.group(1) == "rr_t" and broadcast()):
            return True
    return False


def reset_tree_types(raw, classes=CLASSES, broadcast=lambda: False):
    """RESET-TREE-CACHE-1124: the types findings() reads the solved reset tree of whatever the trees hold (Solver.relays / tree):
    DERIVEDNAME on a relay-name reference or landing_raw_branches, RSTREACH on a raw_hops raw relay or FSTART branches.  A read
    that only follows a finding (the re-pick of a type with tap-only references, the base tree of an rstnode rename) is not in it."""
    want = {c.upper() for c in classes}
    out = set()
    for tn, t in derived_todo(raw):
        branches = [b for b in ((t.get("clock") or {}).get("landing_raw_branches") or []) if isinstance(b, dict)]
        if "DERIVEDNAME" in want and (branches or any(RELAY.match(v) for v in name_refs(t).values())):
            out.add(tn)
        elif "RSTREACH" in want and ((branches and fstart_pins(t)) or _raw_hop_reads(t, broadcast)):
            out.add(tn)
    return out


def findings(raw, plan_path, tree=None, classes=CLASSES, bind_rtl=None, solver=None, budget_s=None, base=None,
             base_solver=None):
    """FAIL / WARN lines of the three classes (a type the solver cannot build is WARN ... not checked: the bind names it)"""
    want = {c.upper() for c in classes}
    if not want & set(CLASSES):
        return []
    todo = derived_todo(raw)
    only = set(filter(None, os.environ.get("OT_DERIVED_TYPES", "").split(",")))
    S = solver or Solver(raw, plan_path, tree)
    base_raw = None
    if base:
        try:
            base_raw = json.loads(Path(base).read_text()) if isinstance(base, (str, Path)) else base
        except (OSError, ValueError):
            base_raw = None
        if base_raw is not None and Path(str(base)).resolve() == Path(str(plan_path)).resolve():
            base_raw = None
    BS = base_solver or (Solver(base_raw, base if isinstance(base, (str, Path)) else plan_path, tree) if base_raw else None)
    if bind_rtl is None and solver is None:
        bind_rtl = default_bind_rtl(plan_path)
    sys.path.insert(0, str(HERE))
    budget = float(budget_s if budget_s is not None else os.environ.get("OT_DERIVED_BUDGET_S", "900"))
    t0, out, done, errs = time.time(), [], 0, 0
    if "DERIVEDNAME" in want and not only:
        out += die_relay_findings(raw, S)
    if "ENTRYFOOT" in want:
        ef = entryfoot_findings(raw, S, base_raw, only)
        if hasattr(S, "grid"):
            ef += exporttap_findings(raw, S, only, budget=budget)
        out += [ENTRYFOOT_LEVEL + l[4:] if l.startswith("FAIL ENTRYFOOT") else l for l in ef]
    for tn, t in todo:
        if time.time() - t0 > budget:
            break
        done += 1
        for cls, fn in (("DERIVEDNAME", lambda: derivedname_type(tn, t, S, base_raw, BS)),
                        ("RSTREACH", lambda: rstreach_type(tn, t, S, bind_rtl))):
            if cls not in want:
                continue
            try:
                out += fn()
            except Exception as e:  # noqa: BLE001 the bind reports its own tree error
                errs += 1
                out.append(f"WARN {cls} {tn}: not checked ({type(e).__name__}: {str(e)[:160]})")
    left = len(todo) - done
    if left:
        out.append(f"WARN DERIVED summary: {done} of {len(todo)} type(s) checked, {left} not checked (budget {budget:.0f} s; "
                   f"OT_DERIVED_BUDGET_S)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="derived_drop", description=__doc__.split("\n\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--tree")
    ap.add_argument("--elab-dir", help="bind OUT dir (its rtl/ is read for the bound cland_start_raw site)")
    ap.add_argument("--classes", default=",".join(CLASSES))
    ap.add_argument("--baseline-plan", help="remap base (landing_remap rule 1: finals renumbered since the base)")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    try:
        raw = json.loads(Path(a.plan).read_text())
    except (OSError, ValueError) as e:
        print(f"derived_drop: cannot read {a.plan}: {e}", file=sys.stderr)
        return 2
    t0 = time.time()
    rtl = default_bind_rtl(a.plan, a.elab_dir)
    lines = findings(raw, a.plan, a.tree, [c for c in a.classes.split(",") if c], bind_rtl=rtl, base=a.baseline_plan)
    for x in lines:
        print(x)
    nf = sum(x.startswith("FAIL") for x in lines)
    print(f"DERIVED-DROP plan={a.plan} fail_lines={nf} warn_lines={len(lines) - nf} seconds={time.time() - t0:.0f}")
    if a.json:
        Path(a.json).write_text(json.dumps({"plan": a.plan, "lines": lines}, indent=1) + "\n")
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
