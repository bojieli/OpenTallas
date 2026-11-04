#!/usr/bin/env python3
"""HBM-RF1 RE-FORM class 4 (DIE-HBM-61/MEM 55c4a61894a): gen_core_kit_hbm.py with the plan's mem_recipe_delta.json.

  gen_core_kit_hbm_rw.py [--rw-recipe-delta <plan dir>/mem_recipe_delta.json] <gen_core_kit_hbm.py arguments>

Opt-in.  Without --rw-recipe-delta this execs gen_core_kit_hbm.py with the same argv, so the kit is unchanged.  A kit
wave die can therefore point its core_kit gen_cmd here and pass the flag only in the item_args of the RE-FORM MEM cores.

With the flag, the view's module must have an entry in the delta (otherwise RW_RECIPE_DELTA fails closed).  Its
recipe (resolved as gen_core_kit_hbm.main resolves it) gets:
  - defines += defines_add (OT_HBM_RW_MACROS, the RTL ifdef that selects the right-width r0c0 SRAM leaves);
  - macros  := the delta's macro list (physical/asap7_memory_macros_v2);
  - rw_recipe_delta = {file, sha256, module}, so freeze.json recipe_sha256 records the change.
The delta's inst_rename rows are the RTL generate scopes the define selects; they are not a recipe field.  A RW core
whose plan core_macros.json has KNOWN rects names the renamed instances already (keybuf_slice, d44v part 2d); a RW
core without KNOWN rects (hfd_ep_static, host_cp_rxs in d44v) runs with --core-macros off (RTL macro placement).
"""
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_core_kit_hbm.py"
FLAG = "--rw-recipe-delta"


def patched_recipe(rec, entry, delta_path, module):
    """the RW form of recipe REC from one mem_recipe_delta.json ENTRY"""
    if not entry.get("defines_add") or not entry.get("macros"):
        raise SystemExit(f"RW_RECIPE_DELTA {module}: entry needs defines_add and macros")
    r = dict(rec)
    old = list(rec.get("defines") or [])
    r["defines"] = old + [d for d in entry["defines_add"] if d not in old]
    r["macros"] = list(entry["macros"])
    r["rw_recipe_delta"] = dict(file=str(delta_path), sha256=hashlib.sha256(Path(delta_path).read_bytes()).hexdigest(),
                                module=module, macros_before=list(rec.get("macros") or []))
    return r


def recipe_key(G, R, v, argv):
    """the recipe key gen_core_kit_hbm.main picks for view V (same order: --recipe-key, recipes_b2 module, the view's
    recipe_keys[0], the recipe whose top is the module)"""
    module = v["module"]
    rk = argv[argv.index("--recipe-key") + 1] if "--recipe-key" in argv[:-1] else None
    b2 = G.HERE / "recipes_b2.json"
    rk = rk or (module if module in R and b2.is_file() and module in json.load(open(b2)) else None) or \
        (v["recipe_keys"][0] if v.get("recipe_keys") else None)
    if not rk:
        rk, _ = G.resolve_recipe_by_top(module, R)
    if not rk or rk not in R:
        raise SystemExit(f"RW_RECIPE_DELTA NO_RECIPE {v['view']}")
    return rk


def main(argv):
    if FLAG not in argv[:-1]:
        os.execv(sys.executable, [sys.executable, str(GEN), *argv])
    i = argv.index(FLAG)
    delta_path = Path(argv[i + 1]).resolve()
    rest = argv[:i] + argv[i + 2:]
    if FLAG in rest:
        raise SystemExit(f"{FLAG} given twice")
    for k in ("--views", "--view"):
        if k not in rest[:-1]:
            raise SystemExit(f"{k} required")
    delta = json.loads(delta_path.read_text())
    sys.path.insert(0, str(HERE))      # the generator imports its sibling modules by name
    spec = importlib.util.spec_from_file_location("gen_core_kit_hbm", GEN)
    G = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(G)
    view = rest[rest.index("--view") + 1]
    v = next((x for x in json.load(open(rest[rest.index("--views") + 1]))["view_list"] if x["view"] == view), None)
    if v is None:
        raise SystemExit(f"view {view} not in the views file")
    module = v["module"]
    entry = delta.get(module)
    if not isinstance(entry, dict):
        raise SystemExit(f"RW_RECIPE_DELTA {module}: no entry in {delta_path} (entries: "
                         f"{sorted(k for k in delta if not k.startswith('_'))})")
    R = G.load_recipes()
    rk = recipe_key(G, R, v, rest)
    rec = patched_recipe(R[rk], entry, delta_path, module)
    print(f"RW_RECIPE_DELTA {module} recipe {rk}: defines {rec['defines']} macros {rec['macros']}")
    sys.argv = [str(GEN), *rest]
    G.main(recipe_overrides={rk: rec})


if __name__ == "__main__":
    main(sys.argv[1:])
