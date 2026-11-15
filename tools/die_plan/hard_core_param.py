"""GENBUG (FABLE-PD-QCC-0740): a plan hard-core row with param_wrap {base, params} names ONE paramod of the bound module.
The bind passed with 0 errors while the plan rows said SKEW_N 6 / SKEW_S 7/8 and the bound RTL instances held 8/9 and 8/10;
only the kit-rtl step (param_wrap.wrap_bound) looked, one type at a time.  This check runs inside the bind (Binder.__init__)
on the elaborated as-built cells: for every plan hard-core row that carries param_wrap, every as-built instance the row names
must be the row's base module with each planned parameter equal (the as-built value after instance overrides and module
defaults).  usage: python3 tools/die_plan/hard_core_param.py PLAN.json BINDDIR   (report mode: every mismatch, exit 1 if any)"""
import json
import sys
from pathlib import Path


def _names(cell, local):
    n = {cell.path, cell.path.split(".")[-1]}
    if local:
        n.update((local, "u_" + local))
    else:
        n.add("u_" + cell.path.split(".")[-1])
    return n


def mismatches(plan, cells, part_of, local_of, param_defaults):
    """-> [str]: one line per plan param_wrap hard-core row whose as-built instance differs (module or a parameter)."""
    parts = {p["name"]: p["type"] for p in plan["partitions"]}
    out, seen = [], set()
    for c in cells:
        part = part_of(c.path)
        if part not in parts:
            continue
        names = _names(c, local_of(c.path))
        for e in plan["partition_types"][parts[part]].get("hard_cores", []) or []:
            pw = e.get("param_wrap")
            if not pw or e["inst"] not in names:
                continue
            key = (c.path, e["inst"])
            if key in seen:
                continue
            seen.add(key)
            if c.module != pw["base"]:
                out.append(f"{c.path} (plan row {parts[part]}/{e['inst']}): as-built module {c.module}, plan param_wrap base {pw['base']}")
                continue
            have = dict(param_defaults.get((c.ytype, c.module), {}))
            have.update(c.params or {})
            for k, v in pw["params"].items():
                got = have.get(k)
                try:
                    same = got is not None and int(got) == int(v)
                except (TypeError, ValueError):
                    same = False
                if not same:
                    out.append(f"{c.path} (plan row {parts[part]}/{e['inst']}): parameter {k} as-built {got}, plan param_wrap {v}")
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        sys.exit(__doc__)
    import os
    sys.path.insert(0, os.environ.get("HCP_TOOLS") or str(Path(__file__).resolve().parent))   # HCP_TOOLS: another tree's tools/die_plan
    import bind
    E = bind.E
    plan = bind.load_plan(argv[0])
    yjs = bind.load_asbuilt_netlist(Path(argv[1]))
    ab = plan["asbuilt"]
    F = E.flatten(yjs, ab["top"], ab.get("substitute_parent", []))
    R = bind.Rules(ab)
    defaults = {}
    for c in F.cells:
        k = (c.ytype, c.module)
        if k not in defaults:
            defaults[k] = {a: E._pval(b)[0] for a, b in yjs["modules"].get(c.ytype, {}).get("parameter_default_values", {}).items()}
    rows = mismatches(plan, F.cells, R.part_of, R.local_of, defaults)
    for r in rows:
        print("HARD_CORE_PARAM_WRAP", r)
    print("HARD_CORE_PARAM_SUM", argv[0], "mismatches", len(rows))
    return 1 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
