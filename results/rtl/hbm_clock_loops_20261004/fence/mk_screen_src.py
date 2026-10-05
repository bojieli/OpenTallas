#!/usr/bin/env python3
"""Screen-only copy of a W6 fence: inline the SECDED package functions into the module body
(Yosys 0.68 rejects the in-body package import). Logic is unchanged.
Usage: mk_screen_src.py <fence.sv> <out.sv> [module_rename]"""
import re, sys
from pathlib import Path
root = Path(__file__).resolve().parents[4]
pkg = (root / 'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv').read_text()
funcs = pkg[pkg.index('function'):pkg.rindex('endpackage')]
src = Path(sys.argv[1]).read_text()
src = src.replace('  import ot_gpu_w6_secded_pkg::*;\n', funcs)
Path(sys.argv[2]).write_text(src)
