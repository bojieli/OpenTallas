"""adv_tree_switch.py -- PRECHECK ADV-TREE-SWITCH (COORD 11-24, FABLE-RC-QC hub bc55ab84; the switch half of TREE-DRIFT; report only).

A row that sets a switch (partition_types.<t>.verilog_defines) which the bound tree's RTL never mentions is a SILENT NO-OP: the kit builds without it.
Per plan switch: SWITCH-NOOP when no tree rtl file contains the name.  DRIFT when main's rtl has it (files listed with line counts tree vs main, e.g. the QC tree's
ot_coll_tp8_static.sv 603 lines vs 659 on main: carry the file); UNDEFINED when main lacks it too (typo or RTL not pushed).  Switches the tree has are not listed;
files with a switch in both but different line counts are counted as DIFFERS.  kw tree (default: the tree above the plan), main_repo / main_ref as ADV-TREE-DRIFT.
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CHECK = "ADV-TREE-SWITCH"
MAX_LINES = 40
WORD = re.compile(r"OT_[A-Z0-9_]+")
EXT = (".sv", ".v", ".svh", ".vh")
TOOL_DIR = "tools/die_plan"     # generator-consumed switches (gen_phys / bind.py emit the RTL: OT_ST_QNALT, OT_DLY_CPL)


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def tree_index(tree):
    """-> ({switch: {rel file}}, {rel file: lines}) over tree/rtl and the generator files of tree/tools/die_plan"""
    sw, nl = defaultdict(set), {}
    base = Path(tree)
    walk = list(os.walk(base / "rtl"))
    td = base / TOOL_DIR
    if td.is_dir():
        walk.append((str(td), [], [f for f in os.listdir(td) if f.endswith(EXT + (".py",)) and not f.startswith("test_")]))
    for root, _d, files in walk:
        for fn in files:
            if fn.endswith(EXT + (".py",)):
                p = Path(root) / fn
                try:
                    s = p.read_text(errors="replace")
                except OSError:
                    continue
                rel = str(p.relative_to(base))
                nl[rel] = s.count("\n")
                for m in set(WORD.findall(s)):
                    sw[m].add(rel)
    return sw, nl


def main_index(gd, ref):
    import adv_unset_define as U
    sw = defaultdict(set)
    out = U._git(gd, ["grep", "-I", "-o", "-E", "OT_[A-Z0-9_]+", ref, "--", "rtl", f"{TOOL_DIR}/*.py", f"{TOOL_DIR}/*.sv"], 300)
    for ln in out.splitlines():
        parts = ln.split(":", 2)
        if len(parts) == 3 and not parts[1].rsplit("/", 1)[-1].startswith("test_"):
            sw[parts[2]].add(parts[1])
    return sw


def _findings(raw, plan_path, tree=None, **kw):
    import adv_tree_drift as T
    import adv_unset_define as U
    tree = tree or kw.get("tree") or T._find_tree(plan_path)
    if not tree or not (Path(tree) / "rtl").is_dir():
        return [_w("NOT-RUN: no bound tree with rtl/ (kw tree)")]
    gd, ref = T._repo_main(kw)
    if not gd:
        return [_w("NOT-RUN: no main repo (kw main_repo / OT_ADV_MAIN_REPO)")]
    have = U.plan_switches(raw)
    tsw, tnl = tree_index(tree)
    msw = main_index(gd, ref)
    out, noop, drift, undef, differs, dfiles, gen_ok = [], 0, 0, 0, 0, {}, []
    here = Path(__file__).resolve().parent                    # the tools this check runs from = the launch rt's tools
    for sw, tps in sorted(have.items()):
        if sw in tsw:
            for f in msw.get(sw, ()):
                if f in tnl and f not in dfiles and not T._is_tb(f) and f.startswith("rtl/"):
                    try:
                        if T._blob(str(Path(tree) / f)) == U._git(gd, ["rev-parse", f"{ref}:{f}"], 30).strip():
                            continue
                        mn = U._git(gd, ["show", f"{ref}:{f}"], 60).count("\n")
                    except Exception:  # noqa: BLE001
                        continue
                    dfiles[f] = (tnl[f], mn)
            continue
        files = sorted(msw.get(sw, ()))
        if files and all(f.startswith(TOOL_DIR + "/") for f in files):
            # generator-consumed (gen_phys / bind.py emit the RTL): kits run the launch rt's tools, not the tree copy
            if any(sw in (here / Path(f).name).read_text(errors="replace") for f in files
                   if not Path(f).name.startswith("adv_") and (here / Path(f).name).is_file()):
                gen_ok.append(sw)
                continue
        noop += 1
        if files:
            drift += 1
            desc = []
            for f in files[:3]:
                try:
                    mn = U._git(gd, ["show", f"{ref}:{f}"], 60).count("\n")
                except Exception:  # noqa: BLE001
                    mn = -1
                desc.append(f"{f} {'absent in tree' if f not in tnl else str(tnl[f]) + ' lines'} vs {mn} on main")
            out.append(_w(f"{sw}: SWITCH-NOOP+DRIFT set by {len(tps)} type(s) ({','.join(tps[:3]) or 'plan key'}) but the tree's RTL lacks it; main has it in " + "; ".join(desc)))
        else:
            undef += 1
            out.append(_w(f"{sw}: SWITCH-NOOP+UNDEFINED set by {len(tps)} type(s) ({','.join(tps[:3]) or 'plan key'}); neither the tree nor main rtl mentions it"))
    out = out[:MAX_LINES]
    differs = len(dfiles)
    for f, (a, b) in sorted(dfiles.items(), key=lambda kv: -abs(kv[1][1] - kv[1][0]))[:8]:
        out.append(_w(f"{f}: DIFFERS {a} lines in the tree vs {b} on main (carries a switch this plan sets; ADV-TREE-DRIFT rtl says LAG or LOCAL)"))
    out.append(_w("summary", f"{len(have)} switch(es) set by the plan; {noop} SWITCH-NOOP in the tree ({drift} DRIFT main has it, {undef} UNDEFINED); "
                  f"{len(gen_ok)} generator-consumed and present in the running rt tools ({','.join(gen_ok[:4])}); "
                  f"{differs} switch-carrying rtl file(s) differ from main (tb skipped); tree {tree} main {ref[:10]}"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
