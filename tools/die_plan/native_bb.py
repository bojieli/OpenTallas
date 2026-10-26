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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preamble", type=Path)
    patch(parser.parse_args().preamble)
