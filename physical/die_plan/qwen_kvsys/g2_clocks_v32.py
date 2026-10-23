#!/usr/bin/env python3
"""KV-P3b 10-23: G2 die probe of plan v3.2 WITH the non-core clock regions and the plan reset root (clocks_v32.json).

The die_plan schema carries one clock (clk_core) and a die-pin reset, so tools/die_plan/g2.py die routes only those.
This wrapper builds the standard g2 die probe (same tracks, partition M1..M7 blockages, die PG M8/M9 obstructions) and
adds, on the same die layers and in the same GRT run:
  - one spine net per non-core region of clocks_v32.json: root pin at the hub_C PLL (the core spine root, offset one
    lattice step per clock so no two root pins coincide, PG-free), one tap per consuming partition at the partition's
    core clock tap moved k x 17.28 um along x (k = clock index; snapped like gen_phys.tap_points), M9 pins;
  - the reset spine re-rooted at the plan reset source hub_Wi (host.die_rst_n), plus the power-on reset net die pin ->
    hub_Wi's reset tap only (clocks_v32.json reset_root).
Reports overflow per layer and OT_REACH per net (root -> tap Manhattan max / p90).  Diagnostic only, never writes the plan.

    python3 g2_clocks_v32.py die_plan.json clocks_v32.json --out DIR [--mem 64] [--run]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
import g2  # noqa: E402
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

STEP = 8.64


def snap(v, L):
    return round(L["offset_um"] + round((v - L["offset_um"]) / L["pitch_um"]) * L["pitch_um"], 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("clocks")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mem", type=int, default=64)
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    P = S.Plan(S.load(a.plan))
    C = json.load(open(a.clocks))
    out = g2.die_probe(P, a.out, a.mem)
    die_l = P.layer_budget["die_layers"]
    L9, L8 = P.layers[die_l[-1]], P.layers[die_l[0]]
    Lb = P.layers[P.layer_budget["partition_signal_max"]]
    sz9 = "{0.04 0.32}" if L9["dir"] == "V" else "{0.32 0.04}"
    sz8 = "{0.04 0.32}" if L8["dir"] == "V" else "{0.32 0.04}"

    def pin_xy(x, y, L):          # on a track crossing of L and the partition top layer
        return (snap(x, L), snap(y, Lb)) if L["dir"] == "V" else (snap(x, Lb), snap(y, L))

    add, reach, nets = [], [], {}
    for k, r in enumerate(C["regions"], start=1):
        root = r["spine"]["root_um"]
        rx = gen_phys.pg_free(P, die_l[-1], root[0] + 2 * k * STEP) if L9["dir"] == "V" else root[0] + 2 * k * STEP
        ry = root[1] if L9["dir"] == "V" else gen_phys.pg_free(P, die_l[-1], root[1])
        taps = []
        for part in sorted(r["taps"]):
            ck, _ = gen_phys.tap_points(P, P.parts[part]["type"])
            w, h = P.ptype(part)["outline_um"]
            tx = ck[0] + 2 * k * STEP if ck[0] + 2 * k * STEP < w - 1 else ck[0] - 2 * k * STEP
            taps.append((part, pin_xy(*P.to_die(part, (tx, ck[1])), L9)))
        nets[r["name"]] = ((rx, ry), taps, die_l[-1], sz9)
    # reset spine re-rooted at hub_Wi (host.die_rst_n) and the POR pin -> hub_Wi only
    src = C["reset_root"]["source"]["part"]
    _, rs_src = gen_phys.tap_points(P, P.parts[src]["type"])
    rroot = pin_xy(*P.to_die(src, (rs_src[0] + 2 * STEP, rs_src[1])), L8)
    rtaps = []
    for part in sorted(P.parts):
        _, rs = gen_phys.tap_points(P, P.parts[part]["type"])
        rtaps.append((part, P.to_die(part, rs)))
    por_root = {n: (x, y) for n, _, x, y in gen_phys.die_root_pins(P)}["rst_n"]
    nets["rst_plan"] = (rroot, rtaps, die_l[0], sz8)
    nets["por"] = (por_root, [(src, pin_xy(*P.to_die(src, (rs_src[0] - 2 * STEP, rs_src[1])), L8))], die_l[0], sz8)
    for net, (root, taps, L, sz) in nets.items():
        add.append(f"set n [odb::dbNet_create $block {net}_spine]")
        add.append(f"set b [odb::dbBTerm_create $n {net}_root]; $b setIoType INPUT")
        add.append(f"place_pin -pin_name {net}_root -layer {L} -location {{{root[0]:.4f} {root[1]:.4f}}} -pin_size {sz}")
        for part, (x, y) in taps:
            add.append(f"set b [odb::dbBTerm_create $n {net}_tap_{part}]; $b setIoType OUTPUT")
            add.append(f"place_pin -pin_name {net}_tap_{part} -layer {L} -location {{{x:.3f} {y:.3f}}} -pin_size {sz}")
        ds = sorted(abs(x - root[0]) + abs(y - root[1]) for _, (x, y) in taps)
        reach.append(f'puts "OT_REACH {net} max {ds[-1]:.1f} p90 {ds[int(0.9 * (len(ds) - 1))]:.1f} n {len(ds)}"')
    # the plan's die-pin reset spine is replaced by rst_plan: drop the g2 rst net (its pins and its reach line)
    tcl = (out / "probe.tcl").read_text().splitlines()
    keep = [ln for ln in tcl if "rst_spine" not in ln and "rst_root" not in ln and "rst_tap_" not in ln
            and not ln.startswith('puts "OT_REACH rst ')]
    i = next(j for j, ln in enumerate(keep) if ln.startswith("create_obstruction"))
    j = next(j for j, ln in enumerate(keep) if ln.startswith("set_routing_layers"))
    keep = keep[:i] + add + keep[i:j] + reach + keep[j:]
    (out / "probe.tcl").write_text("\n".join(keep) + "\n")
    meta = json.loads((out / "probe.json").read_text())
    meta.update(kind="g2-die-clocks", clocks=a.clocks, extra_nets={n: len(v[1]) for n, v in nets.items()},
                note="core clk spine as g2; die-pin rst spine replaced by rst_plan (root hub_Wi) + por; non-core "
                     "regions from clocks_v32.json; virtual connectivity/PG/reach only, not CTS/STA")
    (out / "probe.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(out)
    if a.run:
        subprocess.run(["bash", str(out / "run.sh")], check=False)
        print((out / "grt.json").read_text() if (out / "grt.json").exists() else "no grt.json")


if __name__ == "__main__":
    main()
