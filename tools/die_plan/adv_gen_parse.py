#!/usr/bin/env python3
"""adv_gen_parse.py -- PRECHECK GEN-PARSE (KV-ALLFIX, COORD 11-25): run the gen-step parse / validation of every type in plan scope.

KV plan R6 (plan_a5t9_r6_publish_1125) passed PRE, G0 and the strict bind, yet its gen step raised for types of the plan:

  kv3_hg_v1p4, kv3_hg_v1p6   ValueError reg_leaf_split u_hst1_g: >= 2 copies needed         (reg_leaf_split.config, from gen_phys.write_type_kit)
  kv3_pc_v1__cl4ea58a5c__r8ef700d7c
                             ValueError invalid bound R8 count declaration: strap_r8pad_lane_i_hsl_Q_N_fo
                                                                                          (bound_r8_straps.project, from gen_phys.bound_parent_id_plan)

Nothing ran those parsers before the kit launched, so every such type was found one gen (a ot-run queue wait) late.  This check calls the
SAME functions, on the plan, without any synthesis or placement:

  reg_leaf_split.config(type)   the validated `reg_leaf_split` rows of each type (pure; no RTL needed)
  bound_r8_straps.project(...)  the bind's R8 pad / lane-count strap declarations against the plan count_straps widths.  It reads a
                                kit_rtl.json that only exists after the kit-rtl stage, so one is synthesized per type from the
                                bind manifest (bind_parent_id_straps.json rows of kind r8pad_strap, owning instances = the plan
                                partitions of the type); kit port widths are assumed equal to the manifest widths.  Needs the bind OUT
                                dir (kw bind_out, else found like ADV-PORT-PIN); without it the R8 half is reported as not checked.

The functions are the ones of the TREE the plan is published with (tree/tools/die_plan, run in a subprocess), since that is the code the
gen step will run: R6's tree had reg_leaf_split ">= 2 copies" and a bound_r8_straps without the lane-count widths, while main had both fixed.
Without a tree (or when the tree has no such tools dir) this module's own directory is used, in process.

Report only: lines are WARN (plan_advisory forces WARN).  OT_GEN_PARSE_BLOCK=1 makes them FAIL for a direct consumer.
findings(raw, plan_path, tree=None, **kw) -> lines, never raises.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CHECK = "GEN-PARSE"
HERE = Path(__file__).resolve().parent
TIMEOUT_S = int(os.environ.get("OT_GEN_PARSE_TIMEOUT_S", "100"))


def _scope(raw):
    """-> ({type: [partition names]}) of the types a kit is generated for: those with partitions; every type when the plan lists none"""
    pt = raw.get("partition_types") or {}
    inst = {}
    for p in raw.get("partitions") or []:
        if isinstance(p, dict) and p.get("type") in pt:
            inst.setdefault(p["type"], []).append(p.get("name"))
    if not inst:
        return {tn: [] for tn in pt}
    return inst


def _r8_rows(manifest, tn):
    return {n: r for n, r in ((manifest.get("types") or {}).get(tn) or {}).items()
            if isinstance(r, dict) and r.get("kind") == "r8pad_strap"}


def probe(raw, bind_out=None):
    """-> dict(rows=[(type, ExcType, message)], n_types, n_rls, n_r8, rls_tool, r8_tool, r8_note).  Imports reg_leaf_split / bound_r8_straps
    from sys.path (the caller puts the wanted tools dir first); never raises."""
    res = dict(rows=[], n_types=0, n_rls=0, n_r8=0, rls_tool=None, r8_tool=None, r8_note="")
    scope = _scope(raw)
    res["n_types"] = len(scope)
    pt = raw.get("partition_types") or {}
    try:
        import reg_leaf_split as RLS
        res["rls_tool"] = os.path.dirname(os.path.abspath(RLS.__file__))
    except Exception as e:  # noqa: BLE001
        RLS = None
        res["rows"].append(("(tools)", type(e).__name__, f"reg_leaf_split not importable: {str(e)[:150]}"))
    try:
        import bound_r8_straps as BRS
        res["r8_tool"] = os.path.dirname(os.path.abspath(BRS.__file__))
    except Exception as e:  # noqa: BLE001
        BRS = None
        res["rows"].append(("(tools)", type(e).__name__, f"bound_r8_straps not importable: {str(e)[:150]}"))
    manifest = None
    if BRS is not None:
        mf = Path(bind_out) / "bind_parent_id_straps.json" if bind_out else None
        if mf is not None and mf.is_file():
            try:
                manifest = json.loads(mf.read_text())
            except (OSError, ValueError) as e:
                res["r8_note"] = f"bind manifest unreadable: {type(e).__name__}"
        else:
            res["r8_note"] = "no bind OUT dir with bind_parent_id_straps.json (R8 declarations not checked)"
    for tn in sorted(scope):
        t = pt.get(tn)
        if not isinstance(t, dict):
            continue
        if RLS is not None:
            try:
                if RLS.config(t):
                    res["n_rls"] += 1
            except Exception as e:  # noqa: BLE001 the gen step would die here
                res["rows"].append((tn, type(e).__name__, str(e)[:300]))
        if manifest is not None and _r8_rows(manifest, tn):
            res["n_r8"] += 1
            try:
                with tempfile.TemporaryDirectory(prefix="gen_parse_") as d:
                    ports = [dict(port=n, dir="input", width=r.get("width")) for n, r in _r8_rows(manifest, tn).items()]
                    (Path(d) / "kit_rtl.json").write_text(json.dumps(dict(
                        type=tn, bound_type=tn, plan_type=tn, bind_out=str(bind_out), instances=list(scope[tn]), bound_only_pins=ports)))
                    (Path(d) / "x.f").write_text("")
                    light = dict(partition_types={tn: t}, partitions=[dict(name=q, type=tn) for q in scope[tn]])
                    BRS.project(light, {tn: str(Path(d) / "x.f")})
            except Exception as e:  # noqa: BLE001
                res["rows"].append((tn, type(e).__name__, str(e)[:300]))
    return res


def _worker(argv):
    """python3 -I adv_gen_parse.py --worker TOOLS PLAN BIND_OUT|- : the probe under the tree's tools, JSON on stdout"""
    tools, plan, bind_out = argv
    sys.path.insert(0, tools)
    raw = json.loads(Path(plan).read_text())
    print(json.dumps(probe(raw, None if bind_out == "-" else bind_out)))
    return 0


def _find_bind_out(raw, plan_path, tree, bind_out):
    try:
        sys.path.insert(0, str(HERE))
        from adv_port_pin import find_bind_out
        return find_bind_out(raw, plan_path, tree, bind_out)
    except Exception:  # noqa: BLE001
        return None
    finally:
        try:
            sys.path.remove(str(HERE))
        except ValueError:
            pass


def findings(raw, plan_path=None, tree=None, bind_out=None, **kw):
    lvl = "FAIL" if os.environ.get("OT_GEN_PARSE_BLOCK") == "1" else "WARN"
    t0 = time.time()
    try:
        bo = _find_bind_out(raw, plan_path, tree, bind_out)
        tools = Path(tree) / "tools" / "die_plan" if tree else None
        use_tree = bool(tools and (tools / "reg_leaf_split.py").is_file() and tools.resolve() != HERE and plan_path)
        if use_tree:
            p = subprocess.run([sys.executable, "-I", str(HERE / "adv_gen_parse.py"), "--worker", str(tools), str(plan_path), bo or "-"],
                               capture_output=True, text=True, timeout=TIMEOUT_S, stdin=subprocess.DEVNULL)
            if p.returncode != 0:
                return [f"WARN ADV-GEN-PARSE not checked: tree-tools worker exit {p.returncode}: {(p.stderr or p.stdout).strip()[-200:]}"]
            res = json.loads(p.stdout.strip().splitlines()[-1])
        else:
            sys.path.insert(0, str(HERE))
            try:
                res = probe(raw, bo)
            finally:
                try:
                    sys.path.remove(str(HERE))
                except ValueError:
                    pass
        out = [f"{lvl} ADV-GEN-PARSE {tn}: {exc} {msg}" for tn, exc, msg in res["rows"]]
        bad = len({r[0] for r in res["rows"]})
        out.append(f"WARN ADV-GEN-PARSE summary {bad} of {res['n_types']} type(s) fail the gen-step parse ({res['n_rls']} type(s) with valid reg_leaf_split rows, "
                   f"bound R8 {res['n_r8']} types checked; tools {res['rls_tool'] or '-'}; bind_out {bo or '-'}"
                   f"{'; ' + res['r8_note'] if res['r8_note'] else ''}; {time.time() - t0:.1f} s)")
        return out
    except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
        return [f"WARN ADV-GEN-PARSE not checked: {type(e).__name__}: {str(e)[:200]}"]


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--worker":
        sys.exit(_worker(sys.argv[2:]))
    print(__doc__)
