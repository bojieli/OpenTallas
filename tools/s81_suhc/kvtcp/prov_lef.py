#!/usr/bin/env python3
"""S81-KVTC-PINS: PROVISIONAL probe abstract of a kvtcp kit (pins from its pins_ns.tcl, PG pins as the signed kvtch
form, OBS = conservative blanket M1-M5 over the core, 0.3 um clear of the N/S pin faces).  Probe-only: the signed
view replaces it.  usage: prov_lef.py OLD_LEF IO_TCL H OUT"""
import re, sys
old, io, H, out = sys.argv[1], sys.argv[2], round(float(sys.argv[3]), 3), sys.argv[4]
t = open(old).read(); W = float(re.search(r'SIZE ([\d.]+) BY', t).group(1))
dirs = dict(re.findall(r'PIN (\S+)\n\s+DIRECTION (\w+)', t))
pins = []
for ln in open(io):
    m = re.match(r'place_pin -pin_name \{(\S+)\} -layer (\w+) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}', ln)
    if m:
        n, l, x, y, w, h = m.groups(); x, y, w, h = map(float, (x, y, w, h))
        pins.append((n, l, x - w / 2, y - h / 2, x + w / 2, y + h / 2))
assert len(pins) == 6867 and all(p[0] in dirs for p in pins)
o = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', "UNITS", "    DATABASE MICRONS 1000 ;", "END UNITS", "",
     "MACRO dsfd_su_t_kvtc", "  FOREIGN dsfd_su_t_kvtc 0 0 ;", "  CLASS BLOCK ;", f"  SIZE {W} BY {H} ;"]
for n, l, a, b, c, d in sorted(pins):
    o += [f"  PIN {n}", f"    DIRECTION {dirs[n]} ;", "    USE SIGNAL ;", "    PORT", f"      LAYER {l} ;",
          f"        RECT  {a:.3f} {b:.3f} {c:.3f} {d:.3f} ;", "    END", f"  END {n}"]
# PG: M5 stripes as the kit pdn.tcl (width 0.12, pitch 5.4, offset 0.3 from core 2.16; VDD/VSS alternate by 0.192)
for net, off in (("VDD", 0.0), ("VSS", 0.192)):
    o += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {'POWER' if net == 'VDD' else 'GROUND'} ;", "    PORT", "      LAYER M5 ;"]
    x = 2.16 + 0.3 + off
    while x + 0.12 < W - 2.16:
        o.append(f"        RECT  {x:.3f} 2.160 {x + 0.12:.3f} {H - 2.16:.3f} ;"); x += 5.4
    o += ["    END", f"  END {net}"]
o += ["  OBS"]
for l in ("M1", "M2", "M3", "M4", "M5"):
    o += [f"    LAYER {l} ;", f"      RECT  0.000 0.300 {W:.3f} {H - 0.3:.3f} ;"]
o += ["  END", "END dsfd_su_t_kvtc", "", "END LIBRARY", ""]
open(out, "w").write("\n".join(o))
print("provisional", out, W, H, len(pins))
