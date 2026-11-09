#!/usr/bin/env python3
"""DIE-KV-94 11-08: KV die PLL reservation abstract (analog hard IP), cloned from the HBM/S81 die PLL abstract: pins, PG and
obstruction only, no timing claim.  The bound module qkd_pll_analog_model (rtl/qwen_sys/split_20261014, a simulation model with
five delay-loop oscillators) becomes a black box in the physical kit, so no behavioural loop reaches synthesis (rtl_lint).
Pin names and directions are the module ports; pins sit on M4 at the west edge as in the HBM view, 8.64 um apart.
usage: kv_pll_views.py HBM_VIEW_DIR OUT_DIR   (writes qkd_pll_analog_model.lef + _{tt,ff,ss}.lib + .pins.json)"""
import json
import re
import sys
from pathlib import Path

MODULE = "qkd_pll_analog_model"
INPUTS = ["refclk", "por_n"]
OUTPUTS = ["locked", "pll_WS", "pll_WN", "pll_ES", "pll_EN", "pll_c", "pll_fwd", "pll_hbm_WS", "pll_hbm_WN", "pll_hbm_ES",
           "pll_hbm_EN", "pll_host", "pll_ingest", "pll_phy"]
Y0, STEP = 30.24, 8.64       # M4 track grid (0.048): 630 + 180*i tracks
SIZE = 172.8


def pin_rows():
    rows = []
    for i, name in enumerate(INPUTS + OUTPUTS):
        rows.append((name, "INPUT" if name in INPUTS else "OUTPUT", round(Y0 + STEP * i, 3)))
    return rows


def pin_block(name, direction, y):
    use = "CLOCK" if name == "refclk" or name.startswith("pll_") else "SIGNAL"
    return (f"  PIN {name}\n    DIRECTION {direction} ;\n    USE {use} ;\n    SHAPE ABUTMENT ;\n    PORT\n      LAYER M4 ;\n"
            f"      RECT 0.000 {y:.3f} 0.024 {y + 0.024:.3f} ;\n    END\n  END {name}\n")


def lef(hbm_text):
    """HBM abstract head, PG rails and obstruction byte for byte; only the cell name and the signal pins change."""
    head, rest = hbm_text.split("  PIN refclk\n", 1)
    i = rest.index("  PIN VDD\n")
    text = head + "".join(pin_block(*r) for r in pin_rows()) + rest[i:]
    text = text.replace("ot_hbm_pll_bb", MODULE)
    note = "# DIE-KV-94 11-08: KV die PLL reservation abstract cloned from ot_hbm_pll_bb: pins + PG + obstruction only, no timing claim.\n"
    return re.sub(r"^#.*\n", note, text, count=1)


def lib(hbm_text):
    text = hbm_text.replace("ot_hbm_pll_bb", MODULE)
    keep, tail = text.split("    pin (refclk)", 1)
    keep = re.sub(r'comment : ".*?";', 'comment : "DIE-KV-94 11-08: KV die PLL reservation (analog hard IP): pins only, no timing";',
                  keep, count=1)
    template_in = "pin (refclk)" + tail.split("\n", 1)[0]
    template_out = re.search(r"pin \(clk_stream\).*", tail).group(0)
    pins = [template_in.replace("pin (refclk)", f"pin ({n})", 1) for n in INPUTS]
    pins += [template_out.replace("pin (clk_stream)", f"pin ({n})", 1) for n in OUTPUTS]
    return keep + "".join(f"    {p}\n" for p in pins) + "  }\n}\n"


def main(argv):
    hbm, out = Path(argv[0]), Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{MODULE}.lef").write_text(lef((hbm / "ot_hbm_pll_bb.lef").read_text()))
    for c in ("tt", "ff", "ss"):
        (out / f"{MODULE}_{c}.lib").write_text(lib((hbm / f"ot_hbm_pll_bb_{c}.lib").read_text()))
    pins = [dict(name=n, layer="M4", xy=[0.012, round(y + 0.012, 3)]) for n, _d, y in pin_rows()]
    (out / f"{MODULE}.pins.json").write_text(json.dumps(pins, indent=1) + "\n")
    print("wrote", out, len(pins), "pins, outline", SIZE)


if __name__ == "__main__":
    main(sys.argv[1:])
