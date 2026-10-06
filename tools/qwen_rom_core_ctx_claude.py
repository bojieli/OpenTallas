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


def module_closure(top_text: str, already: set) -> list:
    """repo RTL files defining every module instantiated (transitively) by top_text, minus `already` (paths)"""
    import re
    defs = {}
    for d in ("rtl/hdc", "rtl/common", "rtl/proto", "rtl/lib", "rtl/hdc/v41x"):
        for f in sorted((ROOT / d).glob("*.sv")) + sorted((ROOT / d).glob("*.v")):
            for m in re.findall(r"^\s*module\s+(\w+)", f.read_text(errors="ignore"), re.M):
                defs.setdefault(m, f)
    inst = lambda t: set(re.findall(r"^\s*(ot_\w+)\s*(?:#\s*\(|\w+\s*\()", t, re.M))   # noqa: E731
    todo, seen, files = list(inst(top_text)), set(), []
    while todo:
        m = todo.pop()
        if m in seen or m not in defs:
            continue
        seen.add(m)
        f = defs[m]
        if f not in files and str(f) not in already:
            files.append(f)
        todo += list(inst(f.read_text(errors="ignore")))
    return files


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fallback", type=int, default=0, help="0 none, 1 issue copies, 2 = 1 + one-hot chase select")
    ap.add_argument("--vpos", type=int, default=0)
    ap.add_argument("--bound", action="store_true", help="also DEC_LA_BOUND (narrow la_lo remainder table)")
    ap.add_argument("--amq", action="store_true", help="also DEC_LA_AMQ (argmax boundary register, +1 cycle per END)")
    ap.add_argument("--nxreg", action="store_true", help="also DEC_LA_NXREG (NEXT fields registered at the boundary)")
    ap.add_argument("--meif", action="store_true", help="also DEC_LA_MEIF (registered ME-spine handshake)")
    ap.add_argument("--su-in", action="store_true", help="re-cut (coordinator 2026-10-06): the vector stream unit "
                    "(ot_hdc_vstream_rt) is routed INSIDE the core block (not black-boxed), so the issue loop and the "
                    "SU ready / progress handshakes are block-internal")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / "gen").mkdir()
    core = core_text(a.fallback, a.vpos, a.bound, a.amq, a.nxreg, a.meif)
    (a.out / "core.sv").write_text(core)
    (a.out / "gen/ot_hdc_vstream_rt.sv").write_text(E.E.emit_vstream(E.E.VSTREAM.read_text()))
    lines = []
    for line in RETAINED.read_text().splitlines():
        if a.su_in and line.strip() == "blackbox ot_hdc_vstream_rt":
            continue
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
    if a.su_in:
        vs = (a.out / "gen/ot_hdc_vstream_rt.sv").read_text()
        have = {l.split()[-1] for l in lines if l.startswith("read_verilog ")}
        extra = module_closure(vs, have)
        k = max(i for i, l in enumerate(lines) if l.startswith("read_verilog "))
        lines[k + 1:k + 1] = [f"read_verilog -sv -I{ROOT}/rtl/hdc {f}" for f in extra]
    lines += ["proc", f"write_json {a.out}/original.json"]
    (a.out / "prepare.ys").write_text("\n".join(lines) + "\n")
    (a.out / "inputs.json").write_text(json.dumps(dict(
        core_sha256=hashlib.sha256(core.encode()).hexdigest(), fallback=a.fallback, bound=a.bound, amq=a.amq, nxreg=a.nxreg, meif=a.meif, su_in=a.su_in, vpos=a.vpos, dec_la=1,
        parameter_source="results/rtl/qwen_rom_core_takeover_20261005/retained_screen/synth.ys (P8191 plain-AR set)",
        clock_ps=833, setup_uncertainty_ps=60, hold_uncertainty_ps=25), indent=2) + "\n")


if __name__ == "__main__":
    main()
