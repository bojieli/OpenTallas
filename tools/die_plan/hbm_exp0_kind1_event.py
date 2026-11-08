"""HBM plan event EXP0-KIND1-1108 (DIE-HBM-92-SU-EXP 11-08, plan owner DIE-HBM-92 ruling GO): the four exp0 lane cores.

Plan d44v p18 part 42 names u_su_Q<q>_lane_exp0.u_fcore.u_core.u_l = ot_hbm_su_pg_lane_full_x_core (lane KIND 2 FULL,
354.24x207.36).  Every as-built su_N[EW][01] g_lane[0] is KIND 1 (HBM-044 (A): the side unit is removed), so the exact
bind regroup refuses it (parameter KIND=1 != sub-core KIND=2).  This event makes the exp0 u_l the KIND 1 core every
other lane_exp uses: ot_hbm_su_pg_lane_exp_x_core, 319.68x207.36, its existing one-clock pin table
cores/ot_hbm_su_pg_lane_exp_x_core__319.68x207.36__d44v_split__oneclk.json.  Origin, orientation, obs, parent ID
straps and the u_s core are unchanged (u_s keeps its site: the 34.56 um part-42 growth strip stays empty).

    hbm_exp0_kind1_event.py BASE_PLAN_DIR OUT_DIR     (OUT_DIR must not exist; cp -al, then only the changed files
                                                       die_plan.json(.gz), README.md, SHA256SUMS + the receipt are
                                                       removed and rewritten, never written through a hard link)
"""
import gzip
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

EVENT = "EXP0-KIND1-1108"
OLD, NEW = "ot_hbm_su_pg_lane_full_x_core", "ot_hbm_su_pg_lane_exp_x_core"
NEW_PINS = "cores/ot_hbm_su_pg_lane_exp_x_core__319.68x207.36__d44v_split__oneclk.json"
NEW_OUTLINE = [319.68, 207.36]
TYPES = ["q_su00", "q_su00__physical_v1", "q_su10", "q_su10__physical_v1"]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def edit(plan):
    changes = []
    for tn in TYPES:
        hs = [h for h in plan["partition_types"][tn]["hard_cores"] if h.get("module") == OLD]
        if len(hs) != 1 or not hs[0]["inst"].endswith("_lane_exp0__l"):
            raise SystemExit(f"{tn}: expected one {OLD} exp0 u_l, found {[h['inst'] for h in hs]}")
        h = hs[0]
        before = {k: h.get(k) for k in ("module", "physical_master", "outline_um", "pins_file")}
        h.update(module=NEW, physical_master=NEW, outline_um=list(NEW_OUTLINE), pins_file=NEW_PINS)
        h["note"] = (h.get("note", "") + f" | {EVENT} (DIE-HBM-92 GO 11-08): {OLD} -> {NEW} 319.68x207.36, the KIND 1 "
                     "core of every other lane_exp (as-built g_lane[0] is KIND 1, HBM-044 (A)); origin/orient/straps kept")
        changes.append(dict(type=tn, inst=h["inst"], before=before,
                            after={k: h.get(k) for k in ("module", "physical_master", "outline_um", "pins_file")}))
    left = [(tn, h["inst"]) for tn, t in plan["partition_types"].items() for h in t.get("hard_cores", []) or []
            if h.get("module") == OLD or h.get("physical_master") == OLD]
    if left:
        raise SystemExit(f"{OLD} still placed: {left}")
    return changes


def replace(path, data):
    """Remove (breaking any hard link) and write fresh."""
    if path.exists():
        path.unlink()
    path.write_bytes(data)


def main(base, out):
    base, out = Path(base), Path(out)
    if os.path.realpath(base) != str(base.resolve()) or base.is_symlink():
        raise SystemExit("base must be a real directory path")
    if any(p.is_symlink() for p in base.rglob("*")):
        raise SystemExit("base contains symlinks: cp -al would copy them, refusing")
    if out.exists():
        raise SystemExit(f"{out} exists")
    if not (base / NEW_PINS).is_file():
        raise SystemExit(f"missing {NEW_PINS}")
    pins = json.loads((base / NEW_PINS).read_text())
    if "lane_lane_id" not in json.dumps(pins):
        raise SystemExit(f"{NEW_PINS}: no lane_lane_id pin for the parent ID strap")
    subprocess.run(["cp", "-al", str(base), str(out)], check=True)
    src = (base / "die_plan.json").read_bytes()
    plan = json.loads(src)
    if json.dumps(plan, indent=1) + "\n" != src.decode():
        raise SystemExit("die_plan.json does not round-trip (indent 1)")
    changes = edit(plan)
    new = (json.dumps(plan, indent=1) + "\n").encode()
    replace(out / "die_plan.json", new)
    replace(out / "die_plan.json.gz", gzip.compress(new, mtime=0))
    receipt = dict(event=EVENT, lane="DIE-HBM-92-SU-EXP", ruling="DIE-HBM-92 11-08 exp0 GO",
                   plan_in=str(base / "die_plan.json"), sha_in=sha(src), sha_out=sha(new),
                   pins_file={NEW_PINS: sha((base / NEW_PINS).read_bytes())},
                   changed_types=TYPES, changed_top_level=[], changes=changes,
                   unchanged_note="u_s (sfu_s_core) sites, parent ID straps, clock_entries.json and core_macros.json "
                                  f"unchanged (their {OLD} rows are no longer referenced)")
    rj = f"{EVENT.lower().replace('-', '_')}_event.json"
    replace(out / rj, (json.dumps(receipt, indent=1) + "\n").encode())
    readme = (base / "README.md").read_text() + (
        f"\n## {EVENT} (DIE-HBM-92-SU-EXP 2026-11-08, plan owner DIE-HBM-92 GO)\n"
        f"plan_hbm_1108d ({sha(src)[:12]}) + {EVENT}: u_su_Q{{0,1}}_lane_exp0__l in {', '.join(TYPES)}: {OLD} 354.24x207.36 "
        f"-> {NEW} 319.68x207.36 ({NEW_PINS}); the as-built lane 0 is KIND 1 (HBM-044 (A)), so the exp0 core is the "
        f"same KIND 1 core as every other lane_exp; origin/orient/straps and u_s unchanged. die_plan.json sha256 "
        f"{sha(new)[:12]}. Receipt {rj}.\n")
    replace(out / "README.md", readme.encode())
    lines = (base / "SHA256SUMS").read_text().splitlines()
    hashes = {n: sha((out / n).read_bytes()) for n in ("die_plan.json", "die_plan.json.gz", "README.md", rj)}
    names = [ln.split(None, 1)[1].strip() for ln in lines]
    outl = [f"{hashes[n]}  {n}" if n in hashes else ln for ln, n in zip(lines, names)]
    outl += [f"{hashes[n]}  {n}" for n in hashes if n not in names]
    replace(out / "SHA256SUMS", ("\n".join(outl) + "\n").encode())
    print(json.dumps(dict(sha_in=sha(src), sha_out=sha(new), changed=[c["type"] + "/" + c["inst"] for c in changes],
                          rewritten=sorted(hashes) + ["SHA256SUMS"])))


if __name__ == "__main__":
    main(*sys.argv[1:3])
