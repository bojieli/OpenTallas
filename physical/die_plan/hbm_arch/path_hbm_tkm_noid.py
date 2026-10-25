#!/usr/bin/env python3
"""PATH-HBM TKM tile ID drop + __strap module names (COORD ruling (4) 2026-10-25 14:44 on Codex deaa633922): the TKM
tile core's tile_tid input has no loads (ot_hgi_coll_tkm_tile_e86.tid is declared and never read), so the port is
DROPPED -- no dead pins, straps exist only where an ID is used -- and the plan names the converted kit modules
(<old>__strap, kit_static_ids.py).  Plan delta:
  * the 31 common tiles -> ot_hgi_coll_tkm_tp192_tile_core__idpin__strap, tile31 -> ..._terminal_idpin__strap
    (hard_cores[].module, clock taps[].budget_owner);
  * parent_id_straps removed from the 32 TKM tiles (no ID port left);
  * the 6 strap_tile_tid pins removed from both TKM tile pin tables (every other pin unchanged).

    python3 path_hbm_tkm_noid.py --src <plan dir> --out <new plan dir>
"""
import argparse, json, os, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import path_hbm_b2p as PB  # noqa: E402
import schema as S  # noqa: E402

OLD = {PB.TILE_M: PB.TILE_M + "__strap", PB.TERM_M: PB.TERM_M + "__strap"}
PORT = "strap_tile_tid"


def apply(plan, out):
    T = plan["partition_types"]["root"]
    rep = dict(renamed=0, straps_removed=0, pins_removed={}, budget_owner=0)
    files = set()
    for h in T["hard_cores"]:
        if h.get("module") not in OLD:
            continue
        h["module"] = OLD[h["module"]]
        rep["renamed"] += 1
        st = h.pop("parent_id_straps", None)
        if st is not None:
            if set(st) != {PORT}:
                raise ValueError(f"{h['inst']}: unexpected straps {sorted(st)}")
            rep["straps_removed"] += 1
        if "straps" in h:
            raise ValueError(f"{h['inst']}: core straps present")
        files.add(h["pins_file"])
    if rep["renamed"] != 32 or rep["straps_removed"] != 32:
        raise ValueError(f"expected 32 TKM tiles renamed and unstrapped, got {rep}")
    for tp in T["clock"]["taps"]:
        if tp.get("budget_owner") in OLD:
            tp["budget_owner"] = OLD[tp["budget_owner"]]
            rep["budget_owner"] += 1
    for rel in sorted(files):
        p = out / rel
        pins = json.loads(p.read_text())
        keep = [q for q in pins if not q["name"].startswith(PORT + "[") and q["name"] != PORT]
        if len(pins) - len(keep) != 6:
            raise ValueError(f"{rel}: expected 6 {PORT} pins, found {len(pins) - len(keep)}")
        if p.is_symlink():
            p.unlink()
        p.write_text(json.dumps(keep) + "\n")
        rep["pins_removed"][rel] = dict(removed=6, pins=len(keep), sha256=PB.sha(p))
    return rep


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--src", required=True)
    a.add_argument("--out", required=True)
    x = a.parse_args()
    src, out = Path(x.src), Path(x.out)
    if out.exists():
        raise ValueError("new output directory required")
    out.mkdir(parents=True)
    for p in src.iterdir():
        if p.name.startswith("g0") or p.name.startswith("gates") or p.name == "die_plan.json" or p.suffix in (".log", ".exit"):
            continue
        if p.is_symlink():
            os.symlink(os.readlink(p), out / p.name)
        elif p.is_dir():
            shutil.copytree(p, out / p.name, symlinks=True)
        else:
            shutil.copy2(p, out / p.name)
    plan = json.loads((src / "die_plan.json").read_text())
    rep = apply(plan, out)
    plan["note"] = plan.get("note", "") + " | PATH-HBM TKMNOID: TKM tile ID port dropped (no loads), __strap kit modules"
    S.Plan(plan, out / "die_plan.json")
    (out / "die_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    rep.update(src=str(src), src_plan_sha256=PB.sha(src / "die_plan.json"), out_plan_sha256=PB.sha(out / "die_plan.json"))
    (out / "tkm_noid_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
