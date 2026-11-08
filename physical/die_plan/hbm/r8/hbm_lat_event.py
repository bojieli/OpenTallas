"""DIE-HBM-92-LAT 11-08: build the HBM latency plan event dir (re-runnable delta; F1 + F2 of the HBM latency event).

    python3 -I hbm_lat_event.py BASE_PLAN_DIR BUS_GROUPS.json ASBUILT.json OUT_DIR [--tools TOOLS/die_plan]

BASE_PLAN_DIR (e.g. plan_hbm_1108e) -> OUT_DIR as `cp -al` (hardlinks), then ONLY new files are written:
  r8/<die>_r8_landing.json   hbm_lat_pads.py table (R8 landing pads + LG loop equalisation), read by bind.py
                             asbuilt.land_align = "r8" from its default PLANDIR/r8/<die>_r8_landing.json
  r8/bus_groups_split.json   the bus groups with the contract's bus_sub splits (what r8.py check reads)
  r8/hbm_lat_contract.json, r8/hbm_lat_pads.py, lat/hbm_param_regen.py   frozen copies of the event code
  asbuilt_lat.json           ASBUILT + land_align "r8" + param_regen {file: OUT/lat/hbm_param_regen.py}: the as-built
                             manifest every bind / kit of this plan uses (bind.py --asbuilt)
  lat_1108_event.json        receipt (inputs + output sha256, loop table)
and README.md / SHA256SUMS are unlinked and rewritten (never written in place: they are hardlinks of BASE).
die_plan.json is NOT changed (the event is pads + parameters, no geometry).  BUS_GROUPS must come from a bind of
BASE/die_plan.json with ASBUILT (no pads): bind.py then checks every table member (R8_STALE / R8_UNCOVERED).
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("bus_groups")
    ap.add_argument("asbuilt")
    ap.add_argument("out")
    ap.add_argument("--tools", default=str(REPO / "tools" / "die_plan"))
    ap.add_argument("--event", default="LAT-1108")
    ap.add_argument("--contract", default=str(HERE / "hbm_lat_contract.json"))
    a = ap.parse_args(argv)
    base, out = Path(a.base), Path(a.out)
    if base.is_symlink() or Path(os.path.realpath(base)) != base.absolute():
        sys.exit(f"{base}: base must be a real directory path, not a symlink (realpath {os.path.realpath(base)})")
    if out.exists() or out.is_symlink():
        sys.exit(f"{out}: exists; the event is built into a NEW dir")
    for p in base.rglob("*"):
        if p.is_symlink():
            sys.exit(f"{p}: symlink inside the base plan dir; cp -al would share its target")
    subprocess.run(["cp", "-al", str(base), str(out)], check=True)
    for d in ("r8", "lat"):
        if (out / d).exists():
            sys.exit(f"{out / d}: already in the base plan dir")
        (out / d).mkdir()
    contract = Path(a.contract)
    shutil.copyfile(contract, out / "r8" / "hbm_lat_contract.json")
    shutil.copyfile(HERE / "hbm_lat_pads.py", out / "r8" / "hbm_lat_pads.py")
    shutil.copyfile(HERE.parent / "bind" / "hbm_param_regen.py", out / "lat" / "hbm_param_regen.py")
    r = subprocess.run([sys.executable, "-I", str(out / "r8" / "hbm_lat_pads.py"), str(out / "die_plan.json"),
                        a.bus_groups, str(out / "r8" / "hbm_lat_contract.json"), "--out", str(out / "r8"),
                        "--tools", a.tools], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode:
        sys.exit(f"hbm_lat_pads.py failed rc={r.returncode}\n{r.stderr}")
    die = json.loads((out / "die_plan.json").read_text())["die"]["name"]
    table = out / "r8" / f"{die}_r8_landing.json"
    ab = json.loads(Path(a.asbuilt).read_text())
    for k in ("land_align", "land_r8", "param_regen"):
        if k in ab:
            sys.exit(f"{a.asbuilt}: already has asbuilt.{k}; the event expects the plain manifest")
    ab["land_align"] = "r8"
    ab["land_r8"] = str(table.absolute())
    ab["param_regen"] = dict(file=str((out / "lat" / "hbm_param_regen.py").absolute()),
                             contract=str((out / "r8" / "hbm_lat_contract.json").absolute()))
    ab["lat_note"] = (f"DIE-HBM-92-LAT {a.event}: {Path(a.asbuilt).name} + R8 landing pads (land_align r8, "
                      f"{table.name}) + HBM fixed-latency param_regen hook")
    (out / "asbuilt_lat.json").write_text(json.dumps(ab, indent=1) + "\n")
    tj = json.loads(table.read_text())
    new = ["r8/hbm_lat_contract.json", "r8/hbm_lat_pads.py", "r8/bus_groups_split.json", f"r8/{table.name}",
           "lat/hbm_param_regen.py", "asbuilt_lat.json"]
    rec = dict(schema="opentallas.hbm_plan_event.v1", event=a.event, lane="DIE-HBM-92-LAT",
               tag=f"DIE-HBM-92-LAT {a.event}: HBM R8 landing pads + fixed-latency loop equalisation + param_regen",
               base=str(base.absolute()), out=str(out.absolute()), die=die,
               die_plan_sha256=sha(out / "die_plan.json"), die_plan_changed=False,
               inputs=dict(bus_groups=dict(path=str(Path(a.bus_groups).absolute()), sha256=sha(a.bus_groups)),
                           asbuilt=dict(path=str(Path(a.asbuilt).absolute()), sha256=sha(a.asbuilt)),
                           tools=a.tools),
               builder=f"physical/die_plan/hbm/r8/hbm_lat_event.py {a.base} {a.bus_groups} {a.asbuilt} {a.out}",
               summary=tj["summary"], loops=[dict(family=x["family"], rt_added=x["rt_added"]) for x in tj["loops"]],
               legs=tj["legs"], errors=tj["errors"], files={f: sha(out / f) for f in new})
    (out / "lat_1108_event.json").write_text(json.dumps(rec, indent=1) + "\n")
    new.append("lat_1108_event.json")
    readme = out / "README.md"
    old = readme.read_text() if readme.exists() else ""
    readme.unlink(missing_ok=True)
    readme.write_text(
        f"# HBM plan event {a.event} (DIE-HBM-92-LAT, 2026-11-08): R8 landing pads + fixed-latency param_regen\n\n"
        f"Base: `{base}` (die_plan.json sha256 {rec['die_plan_sha256']}, unchanged). Builder:\n"
        f"`{rec['builder']}`.\n\n"
        "Bind / kit every type of this plan with `--asbuilt asbuilt_lat.json` (land_align r8 on "
        f"`r8/{table.name}` + the `lat/hbm_param_regen.py` hook). Receipt: `lat_1108_event.json`.\n\n"
        "---\n\n" + old)
    sums = out / "SHA256SUMS"
    keep = []
    if sums.exists():
        for ln in sums.read_text().splitlines():
            f = ln.split(None, 1)[1].lstrip("*") if len(ln.split(None, 1)) == 2 else None
            if f and f != "README.md" and f not in new:
                keep.append(ln)
        sums.unlink()
    lines = keep + [f"{sha(out / f)}  {f}" for f in ["README.md"] + new]
    sums.write_text("\n".join(lines) + "\n")
    r = subprocess.run(["sha256sum", "-c", "--quiet", "SHA256SUMS"], cwd=out, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"SHA256SUMS check failed:\n{r.stdout}{r.stderr}")
    print(f"EVENT {out}: die_plan {rec['die_plan_sha256'][:12]} table {sha(table)[:12]} "
          f"SHA256SUMS {sha(sums)} errors {len(tj['errors'])}")
    return 1 if tj["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
