"""Plan-relative input files (hard-core pins_file tables, native_domains census files) resolved from explicit roots.

HEAD-CROSSING-1119 11-19 (COORD): a plan copied or composed outside its prep folder (e.g. a die clock input plan) lost
its relative inputs, and die_trial failed one at a time deep in the run (child census at the abstracts stage, core_pins
after the DME stage) -- five reruns and symlink mirrors.  Now a relative path resolves, in order, against

  1. the plan file's own folder (historical behaviour, unchanged first),
  2. every explicit plan root: die_trial --plan-root DIR (repeatable; ot_clk inputs.plan_root), env OT_PLAN_ROOT
     (os.pathsep list), and the plan's own top-level "plan_root" field (str or list),
  3. the tree root (the repo / snapshot that holds this tools/ folder).

check(P) lists EVERY unresolved input with the folders tried; die_trial calls it right after the plan load, before
abstracts / clock tree / DME, so a missing file is named up front.
"""
import os
from pathlib import Path

TREE_ROOT = Path(__file__).resolve().parents[2]
ROOTS = []          # set by die_trial --plan-root


class PlanInputError(ValueError):
    pass


def set_roots(roots):
    ROOTS[:] = [Path(r) for r in (roots or []) if r]


def dirs(P):
    """ordered, de-duplicated folders a relative plan input is looked up in"""
    out = []
    path = getattr(P, "path", None)
    if path:
        out.append(Path(path).resolve().parent)
    out += ROOTS
    out += [Path(r) for r in os.environ.get("OT_PLAN_ROOT", "").split(os.pathsep) if r]
    raw = getattr(P, "raw", None)
    own = raw.get("plan_root") if isinstance(raw, dict) else None
    if own:
        out += [Path(r) for r in ([own] if isinstance(own, str) else own)]
    out.append(TREE_ROOT)
    seen, res = set(), []
    for d in out:
        k = str(d)
        if k not in seen:
            seen.add(k)
            res.append(d)
    return res


def resolve(P, rel):
    """Path of an existing plan input (absolute as given), else None"""
    p = Path(rel)
    if p.is_absolute():
        return p if p.is_file() else None
    for d in dirs(P):
        if (d / rel).is_file():
            return d / rel
    return None


def base_dir(P, rel):
    """the folder that rel resolves against (resolve(P, rel) == base_dir / rel), else None"""
    p = resolve(P, rel)
    if p is None or Path(rel).is_absolute():
        return None
    for _ in Path(rel).parts:
        p = p.parent
    return p


def require(P, rel, what):
    p = resolve(P, rel)
    if p is None:
        raise PlanInputError(f"{what}: plan input {rel} not found (tried {', '.join(str(d) for d in dirs(P))}; "
                             f"pass die_trial --plan-root / ot_clk inputs.plan_root / OT_PLAN_ROOT)")
    return p


def missing(P):
    """[message] for every relative plan input that does not resolve: native_domains census files (parent + children)
    and hard-core pins_file tables (with reset_tree's view-side fallbacks)."""
    out = []
    types = getattr(P, "types", None) or {}
    for tn in sorted(types):
        t = types[tn]
        nd = (t.get("clock") or {}).get("native_domains")
        if isinstance(nd, dict):
            for who, f in [("native_domains", nd.get("census_file"))] + \
                          [(f"native_domains child {c.get('inst')}", c.get("census_file")) for c in nd.get("children") or []]:
                if f and resolve(P, f) is None:
                    out.append(f"type {tn}: {who} census_file {f}")
        for c in t.get("hard_cores") or []:
            f = c.get("pins_file")
            if not f or c.get("reset_net") or Path(f).is_absolute():
                continue
            try:
                import reset_tree
                reset_tree.pin_table_dir(P, tn, c)
            except Exception as e:   # noqa: aggregate every miss, never stop at the first
                out.append(f"type {tn}: hard core {c.get('inst')} pins_file {f} ({e})")
    return out


def check(P):
    miss = missing(P)
    if miss:
        uniq = sorted(set(miss))
        raise PlanInputError(f"{len(uniq)} plan input(s) do not resolve (tried {', '.join(str(d) for d in dirs(P))}; "
                             f"pass die_trial --plan-root / ot_clk inputs.plan_root / OT_PLAN_ROOT):\n  " + "\n  ".join(uniq[:50]))
