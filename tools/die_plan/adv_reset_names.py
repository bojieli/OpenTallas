"""ADV-RESET-NAME (TAP-GRID-R5 + PRECHECK-R2, COORD Fable flow review 11-23; estimator, never a gate): every generated
reset relay name (rst_rl_<k>) and density tap name (clk_t<i>) the plan's clock sections reference must exist in the
relay / tap set the bind will emit for that type.

Three tap rows in one night (S81 J8, HEAD Row B, KV D29: 14 EMIT "exactly one same-clk plain relay required" / "D !=
literal predecessor") added taps, which renumbered the reset relay tree, while clock.landing_local_resets / START stages kept
the old raw names; the bind found them an hour later.  This check solves each referencing type's reset tree
(reset_tree.for_type, the bind's own builder) and its tap table (schema.tap_grid) on the plan as written and names every
reference that is no longer emitted.  Unlike PRE LANDREMAP it needs no baseline (a composer that never ran landing_remap,
or ran it from the wrong tool path, is caught too); it cannot tell a renamed relay from a moved one, so the fix line points
at landing_remap (anchor mode) from the TREE's own tools.

Cost: one reset-tree solve per referencing type; OT_ADV_RESETNAME_BUDGET_S (default 100) bounds the total, the rest is
reported as not checked.  OT_ADV_RESETNAME_TYPES=a,b limits the types.
"""
import os
import re
import sys
import time
from pathlib import Path

CHECK = "ADV-RESET-NAME"
MAX_LINES = 20
RELAY = re.compile(r"^rst_rl_\d+$")
TAP = re.compile(r"^clk_t\d+$")
SKIP_KEYS = ("collector_tree", "taps", "added_taps")


def refs(t):
    """{plan path: name} of every rst_rl_<k> / clk_t<i> string in the type's clock section (tap tables and collector
    trees excluded: they define names, they do not reference them)."""
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


def stale(ref, relays, taps):
    """[(path, name)] of references not in the emitted relay / tap name sets (a set of None = not known, not checked)."""
    out = []
    for p, v in sorted(ref.items()):
        pool = relays if RELAY.match(v) else taps
        if pool is not None and v not in pool:
            out.append((p, v))
    return out


def configured_types(scope=None, env=None):
    env = os.environ if env is None else env
    only = {name for name in env.get("OT_ADV_RESETNAME_TYPES", "").split(",") if name}
    return only or scope


def candidates(raw, types=None):
    rows = (raw or {}).get("partition_types") or {}
    selected = []
    for name, row in sorted(rows.items()):
        if not isinstance(row, dict) or row.get("hard") or (types is not None and name not in types):
            continue
        references = refs(row)
        if references:
            selected.append((name, references))
    return selected


def findings(raw, plan_path, tree=None, tree_fn=None, taps_fn=None, budget_s=None,
             reset_plan=None, reset_types=None, **_kw):
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    rp = ((raw or {}).get("reset") or {}).get("root_part")
    if rp and rp not in {x.get("name") for x in (raw or {}).get("partitions") or [] if isinstance(x, dict)}:
        # P-FALSE-GREEN-1126: a scoped view dropped the reset root partition; the tree solve would die with KeyError (sp5)
        raise KeyError(f"reset.root_part {rp!r} is not a partition of this plan view: run RESET-NAME on the whole plan (OT_ADV_RESETNAME_TYPES limits the types)")
    todo = candidates(raw, configured_types() if reset_types is None else reset_types)
    if not todo:
        return []
    if tree_fn is None or taps_fn is None:
        import schema
        import reset_tree as RT
        P = reset_plan if reset_plan is not None else schema.Plan(raw, Path(plan_path).parent / "die_plan.json")
        tree_fn = tree_fn or (lambda tn: {x["q"] for x in RT.for_type(P, tn)["relays"]})
        taps_fn = taps_fn or (lambda tn: {p[0] for p in schema.tap_grid(P, tn)})
    budget = float(budget_s if budget_s is not None else os.environ.get("OT_ADV_RESETNAME_BUDGET_S", "100"))
    t0, out, nbad, done, errs = time.time(), [], 0, 0, 0
    for tn, r in todo:
        if time.time() - t0 > budget:
            break
        done += 1
        relays = taps = None
        try:
            if any(RELAY.match(v) for v in r.values()):
                relays = tree_fn(tn)
            if any(TAP.match(v) for v in r.values()):
                taps = taps_fn(tn)
        except Exception as e:  # noqa: BLE001 the bind reports its own tree error
            errs += 1
            # P-FALSE-GREEN (S81-GATE-LINT 11-26, col_h10_r0_p1 KeyError): a crashed check is an ERROR (FAIL line), never "not checked"
            if errs <= 3:
                out.append(f"FAIL {CHECK} {tn}: TREE-ERROR ({type(e).__name__}: {str(e)[:120]}); the reset tree / tap table could not "
                           f"be solved, so this type was NOT checked (a tool error, not a clean result)")
            continue
        bad = stale(r, relays, taps)
        if bad:
            nbad += 1
            if nbad <= MAX_LINES:
                ex = "; ".join(f"{p} = {v}" for p, v in bad[:3])
                out.append(f"WARN {CHECK} {tn}: {len(bad)} of {len(r)} referenced relay/tap name(s) are not emitted by the "
                           f"type's reset tree / tap table ({ex}); the bind will refuse them at EMIT -- run landing_remap "
                           f"--resets anchor from the TREE's tools/die_plan over this type")
    left = len(todo) - done
    if nbad or left or errs:
        out.append(f"WARN {CHECK} summary: {done - errs} of {len(todo)} referencing type(s) checked, {nbad} with stale names"
                   + (f", {left} not checked (budget {budget:.0f} s)" if left else "") + (f", {errs} TREE ERROR(S) (FAIL)" if errs else ""))
    return out
