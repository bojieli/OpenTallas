#!/usr/bin/env python3
"""Refresh an isolated generated SYS_C kit after its two frontend failures.

The input kit must be a copy, never a running/shared kit. Source topology and
pipeline stages stay unchanged. This refresh does not authorize placement/route:
actual b19 R8 landing banks still need physical allocation and geometry review.
"""
from pathlib import Path
import argparse
import shutil

ROOT = Path(__file__).resolve().parents[2]

def refresh(kit):
    kit = Path(kit).resolve()
    required = [kit / "rtl/kv3_sys_c_part.sv", kit / "rtl/ot_rom_64x32_m2_bb.v"]
    if not all(p.is_file() for p in required):
        raise ValueError("expected isolated native SYS_C source kit")
    shutil.copyfile(ROOT / "rtl/lib/ot_rst_pipe.sv", kit / "rtl/ot_rst_pipe.sv")
    for name in ("rtl_lint.py", "native_bb.py"):
        shutil.copyfile(ROOT / "tools/die_plan" / name, kit / name)
    # The hard macro layout/timing is content-independent. Preserve the exact
    # content identity before removing string-only simulation metadata from the
    # physical cell: OpenSTA's mapped-Verilog parser rejects string parameters.
    (kit / "native_rom_metadata.tcl").write_text(
        "select -assert-count 1 t:ot_rom_64x32_m2\n"
        "tee -o $::env(RESULTS_DIR)/native_rom_metadata.rtlil dump t:ot_rom_64x32_m2\n"
        "setparam -unset INSTANCE -unset VIAMAP t:ot_rom_64x32_m2\n")
    config = kit / "config.mk"
    text = config.read_text()
    setting = "export SYNTH_CANONICALIZE_TCL = /work/native_rom_metadata.tcl\n"
    if setting not in text:
        if "SYNTH_CANONICALIZE_TCL" in text:
            raise ValueError("kit already owns a canonicalization hook")
        config.write_text(text + "\n" + setting)
    runner = kit / "run_kit.sh"
    text = runner.read_text()
    command = "  python3 -I /work/native_bb.py /OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl || exit 8; " + chr(92) + "\n"
    if command not in text:
        if text.count("  M=") != 1:
            raise ValueError("unrecognized generated runner; refusing refresh")
        text = text.replace("  M=", command + "  M=", 1)
    # Correct the extra escaped newline from the old generated preflight line.
    text = text.replace(chr(92) * 3 + "\n", chr(92) + "\n")
    runner.write_text(text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kit", type=Path)
    refresh(parser.parse_args().kit)
