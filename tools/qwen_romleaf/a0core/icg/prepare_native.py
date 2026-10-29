#!/usr/bin/env python3
"""Build the selected A0 source with actual mapped rawleaf and functional ROMs.

Read-only kit inputs; all replacements are written into a new proof directory.
The rawleaf mapped netlist and patched cell models are explicit inputs, because
empty hardened-macro declarations cannot establish clock-gating equivalence.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kit", type=Path, required=True)
    ap.add_argument("--rawleaf", type=Path, required=True)
    ap.add_argument("--cell-model", type=Path, required=True)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit("fresh proof output required")
    rtl = a.out / "rtl"
    shutil.copytree(a.kit / "rtl", rtl)
    for p in rtl.glob("*_bb.v"):
        p.unlink()  # Only copied empty macro declarations; real bodies follow.
    rawcut = rtl / "ot_qwen_tile_lsl_rawcut.v"
    s, n = re.subn(r"\(\* blackbox \*\)\s*module ot_qwen_tile_lsl_rawfault_m3\b.*?endmodule", "",
                  rawcut.read_text(), count=1, flags=re.S)
    if n != 1:
        raise SystemExit("expected one selected rawfault blackbox in copied kit")
    rawcut.write_text(s)
    shutil.copy2(a.rawleaf, rtl / "rawleaf_keep.v")
    shutil.copy2(a.cell_model, rtl / "asap7_functional.v")
    src = a.repo / "rtl"
    for name in ("ot_qwen_tile_romleaf.sv", "ot_qwen_tile_node.sv"):
        shutil.copy2(src / "physical" / name, rtl / name)
    shutil.copy2(src / "lib/ot_rst_relay.sv", rtl / "ot_rst_relay.sv")
    for name in ("ot_rom_4096x266_m8", "ot_rom_2048x266_m8", "ot_sram_1r1w_128x256_m1_r2c2"):
        shutil.copy2(a.repo / "physical/asap7_memory_macros" / name / f"{name}.v", rtl / f"{name}.v")
    files = sorted(p.resolve() for p in rtl.iterdir() if p.suffix in (".sv", ".v"))
    (a.out / "files.txt").write_text("\n".join(str(p) for p in files) + "\n")
    manifest = {str(p.relative_to(a.out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (a.out / "manifest.json").write_text(json.dumps(dict(kit=str(a.kit), rawleaf=str(a.rawleaf),
        cell_model=str(a.cell_model), grade="operational-source-miter", defines=["OT_ROM_CONST0_KV"],
        REGROOT_MODE=3, ICG=2, files=manifest), indent=2) + "\n")
    print(f"NATIVE_SOURCE_READY {len(files)} files; no FP1 substitute")


if __name__ == "__main__":
    main()
