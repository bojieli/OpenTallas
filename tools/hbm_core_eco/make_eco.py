#!/usr/bin/env python3
"""Create a new HBM core warm ECO kit with real TT/FF modes and measured FF IO reference."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MM_SOURCE = "a8ff2dc39"
FF_SOURCE = "0fa24094d"
SIGNOFF_SOURCE = "32e1c492c"


def pinned(ref, name, dst):
    dst.write_bytes(subprocess.check_output(["git", "-C", str(REPO), "show", f"{ref}:{name}"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--contract", required=True, help="source-pinned measured boundary reference")
    ap.add_argument("--hold-margin", type=int, choices=range(0, 6), default=3)
    ap.add_argument("--drv-place", action="store_true")
    a = ap.parse_args()
    src, out = a.source.resolve(), a.out.resolve()
    if out.exists():
        raise SystemExit("output exists; preserve previous attempt and choose a new directory")
    rs, = (src / "run/results/asap7").glob("*/base")
    for f in ("5_2_route.odb", "6_final.spef"):
        if not (rs / f).is_file():
            raise SystemExit(f"missing routed checkpoint {rs / f}")
    out.mkdir(parents=True)
    for p in src.iterdir():
        if p.name in {"run", "views", "rc.txt"} or p.name.startswith(("signoff", "run_")):
            continue
        q = out / p.name
        if p.is_dir():
            shutil.copytree(p, q, symlinks=True)
        else:
            shutil.copy2(p, q)
    nick = rs.parent.name
    dst = out / "run/results/asap7" / nick / "base"
    dst.mkdir(parents=True)
    shutil.copy2(rs / "5_2_route.odb", dst / "4_cts.odb")
    for f in ("6_final.spef", "1_2_yosys.v", "1_synth.v", "clock_period.txt", "mem.json", "ot_face_flops.txt"):
        if (rs / f).is_file():
            shutil.copy2(rs / f, dst / f)
    objects = src / "run/objects/asap7" / nick / "base"
    if objects.is_dir():
        shutil.copytree(objects, out / "run/objects/asap7" / nick / "base")
    for typ in ("logs", "reports"):
        (out / "run" / typ / "asap7" / nick / "base").mkdir(parents=True)
    (dst / "4_cts.sdc").write_text((out / "constraint.sdc").read_text() + "\nset_propagated_clock [all_clocks]\n")
    for f in ("eco_route.tcl", "run_eco.sh"):
        shutil.copy2(HERE / f, out / f)
    for f in ("orfs_hold_mm.py", "orfs_hold_mm.tcl"):
        pinned(MM_SOURCE, "tools/" + f, out / f)
    pinned(FF_SOURCE, "tools/die_plan/core_ff_vclk.sdc", out / "core_ff_vclk.sdc")
    pinned(SIGNOFF_SOURCE, "tools/die_plan/signoff.py", out / "signoff.py")
    with (out / "config.mk").open("a") as f:
        f.write("\n# Real TT setup / FF hold; source-pinned opt-in boundary reference.\n")
        for k, v in dict(POST_GLOBAL_ROUTE_TCL="/work/eco_route.tcl", CORNER="TC", CORNERS="tc bc",
                         OT_HOLD_MM=1, OT_MM_SETUP_CORNER="TC", OT_FF_VCLK_MODE="pin_flop_mean",
                         OT_MM_FF_SDC="/work/core_ff_vclk.sdc", OT_MM_IOREF_FILE="/work/core_ff_vclk.sdc",
                         OT_FF_VCLK_CONTRACT=a.contract).items():
            f.write(f"export {k} = {v}\n")
    env = dict(OT_MAX_FANOUT=24, OT_SLEW_MARGIN=20, OT_SETUP_MARGIN=10,
               OT_HOLD_MARGIN=a.hold_margin, OT_HOLD_ALLOW_SETUP=0, OT_HOLD_MAXBUF=40,
               OT_DRV_LAST=int(not a.drv_place), OT_DRV_PLACE=int(a.drv_place), OT_RETIME_LAST=1)
    (out / "variant.env").write_text("".join(f"export {k}={v}\n" for k, v in env.items()))
    record = dict(source=str(src), freeze=json.loads((src / "freeze.json").read_text()),
                  contract=a.contract, mm_source=MM_SOURCE, ff_source=FF_SOURCE,
                  signoff_source=SIGNOFF_SOURCE, variant=env)
    (out / "ECO.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(dict(kit=str(out), contract=a.contract, variant=env)))


if __name__ == "__main__":
    main()
