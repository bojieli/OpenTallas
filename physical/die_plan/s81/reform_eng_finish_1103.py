#!/usr/bin/env python3
"""RF-B 11-03 (S81-RF1 RE-FORM, S81-046): re-size the ot_s81dv_eng_finish hard child of ot_s81dv_xfin to the RE-FORM fill
band (std 13730 um2 / 181.44 x 190.08 = 0.398 of the outline) and re-spread its 614 N-face M5 pins (>= 0.192 um pitch).
Writes the child LEF + spec note (recipe row ot_s81dv_eng_finish, child_of ot_s81dv_xfin, is in recipes.json).  The parent outline is a PLAN delta."""
import argparse, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
p = argparse.ArgumentParser(); p.add_argument("--width", type=float, default=181.44); p.add_argument("--height", type=float, default=190.08)
p.add_argument("--std", type=float, default=13730.0); a = p.parse_args()
W, H = a.width, a.height
vd = "physical/ref_tile/s81dv_eng_finish/views/ot_s81dv_eng_finish"; lf = ROOT / vd / "ot_s81dv_eng_finish.lef"
pins = re.findall(r"  PIN (.*?)\n    DIRECTION (INPUT|OUTPUT)", lf.read_text())
assert len(pins) == 614, len(pins)
L = ["VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", "UNITS", "    DATABASE MICRONS 1000 ;", "END UNITS", "",
     "MACRO ot_s81dv_eng_finish", "  FOREIGN ot_s81dv_eng_finish 0 0 ;", "  CLASS BLOCK ;", f"  SIZE {W} BY {H} ;"]
k0 = 90; k1 = int((W - 4.32 - .012) / .048); prev = None
for i, (n, d) in enumerate(pins):
    c = round(.012 + (k0 + round(i * (k1 - k0) / 613)) * .048, 4)
    if prev is not None: assert c - prev >= .192 - 1e-6
    prev = c
    L += [f"  PIN {n}", f"    DIRECTION {d} ;", "    USE SIGNAL ;", "    PORT", "      LAYER M5 ;",
          (f"        RECT {c-.024:.4f} {H-.48:.4f} {c+.024:.4f} {H:.4f} ;" if n == "clk" else   # GEOM-21 clock pin 0.048x0.48
           f"        RECT {c-.012:.4f} {H-.084:.4f} {c+.012:.4f} {H:.4f} ;"), "    END", f"  END {n}"]
L += ["END ot_s81dv_eng_finish", "END LIBRARY", ""]; lf.write_text("\n".join(L))
sp = ROOT / "physical/ref_tile/s81dv_eng_finish/spec.json"; s = json.loads(sp.read_text())
s["util"] = 0.40
s["structural_change"] = (f"RF-B 11-03 S81-RF1 RE-FORM (two strikes): child {W}x{H} (outline fill {a.std/(W*H):.3f}, band 0.35-0.45; was "
    "155.52x164.16 fill 0.60 with GRT overflow on M5); write enables pre-decoded one stage early (cycle-exact); every output = face "
    "flop -> negative-level lockup latch -> port; 614 N-face M5 pins re-spread >= 0.192 um. No added cycles, no port change.")
sp.write_text(json.dumps(s, indent=1) + "\n")
print(json.dumps(dict(child=[W, H], outline_fill=round(a.std / (W * H), 4), core_fill=round(a.std / ((W - 8.64) * (H - 8.64)), 4), aspect=round(H / W, 3))))
