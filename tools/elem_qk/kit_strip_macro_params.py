#!/usr/bin/env python3
"""ELEM-QK 10-24: drop parameter overrides on HARD-MACRO instantiations in a G3 kit's rtl/ copy.

The as-built RTL instantiates ROM macros with content selectors (#(.VIAMAP(..), .INSTANCE(..)): which image the
behavioural model loads).  The kit reads the macro black box (_bb.v, no parameters) + its LEF/liberty: Yosys stops on
"does not have a parameter named 'INSTANCE'", and OpenSTA cannot read a netlist cell with #(...) (STA-0171).  The
timing/physical view of a ROM does not depend on its content (the image is the via programming), so the kit copy
instantiates the macro without the override.  Only modules listed in the kit's config.mk ADDITIONAL_LEFS are touched;
every change is listed in KIT/macro_params_stripped.json.

    kit_strip_macro_params.py KITDIR
"""
import json
import re
import sys
from pathlib import Path


def strip_params(text, macros):
    out, log, i = [], [], 0
    rx = re.compile(r"\b(" + "|".join(map(re.escape, sorted(macros))) + r")(\s*)#\s*\(")
    while True:
        m = rx.search(text, i)
        if not m:
            out.append(text[i:])
            break
        j, depth = m.end(), 1
        while depth and j < len(text):
            depth += {"(": 1, ")": -1}.get(text[j], 0)
            j += 1
        out.append(text[i:m.start()] + m.group(1) + " ")
        log.append(dict(module=m.group(1), params=" ".join(text[m.end():j - 1].split())))
        i = j
    return "".join(out), log


def main(kd):
    kd = Path(kd)
    cfg = (kd / "config.mk").read_text()
    lefs = re.search(r"ADDITIONAL_LEFS\s*=\s*(.*)", cfg)
    macros = {Path(x).stem for x in lefs.group(1).split()} if lefs else set()
    rec = []
    if macros:
        for f in sorted((kd / "rtl").iterdir()):
            if f.suffix not in (".v", ".sv") or f.name.endswith("_bb.v"):
                continue
            t = f.read_text(errors="replace")
            n, log = strip_params(t, macros)
            if log:
                f.write_text(n)
                rec += [dict(file=f.name, **x) for x in log]
    (kd / "macro_params_stripped.json").write_text(json.dumps(dict(macros=sorted(macros), stripped=rec), indent=1) + "\n")
    print(f"{kd.name}: {len(rec)} macro instantiation(s) without parameter overrides")


if __name__ == "__main__":
    for k in sys.argv[1:]:
        main(k)
