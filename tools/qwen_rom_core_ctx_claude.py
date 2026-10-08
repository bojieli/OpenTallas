#!/usr/bin/env python3
"""Prepare the Qwen ROM decode core (final DEC_LA "h", optional zero-latency issue fallbacks) for an in-context route.

Same cut as results/rtl/qwen_rom_core_takeover_20261005 (controller_cut): the three units (ME spine, vector stream,
stream) are black-boxed and exposed, synthesised without ABC, and every interface port that touches no cell (the
pass-through ROM/data buses between memories and units) is removed by tools/qwen_rom_core_controller_cut.py, so the
route carries the core's real logic and every port that reaches it.  Parameters: the retained AR screen's (VPOS 0,
DEC_LA 1, the P8191 plain-AR build's G/NW/SMIN/TCUT/...).

Usage: qwen_rom_core_ctx_claude.py --out DIR [--fallback N]   (writes DIR/core.sv, DIR/gen/ot_hdc_vstream_rt.sv,
DIR/prepare.ys; run Yosys on prepare.ys -> DIR/original.json, then the controller cut)."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_rom_core_dec_emit_w12 as E  # noqa: E402
import qwen_rom_core_issue_fallback_w12 as FB  # noqa: E402

RETAINED = ROOT / "results/rtl/qwen_rom_core_takeover_20261005/retained_screen/synth.ys"
OLDROOT = "/srv/opentallas-scratch/claude/qwen-core-decode/src/"


def core_text(fallback: int, vpos: int, bound: bool = False, amq: bool = False, nxreg: bool = False,
              meif: bool = False) -> str:
    s = E.emit(E.V.E.CORE.read_text())
    if bound:   # Codex DEC_LA_BOUND: E2 remainder table width ODD*2^H-1 (exact; tools/qwen_rom_core_dec_bound_emit_w12.py)
        import qwen_rom_core_dec_bound_emit_w12 as BD
        s = BD.apply(s)
    s = FB.apply(s, fallback)
    if amq:
        s = FB.apply_amq(s)
    if fallback >= 3:
        s = FB.apply_start(s)
    if nxreg:
        s = FB.apply_nxreg(s)
    if meif:
        s = FB.apply_meif(s)
    # Yosys 0.68 workarounds of the retained screen copy (logic identical).
    s = s.replace("    generate if (VPOS != 0) begin : g_vpos_tiles\n        genvar vpt;\n",
                  "    genvar vpt;\n    generate if (VPOS != 0) begin : g_vpos_tiles\n")
    for old, new in [("    wire [NW-1:0] dynp_tiles_zero [0:7];\n", "    wire [8*NW-1:0] dynp_tiles_zero_f;\n"),
                     (".rounds(dynp_tiles_zero[vpt])", ".rounds(dynp_tiles_zero_f[vpt*NW +: NW])"),
                     ("<= dynp_tiles_zero[vpo];", "<= dynp_tiles_zero_f[vpo*NW +: NW];")]:
        assert s.count(old) == 1, old
        s = s.replace(old, new)
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fallback", type=int, default=0, help="0 none, 1 issue copies, 2 = 1 + one-hot chase select")
    ap.add_argument("--vpos", type=int, default=0)
    ap.add_argument("--bound", action="store_true", help="also DEC_LA_BOUND (narrow la_lo remainder table)")
    ap.add_argument("--amq", action="store_true", help="also DEC_LA_AMQ (argmax boundary register, +1 cycle per END)")
    ap.add_argument("--nxreg", action="store_true", help="also DEC_LA_NXREG (NEXT fields registered at the boundary)")
    ap.add_argument("--meif", action="store_true", help="also DEC_LA_MEIF (registered ME-spine handshake)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / "gen").mkdir()
    core = core_text(a.fallback, a.vpos, a.bound, a.amq, a.nxreg, a.meif)
    (a.out / "core.sv").write_text(core)
    (a.out / "gen/ot_hdc_vstream_rt.sv").write_text(E.E.emit_vstream(E.E.VSTREAM.read_text()))
    lines = []
    for line in RETAINED.read_text().splitlines():
        if line.startswith(("dfflibmap", "abc ", "setundef", "splitnets", "tee ", "write_verilog")):
            continue
        if line.startswith("read_verilog "):
            f = line.split()[-1].removeprefix(OLDROOT)
            if f.startswith("gen/ot_qwen_rom_core_scr_"):
                sel = a.out / "core.sv"
            elif f.startswith("gen/"):
                sel = a.out / f
            else:
                sel = ROOT / f
            assert sel.is_file(), sel
            lines.append(f"read_verilog -sv -I{ROOT}/rtl/hdc {sel}")
        elif line.startswith("synth "):
            lines.append(line + " -noabc")
        elif line.startswith("hierarchy "):
            assert "-chparam VPOS 0" in line and "-chparam DEC_LA 1" in line
            line = line.replace("-chparam VPOS 0", f"-chparam VPOS {a.vpos}")
            if a.fallback:
                line += f" -chparam DEC_LA_ISSUE_FB {a.fallback}"
            if a.bound:
                line += " -chparam DEC_LA_BOUND 1"
            if a.amq:
                line += " -chparam DEC_LA_AMQ 1"
            if a.nxreg:
                line += " -chparam DEC_LA_NXREG 1"
            if a.meif:
                line += " -chparam DEC_LA_MEIF 1"
            lines.append(line)
        else:
            lines.append(line)
    lines += ["proc", f"write_json {a.out}/original.json"]
    (a.out / "prepare.ys").write_text("\n".join(lines) + "\n")
    (a.out / "inputs.json").write_text(json.dumps(dict(
        core_sha256=hashlib.sha256(core.encode()).hexdigest(), fallback=a.fallback, bound=a.bound, amq=a.amq, nxreg=a.nxreg, meif=a.meif, vpos=a.vpos, dec_la=1,
        parameter_source="results/rtl/qwen_rom_core_takeover_20261005/retained_screen/synth.ys (P8191 plain-AR set)",
        clock_ps=833, setup_uncertainty_ps=60, hold_uncertainty_ps=25), indent=2) + "\n")


if __name__ == "__main__":
    main()
