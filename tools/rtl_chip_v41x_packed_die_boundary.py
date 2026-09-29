"""Fast source-pinned interface lint for the V4.1 packed-window die boundary.

The adopted full core and behavioral HBM make an unrestricted die lint very
large.  This gate keeps their *exact port headers* while blackboxing their
internals.  It checks both reduced and full die wiring; it is not a token,
memory, synthesis, or timing verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from tools import rtl_chip_v41x_die_smoke as die


ROOT = Path(__file__).resolve().parents[1]
CHIP = ROOT / "rtl/chip"
ROM = ROOT / "rtl/rom"
SOURCES = [
    CHIP / f"{n}.sv" for n in (
        "ot_chip_v41x_die", "ot_chip_v41x_tile", "ot_chip_v41x_hbm3e_phy",
        "ot_chip_v41x_window_row_codec", "ot_chip_v41x_window_kv_prefetch",
        "ot_chip_v41x_window_stage4", "ot_chip_v41x_window_refill_schedule",
        "ot_chip_v41x_window_attn_source", "ot_chip_v41x_attn_row_merge",
        "ot_chip_v41x_attn_desc_lifecycle", "ot_chip_v41x_rope_region_guard",
        "ot_chip_v41x_rope_hbm_cache", "ot_chip_v41x_kv_rope_reqmux",
        "ot_chip_v41x_window_block_guard",
        "ot_chip_v41x_kv_reqmux", "ot_chip_v41x_kv_prefetch",
        "ot_chip_v41x_hbm_karb", "ot_chip_v41x_coll_dma",
        "ot_chip_v41x_coll_transpose",
    )
] + [ROM / f"{n}.sv" for n in (
    "ot_rom_pkg_ctrl_x", "ot_rom_fabric_router", "ot_rom_oneshot_px",
)] + [ROOT / "rtl/hdc/ot_hdc_fastfp.sv"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tag_width_check(source: str, scratch: Path) -> dict:
    """Elaborate exact die declarations: each of four stacks owns 16 tag bits.

    Keep this independent of inherited lint flags, which suppress WIDTH.
    The real net declarations are extracted, so a narrow connection cannot
    pass merely because the standalone client and mux tests use wider nets.
    """
    names = ("w_tag", "w_s_tag", "p_tag", "p_stag")
    declarations = re.findall(r"\bwire\s*\[[^;]+;", source)
    selected = []
    for name in names:
        matches = [d for d in declarations if re.search(r"\b" + name + r"\b", d)]
        if len(matches) != 1:
            return {"returncode": 1, "diagnostics": [f"Cannot identify unique declaration: {name}"]}
        if matches[0] not in selected:
            selected.append(matches[0])
    checks = [f'if ($bits({name}) != 64) $fatal(1, "{name}: expected 4 x 16 tag bits, got %0d", $bits({name}));'
              for name in names]
    tb = scratch / "tag_widths.sv"
    binary = scratch / "tag_widths.vvp"
    tb.write_text("module tag_widths;\n" + "\n".join(selected) +
                  "\ninitial begin\n" + "\n".join(checks) +
                  '\n$display("DIE_TAG_WIDTHS_PASS stacks=4 tag_bits=16 buses=4"); $finish; end\nendmodule\n')
    build = subprocess.run(["iverilog", "-g2012", "-s", "tag_widths", "-o", str(binary), str(tb)],
                           capture_output=True, text=True, check=False)
    if build.returncode:
        return {"returncode": build.returncode, "diagnostics": [build.stderr]}
    sim = subprocess.run(["vvp", str(binary)], capture_output=True, text=True, check=False)
    return {"returncode": sim.returncode, "diagnostics": sim.stdout.splitlines() + sim.stderr.splitlines()}


def run() -> dict:
    results = {}
    with tempfile.TemporaryDirectory(prefix="v41_packed_die_boundary_") as name:
        scratch = Path(name)
        results["tag_bus_widths"] = tag_width_check((CHIP / "ot_chip_v41x_die.sv").read_text(), scratch)
        for stem in ("ot_chip_v41x_tile", "ot_chip_v41x_hbm3e_phy"):
            die.blackbox_stub(CHIP / f"{stem}.sv", scratch / f"{stem}.sv")
        rtl = [scratch / "ot_chip_v41x_tile.sv", scratch / "ot_chip_v41x_hbm3e_phy.sv"]
        rtl += [p for p in SOURCES if p.name not in {
            "ot_chip_v41x_tile.sv", "ot_chip_v41x_hbm3e_phy.sv"}]
        for full, window in ((0, 0), (1, 0), (1, 1)):
            cmd = [
                die.VERILATOR, "--lint-only", *die.LINT_FLAGS,
                "-Wno-PINMISSING", "-Wno-UNDRIVEN",
                "--top-module", "ot_chip_v41x_die", f"-GFULL_SHAPE={full}",
                f"-GWINDOW_HBM_ATTENTION={window}",
                "-GK_MEM=524288", *map(str, rtl),
            ]
            result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                                    timeout=90, check=False)
            mode = "reduced" if not full else ("full_window_hbm" if window else "full")
            results[mode] = {
                "returncode": result.returncode,
                "diagnostics": [line.replace(str(ROOT) + "/", "")
                                for line in result.stderr.splitlines() if line.startswith("%")],
            }
    return {
        "claim": "die port/header elaboration with exact tile and HBM PHY headers, including opt-in WINDOW HBM source; no token or P&R claim",
        "verilator": die.tool_version(die.VERILATOR),
        "sources_sha256": {str(p.relative_to(ROOT)): sha(p) for p in SOURCES + [Path(__file__)]},
        "modes": results,
        "pass": all(item["returncode"] == 0 for item in results.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/rtl/chip_v41x_packed_die_boundary.json")
    args = parser.parse_args()
    record = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"packed die boundary: {'PASS' if record['pass'] else 'FAIL'}; {args.output}")
    if not record["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
