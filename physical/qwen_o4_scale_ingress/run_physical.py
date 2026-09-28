#!/usr/bin/env python3
"""Synthesize a bounded matched ROM/HBM scale-ingress physical cut in ORFS.

Run inside the pinned openroad/orfs container with the bundle mounted at
/work. Both arms use the same 16 FP32 row-scale lanes, 0.92-ns clock,
240-by-240-um die outline and source capture; only the upstream scale source
changes. The HBM arm begins at a registered local 256-bit word, excluding
controller, PHY and stack power/area. Its input delay is explicitly 184 ps.
"""
from __future__ import annotations

import argparse
import glob
import subprocess
from pathlib import Path

ROOT = Path("/work")
PLATFORM = Path("/OpenROAD-flow-scripts/flow/platforms/asap7")
YOSYS = Path("/usr/local/bin/yosys")
OPENROAD = Path("/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad")
MACRO = ROOT / "physical/asap7_memory_macros/ot_rom_8192x266_m8"
RTL = [
    ROOT / "rtl/hdc/ot_hdc_delay.sv",
    ROOT / "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
    ROOT / "rtl/hdc/ot_hdc_fpu.sv",
    ROOT / "physical/qwen_o4_scale_ingress/ot_qwen_o4_scale_ingress_probe.sv",
]


def run(cmd: list[str], log: Path, *, env: dict[str, str] | None = None) -> None:
    import os

    with log.open("w") as f:
        subprocess.run(cmd, cwd=ROOT, env={**os.environ, **(env or {})},
                       stdout=f, stderr=subprocess.STDOUT, check=True)


def synth(arm: str, out: Path) -> None:
    libs = sorted(Path(p) for p in glob.glob(str(PLATFORM / "lib/NLDM/*RVT_TT_nldm*.lib*"))
                  if "FAKE" not in p)
    assert libs and all(p.is_file() for p in libs)
    seq = next(p for p in libs if "SEQ_RVT_TT" in p.name)
    lines = [f"read_liberty -lib {MACRO / 'ot_rom_8192x266_m8_tt.lib'}"]
    lines += [f"read_verilog -sv {p}" for p in RTL]
    lines += [
        f"chparam -set HBM_SOURCE {int(arm == 'hbm')} ot_qwen_o4_scale_ingress_probe",
        "hierarchy -check -top ot_qwen_o4_scale_ingress_probe",
        "synth -top ot_qwen_o4_scale_ingress_probe -flatten",
        f"dfflibmap -liberty {seq}",
        "abc " + " ".join(f"-liberty {p}" for p in libs) + " -D 920",
        "clean",
        "rename -unescape",
        f"write_verilog -noattr -noexpr {out / 'mapped.v'}",
    ]
    script = out / "synth.ys"
    script.write_text("\n".join(lines) + "\n")
    run([str(YOSYS), "-s", str(script)], out / "synth.log")
    # The mapped cells make net signedness irrelevant. OpenROAD's Verilog
    # reader rejects Yosys's signed generated-wire declarations.
    netlist = out / "mapped.v"
    text = netlist.read_text()
    netlist.write_text(text.replace("wire signed ", "wire "))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", choices=("rom", "hbm"), required=True)
    ap.add_argument("--stage", choices=("synth", "place", "route", "all"), default="all")
    args = ap.parse_args()
    out = ROOT / "out" / args.arm
    out.mkdir(parents=True, exist_ok=True)
    env = {"QWEN_SCALE_ARM": args.arm}
    if args.stage in ("synth", "all"):
        synth(args.arm, out)
    if args.stage in ("place", "all"):
        run([str(OPENROAD), "-exit", str(ROOT / "physical/qwen_o4_scale_ingress/place_route.tcl")],
            out / "place_route.log", env=env)
    if args.stage in ("route", "all"):
        run([str(OPENROAD), "-exit", str(ROOT / "physical/qwen_o4_scale_ingress/detailed_route.tcl")],
            out / "detailed_route.log", env=env)


if __name__ == "__main__":
    main()
