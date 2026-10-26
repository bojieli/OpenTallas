#!/usr/bin/env python3
"""S81/RTLSPLIT: the four split cores' RTL ports (name, width, direction) against the plan pin tables
(physical/die_plan/s81/inputs/core_pins/<mod>.json, + _xm views) and the stub LEF directions (cores/leaf/lef/<mod>.lef).
    python3 tools/s81_slice/split_port_check.py      (cwd = repo root)   exit 1 = mismatch"""
import json, re, sys
sys.path.insert(0, "tools/s81_dv/kits_rtla")
from miter_gen import ports
SRC = {"ot_s81sl_ve_m": "rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv", "ot_s81sl_ve_s": "rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv",
       "ot_s81sl_vn_a": "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv", "ot_s81sl_vn_b": "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv"}
bad = 0
for mod, f in SRC.items():
    text = open(f).read()
    rtl = {}
    for d, hi, lo, n in ports(text, mod):
        w = hi - lo + 1
        for b in range(lo, hi + 1):
            rtl[n if w == 1 and hi == 0 else "%s[%d]" % (n, b)] = "INPUT" if d == "input" else "OUTPUT"
    for view in (mod, mod + "_xm"):
        tab = {p["name"] for p in json.load(open("physical/die_plan/s81/inputs/core_pins/%s.json" % view))["pins"]}
        lef = open("physical/die_plan/s81/cores/leaf/lef/%s.lef" % view).read()
        ldir = dict(re.findall(r"PIN (\S+)\s+DIRECTION (\w+)", lef))
        miss, extra = sorted(tab - set(rtl)), sorted(set(rtl) - tab)
        dmis = sorted(n for n in rtl if n in ldir and ldir[n] != rtl[n])
        nolef = sorted(set(rtl) - set(ldir))
        ok = not (miss or extra or dmis or nolef)
        bad += not ok
        print("%-16s rtl %4d table %4d lef %4d  missing %d extra %d dir_mismatch %d not_in_lef %d  %s" % (
            view, len(rtl), len(tab), len(ldir), len(miss), len(extra), len(dmis), len(nolef), "PASS" if ok else "FAIL"))
        for lst, nm in ((miss, "missing"), (extra, "extra"), (dmis, "dir"), (nolef, "nolef")):
            if lst:
                print("   ", nm, lst[:12])
print("SPLIT_PORTS", "PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
