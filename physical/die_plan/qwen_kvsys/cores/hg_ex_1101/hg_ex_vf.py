#!/usr/bin/env python3
"""KV-HG-SPLIT-1 11-12: the vF HG-EX plan event (cell cap class: kv3_hg family 420-486k native cells > 400k).

    python3 -I hg_ex_vf.py VF_PLAN VF_SIDECAR OUTDIR [--hard 1,2,3]

1. plan_cut.apply(--hard 1,2,3, soft master qkd_astk_ex_s_soft): EX 1..3 of every HG type become hard cores with the
   SIGNED qkd_astk_ex_s_hg1101 view (190.08x112.32, 0 added cycles); EX 0 stays soft as a kit-local renamed exact copy
   (soft_clones).  Fails closed on any band / hard core / station / tap / reset tap under a new core.
2. the reset trees of the 8 HG types are re-solved by the current tools (reset_tree.for_type pushes relays off the new
   cores; the 3 new core taps are new tap sinks) and republished as landing collector_tree in the plan AND the
   sidecar (added_tap_recentre.republish: refuses a type whose sidecar tree differs from the published one).
3. collector_reattach.py BASE CAND OUT: collector sources follow the re-solved relays (same depth, <= 405 um), sidecar
   too; any reach miss -> exit 1, no output.
Writes OUTDIR = a copy of the plan dir with plan_c.json, eW_sidecar.json, pins/qkd_astk_ex_s_hg1101.json replaced/added
+ hg_ex_vf_report.json.  The die clock
islands removed under the new cores are listed in the report (die clock owner re-sites those cells; the 96 new core
taps are new die clock sinks).  Plan arithmetic only: UNCHECKED until G0 + strict bind.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "tools/die_plan"))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("hg_ex_plan_cut", HERE / "plan_cut.py")  # tools/die_plan has a plan_cut too
plan_cut = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan_cut)


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("plan")
    a.add_argument("sidecar")
    a.add_argument("out")
    a.add_argument("--hard", default="1,2,3")
    a.add_argument("--soft-master", default="qkd_astk_ex_s_soft")
    a = a.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        raise SystemExit(f"{out} exists (fresh OUTDIR only)")
    # a full copy of the plan dir (pins_file and other plan references are relative to the plan file)
    shutil.copytree(Path(a.plan).resolve().parent, out, symlinks=False)
    pins = out / "pins"
    for f in (out / "plan_c.json", out / "eW_sidecar.json", pins / Path(plan_cut.PIN_FILE).name):
        f.unlink(missing_ok=True)       # copies may be read-only; these three are rewritten below
    raw = json.load(open(a.plan))
    cut, types, resite = plan_cut.apply(raw, [int(x) for x in a.hard.split(",")], a.soft_master)
    (pins / Path(plan_cut.PIN_FILE).name).write_text(json.dumps(plan_cut.pins(), indent=1) + "\n")
    cand = out / "plan_cut.json"
    cand.write_text(json.dumps(cut, indent=1) + "\n")
    import schema as S
    import added_tap_recentre as ATR
    side = json.load(open(a.sidecar))
    P = S.Plan(json.loads(cand.read_text()), str(cand))
    rep = dict(schema="opentallas.kv.hg_ex_vf.v1", base_plan=str(Path(a.plan).resolve()), hard=a.hard,
               soft_master=a.soft_master, types=types, resite=resite, republish={})
    for tn in types:
        b, n, moved = ATR.republish(P, cut, tn, side)
        rep["republish"][tn] = dict(relays_before=b, relays_after=n, relays_changed=moved)
    cand2 = out / "plan_cut_rt.json"
    cand2.write_text(json.dumps(cut, indent=1) + "\n")
    side2 = out / "sidecar_rt.json"
    side2.write_text(json.dumps(side, indent=1) + "\n")
    r = subprocess.run([sys.executable, "-I", str(REPO / "tools/die_plan/collector_reattach.py"), a.plan, str(cand2),
                        str(out / "plan_c.json"), str(out / "collector_reattach.json"),
                        "--sidecar", str(side2), str(out / "eW_sidecar.json")], capture_output=True, text=True)
    rep["collector_reattach"] = dict(rc=r.returncode, tail=(r.stdout + r.stderr)[-2000:])
    (out / "hg_ex_vf_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print("HG_EX_VF", len(types), "types; reattach rc", r.returncode, "; resite rows", len(resite))
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
