#!/usr/bin/env python3
"""Keep native macro metadata parameters through ORFS classic canonicalization.

Liberty blackboxes do not describe content-only VIAMAP/INSTANCE parameters.
Eager native headers replace their port models; deferred logic still specializes
only at actual instance parameters. This does not change hard macro timing.
"""
from pathlib import Path
import argparse

OLD = "      read_verilog -defer -sv {*}$vIdirsArgs $file"
NEW = """      # OT_NATIVE_BB_METADATA: Liberty omits content-only macro parameters.
      if {[regexp {_bb[.](v|sv)$} $file]} {
        read_verilog -lib -overwrite -sv {*}$vIdirsArgs $file
      } else {
        read_verilog -defer -sv {*}$vIdirsArgs $file
      }"""

def patch(path):
    path = Path(path)
    text = path.read_text()
    if NEW in text:
        return
    if text.count(OLD) != 1:
        raise ValueError("unrecognized synth_preamble.tcl; refusing macro frontend patch")
    path.write_text(text.replace(OLD, NEW))

PHYS_OLD = "write_verilog -nohex -nodec $::env(RESULTS_DIR)/1_2_yosys.v"
PHYS_NEW = """# OT_NATIVE_ROM_PHYSICAL_METADATA: retain all content metadata before serialization.
write_json $::env(RESULTS_DIR)/1_2_yosys_native_metadata.json
# OpenSTA's physical Verilog reader cannot parse string parameter overrides.
# Only ROM content labels are removed; all geometry/numeric parameters remain.
setparam -unset VIAMAP -unset INSTANCE t:ot_rom_*
""" + PHYS_OLD


def patch_physical(path):
    path = Path(path)
    text = path.read_text()
    if PHYS_NEW in text:
        return
    if text.count(PHYS_OLD) != 1:
        raise ValueError("unrecognized synth.tcl; refusing physical metadata patch")
    path.write_text(text.replace(PHYS_OLD, PHYS_NEW))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preamble", type=Path)
    parser.add_argument("--physical-synth", type=Path)
    args = parser.parse_args()
    patch(args.preamble)
    if args.physical_synth:
        patch_physical(args.physical_synth)
