"""DIE-KV-6: strap_lec (MESO-STRAP-1, functions unchanged) on KV. Base = the bound pre-landing partition module captured
by bind_capture.py (KV types have no gen_rtl.wrapper form); leaf headers from the bind filelist (bind.f) + bind rtl/.
Gold = parameter form of the first copy of each variant (Lp, ca_variants), gate = strap master tied (Ls), as strap_lec.main.
usage: kv_strap_lec.py LANDED_PLAN SIDECAR CAPTURE_DIR BIND_OUT OUT [--types a,b] [--jobs N] [--mutant] [--timeout S]"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "tools" / "die_plan"))
import clock_landings as CL  # noqa: E402
import strap_lec as SL  # noqa: E402

ap = argparse.ArgumentParser()
for n in ("plan", "sidecar", "capture", "bind_out", "out"):
    ap.add_argument(n)
ap.add_argument("--types")
ap.add_argument("--jobs", type=int, default=8)
ap.add_argument("--mutant", action="store_true")
ap.add_argument("--timeout", type=int, default=5400)
ap.add_argument("--list", action="store_true")
ap.add_argument("--extra-libs", default="", help="comma list of extra leaf sources (hard-IP models, repo-relative)")
a = ap.parse_args()
raw = json.load(open(a.plan))
side = json.load(open(a.sidecar))
Ls = CL.Landings(raw, side)
sp = copy.deepcopy(side)
sp["count_aligned"]["strap_form"] = False
Lp = CL.Landings(raw, sp, ca_variants=True)
st = Ls.strap
want = a.types.split(",") if a.types else sorted(t for t, v in st["types"].items() if v["straps"])
if a.list:
    for tn in want:
        print(tn, len(SL.variants(st, tn)), len(st["types"][tn]["instances"]))
    sys.exit(0)
bo = Path(a.bind_out)
libs = [x for x in (bo / "bind.f").read_text().split() if x.endswith((".sv", ".v")) and Path(x).exists()]
libs += [str(p) for p in sorted((bo / "rtl").glob("*.sv"))]
libs += [str(p) for p in sorted(bo.glob("shim_*.sv"))]
libs += [str(R / x) for x in a.extra_libs.split(",") if x]  # bind-out shims (e.g. qkd_hbm3e_phy_pc4)
common = [str(R / f) for f in SL.COMMON]
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=True)
prepared, skipped = [], []
for tn in want:
    f = Path(a.capture) / f"{tn}.sv"
    if not f.exists():
        skipped.append(tn)
        continue
    base = f.read_text()
    mod = re.search(r"(?m)^\s*module\s+(\w+)", base).group(1)
    mylibs = [x for x in libs if Path(x).name != f"{mod}.sv"]
    try:
        prepared += SL.lec_type(Ls, Lp, tn, mod, base, mylibs, common, out, image="openroad/orfs:asap7lock",
                                timeout=a.timeout, mutant=a.mutant, run=False)
    except SystemExit as e:
        print("PREP_FAIL", tn, e, flush=True)
        skipped.append(tn)
print("prepared", len(prepared), "skipped (no captured base)", skipped, flush=True)
rows = SL.run_jobs(prepared, a.jobs)
eq = [r for r in rows if r["kind"] == "eq"]
rep = dict(schema="opentallas.strap_lec.v1", note="DIE-KV-6 KV driver (captured bound base)", plan=a.plan,
           landing=a.sidecar, types=want, skipped=skipped, variants=len(eq), equivalent=sum(r["equivalent"] for r in eq),
           copies_equivalent=sum(r["copies"] for r in eq if r["equivalent"]),
           mutants=sum(r["kind"] == "mutant" for r in rows),
           mutants_caught=sum(r["kind"] == "mutant" and r["pass"] for r in rows),
           verdict="PASS" if rows and all(r["pass"] for r in rows) and not skipped else "FAIL", rows=rows)
(out / "strap_lec.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps({k: v for k, v in rep.items() if k != "rows"}))
