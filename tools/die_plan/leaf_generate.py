#!/usr/bin/env python3
"""leaf_generate.py -- ONE generator for the S81 leaf / kv_leaf re-floor chain (FP-CONVERGE-S81, COORD FLOW-0930 S-06).

  leaf_generate.py BASE_PLAN --types t1,t2 --out OUT.json [--grow DX] [--ft-xcut X] [--tree TREE] [--seed SEED.json]
                   [--extra-reg] [--work DIR] [--dry] [--no-core-place]

Chain (every step on the SAME type list, each step's input is the previous step's output; BASE_PLAN is never written):
  1 grow        leaf_grow.py grow --dx DX --ft-interior --ft-xcut X          (only with --grow)
  2 core_place  core_place.py --slot-clear ".*" --ft-resite --obstacle-aware --reach 405 [--seed S]
  3 refresh     leaf_refresh.py run  (core taps / core_resets / relay sites ride with moved cores; legalise in-core / outside)
  4 chain_resite chain_resite.py run  (first-hop / station chains over the 405 um gate; --extra-reg only with --extra-reg)
  5 retap       leaf_grow.py retap     (grid+explicit added-tap names/order follow the re-derived grid)
  6 anchor      reset_anchor.py record --repick
  7 schema      schema_test(): exit 1 on any finding of
      FLOAT      an int in BASE that is a float in OUT with an integer value (12 -> 12.0), or any float in a `bits` list
                 (the SCHEMA-INVALID x6 finding: relay_depth[].bits turned into floats)
      TAPNAME    grid+explicit added tap names / order the bind's own taps.grid_explicit_sites refuses (LANDREMAP-UNCHECKED x61)
      SEAT       relay_sites / collector root / outs inside a hard core or outside the outline (reach_fix_sinks: no worse than BASE)
      ANCHORDRY  anchor_dry.static_findings FAIL lines vs BASE
"""
import argparse
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
INT_KEYS = ("bits", "depth", "stages", "n", "count")


# ---- schema test ----------------------------------------------------------------------------------------------------------------
def _float_regressions(b, n, path="", out=None):
    out = [] if out is None else out
    if isinstance(b, dict) and isinstance(n, dict):
        for k in b:
            if k in n:
                _float_regressions(b[k], n[k], f"{path}/{k}", out)
    elif isinstance(b, list) and isinstance(n, list):
        for i in range(min(len(b), len(n))):
            _float_regressions(b[i], n[i], f"{path}[{i}]", out)
    elif isinstance(b, int) and not isinstance(b, bool) and isinstance(n, float) and n.is_integer():
        out.append(f"{path} int {b} -> float {n}")
    return out


def _bits_floats(o, path="", out=None):
    out = [] if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            if k in INT_KEYS and isinstance(v, list) and any(isinstance(x, float) for x in v):
                out.append(f"{path}/{k} {v}")
            elif k in INT_KEYS and isinstance(v, float):
                out.append(f"{path}/{k} {v}")
            else:
                _bits_floats(v, f"{path}/{k}", out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _bits_floats(v, f"{path}[{i}]", out)
    return out


def default_tap_check(raw, path, tns):
    """-> {type: error} from the bind's own taps.grid_explicit_sites on every grid+explicit type"""
    import schema as S
    import taps as TP
    P = S.Plan(raw, path)
    bad = {}
    for tn in tns:
        if ((raw["partition_types"][tn].get("clock") or {}).get("tap_mode")) == "grid+explicit":
            try:
                TP.grid_explicit_sites(P, tn)
            except Exception as e:  # noqa: BLE001 -- report every refusal
                bad[tn] = f"{type(e).__name__}: {str(e)[:160]}"
    return bad


def default_anchor_check(raw, braw, tns):
    import anchor_dry as AD
    return [x for x in AD.static_findings(raw, braw, types=set(tns)) if x.startswith("FAIL")]


def _seat_counts(t):
    import leaf_refresh as LR
    rects = LR.core_rects(t)
    W, H = t["outline_um"]
    n = dict(in_core=0, outside=0, reach_fix_in_core=0, items=[])
    for lab, c, k in LR._pts(t):
        p = c[k]
        if not isinstance(p, (list, tuple)) or len(p) < 2 or lab[0] in ("core_tap", "core_reset"):
            continue
        inc = any(LR.inside(r[:4], p, 0.0) for r in rects.values())
        out = not (0 <= p[0] <= W and 0 <= p[1] <= H)
        if lab[0] == "reach_fix_sink":
            n["reach_fix_in_core"] += inc
            continue
        n["in_core"] += inc
        n["outside"] += out
        if inc or out:
            n["items"].append(f"{lab[0]} {lab[1] if len(lab) > 1 else ''} {p[:2]} {'in core' if inc else 'outside outline'}")
    return n


def schema_test(base_raw, new_raw, types, plan_path=None, tap_check=default_tap_check, anchor_check=default_anchor_check):
    """-> [finding lines]; empty = pass"""
    out = []
    for tn in types:
        bt = base_raw["partition_types"].get(tn)
        nt = new_raw["partition_types"].get(tn)
        if nt is None:
            out.append(f"FAIL MISSING {tn}")
            continue
        fl = _float_regressions(bt, nt) if bt is not None else []
        fl += _bits_floats(nt)
        for x in sorted(set(fl))[:20]:
            out.append(f"FAIL FLOAT {tn}: {x}")
        ns = _seat_counts(nt)
        bs = _seat_counts(bt) if bt is not None else dict(in_core=0, outside=0, reach_fix_in_core=0)
        if ns["in_core"] or ns["outside"]:
            out.append(f"FAIL SEAT {tn}: {ns['in_core']} in core, {ns['outside']} outside outline: " + "; ".join(ns["items"][:4]))
        if ns["reach_fix_in_core"] > bs["reach_fix_in_core"]:
            out.append(f"FAIL SEAT {tn}: reach_fix_sinks in core {bs['reach_fix_in_core']} -> {ns['reach_fix_in_core']}")
    for tn, e in sorted((tap_check(new_raw, plan_path, types) or {}).items()):
        out.append(f"FAIL TAPNAME {tn}: {e}")
    out += anchor_check(new_raw, base_raw, types) or []
    return out


# ---- the chain -----------------------------------------------------------------------------------------------------------------
def steps(a, work):
    """-> [(name, argv, in_plan, out_plan)] -- pure; tests check the order and the plan hand-over"""
    w = Path(work)
    py = ["python3", "-I"]
    types = a.types
    ty_re = "^(" + "|".join(t.replace("+", r"\+") for t in types.split(",")) + ")$"
    cur = a.base
    st = []

    def add(name, argv, out):
        nonlocal cur
        st.append((name, argv, cur, str(out)))
        cur = str(out)

    pre = cur
    if getattr(a, "shift", 0.0):
        argv = py + [str(HERE / "leaf_grow.py"), "shift", cur, "--types", types, "--dx", str(a.shift), "--ft-interior", "--out", str(w / "s1_shift.json")]
        if a.ft_xcut:
            argv += ["--ft-xcut", str(a.ft_xcut)]
        add("shift", argv, w / "s1_shift.json")
    elif a.grow:
        argv = py + [str(HERE / "leaf_grow.py"), "grow", cur, "--types", types, "--dx", str(a.grow), "--ft-interior", "--out", str(w / "s1_grow.json")]
        if getattr(a, "die_cap", None) is not None:
            argv += ["--die-cap", str(a.die_cap)]
        if a.ft_xcut:
            argv += ["--ft-xcut", str(a.ft_xcut)]
        add("grow", argv, w / "s1_grow.json")
    if (getattr(a, "shift", 0.0) or a.grow) and not a.no_core_place:
        # grown t10: u_vsw moved +151.2 but its core tap sat west of the grow cut and stayed (STALE 160 um).  Ride the
        # grow/shift move first (deltas against the BASE; refresh only moves items still at their base xy, so points the
        # grow already moved are left alone), then the core_place move is refreshed against that plan.
        argv = py + [str(HERE / "leaf_refresh.py"), "run", pre, cur, str(w / "s1_refresh.json"), "--types", types, "--report", str(w / "refresh0.json")]
        add("refresh0", argv, w / "s1_refresh.json")
        pre = cur
    if not a.no_core_place:
        argv = py + [str(HERE / "core_place.py"), cur, "--types", types, "--die", "s81", "--repo", a.tree, "--slot-clear", ".*", "--ft-resite",
                     "--obstacle-aware", "--reach", "405", "--out-plan", str(w / "s2_core.json"), "--event", str(w / "event.json")]
        if a.seed:
            argv += ["--seed", a.seed]
        add("core_place", argv, w / "s2_core.json")
    cp_base = pre
    argv = py + [str(HERE / "leaf_refresh.py"), "run", cp_base, cur, str(w / "s3_refresh.json"), "--types", types, "--report", str(w / "refresh.json")]
    add("refresh", argv, w / "s3_refresh.json")
    argv = py + [str(HERE / "chain_resite.py"), "run", cur, str(w / "s4_resite.json"), "--types", types, "--ops", str(w / "resite_ops.json"),
                 "--report", str(w / "resite.json")] + (["--extra-reg"] if a.extra_reg else [])
    add("chain_resite", argv, w / "s4_resite.json")
    add("retap", py + [str(HERE / "leaf_grow.py"), "retap", cur, "--types", ty_re, "--any-type", "--out", str(w / "s5_retap.json")], w / "s5_retap.json")
    add("anchor", py + ["-u", "-B", str(HERE / "reset_anchor.py"), "record", cur, str(w / "s6_anchor.json"), "--types", types, "--repick",
                  "--root", a.tree],
        w / "s6_anchor.json")
    return st


def run_chain(a, run=subprocess.run):
    work = Path(a.work or (Path(a.out).parent / (Path(a.out).stem + "_work")))
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OT_REPO_ROOT=a.tree, OT_RT_CURRENT=a.tree,
               OT_PLAN_ROOT=str(Path(a.tree) / "physical/die_plan/s81"))
    st = steps(a, work)
    for name, argv, _, outp in st:
        print(f"== {name}: {' '.join(argv[2:6])} ...", flush=True)
        if a.dry:
            continue
        r = run(argv, cwd=a.tree, env=env)
        if r.returncode != 0:
            print(f"FAIL STEP {name} rc={r.returncode}")
            return 2
        if not Path(outp).exists():
            print(f"FAIL STEP {name}: no output {outp}")
            return 2
    if a.dry:
        return 0
    final = st[-1][3]
    os.environ.update(env)                      # the bind's own tap check reads the tree's views / plan dir
    os.chdir(a.tree)
    base_raw = json.loads(Path(a.base).read_text())
    new_raw = json.loads(Path(final).read_text())
    types = [t for t in a.types.split(",") if t]
    findings = schema_test(base_raw, new_raw, types, plan_path=final)
    for x in findings:
        print(x)
    Path(a.out).write_text(Path(final).read_text())
    print(f"leaf_generate: {len(findings)} schema findings -> {a.out}")
    return 1 if findings else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("base")
    ap.add_argument("--types", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--grow", type=float, default=0.0, help="W-face growth DX (um); 0 = no growth")
    ap.add_argument("--ft-xcut", type=float, default=0.0)
    ap.add_argument("--shift", type=float, default=0.0, help="SHIFT-IN-PLACE DX (um): outline and pin windows fixed, the core block moves east (instead of --grow)")
    ap.add_argument("--die-cap", type=float, default=None, help="with --grow: refuse DX above the die-level cap (t10: 155.52)")
    ap.add_argument("--tree", default="/srv/opentallas-scratch2/claude/s81-allfix-int/c9seal_tree")
    ap.add_argument("--seed")
    ap.add_argument("--extra-reg", action="store_true")
    ap.add_argument("--no-core-place", action="store_true", help="skip core_place (refresh/re-site/retap/anchor on an already placed plan)")
    ap.add_argument("--work")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    return run_chain(a)


if __name__ == "__main__":
    sys.exit(main())
