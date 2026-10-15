#!/usr/bin/env python3
"""Track-aligned (v2 rules) SRAM macros of the S81 gather root leaf (s81-gather 2026-10-13).

    python3 tools/s81_ph/gather_macros.py [--out physical/s81_ph_views/macros]

The catalog (physical/asap7_memory_macros_v2) has no 128-word 66-bit or 256 / 512-word 34-bit 1R1W macro.  These are the
SAME generator (tools/mem_compiler/sram_gen.py) under the SAME successor rules build_aligned_v2 injects for the
catalog (H and W = 0.024 mod 0.048 um, SYMMETRY X Y), verified with its verify_lef; a failure aborts.
  ot_sram_1r1w_128x66_m1_r2c2   input queue payload {spare, e, d32, t32} of one root (QD = 128)
  ot_sram_1r1w_256x34_m2_r2c2   pairing store {side, e, d32} of one root, address {open-row slot 3, parent node 5} (S = 8)
  ot_sram_1r1w_512x34_m4_r2c2   the same store for S = 16 (not used by the S = 8 leaf; kept so the parameter is buildable)
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "mem_compiler"))
sys.path.insert(0, str(ROOT / "tools"))
import build_aligned_v2 as B      # noqa: E402
import sram_gen                   # noqa: E402

SPECS = [dict(name="ot_sram_1r1w_128x66_m1_r2c2", words=128, bits=66, mux=1, ports="1r1w", spare_rows=2, spare_cols=2),
         dict(name="ot_sram_1r1w_256x34_m2_r2c2", words=256, bits=34, mux=2, ports="1r1w", spare_rows=2, spare_cols=2),
         dict(name="ot_sram_1r1w_512x34_m4_r2c2", words=512, bits=34, mux=4, ports="1r1w", spare_rows=2, spare_cols=2)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "physical/s81_ph_views/macros")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    index = {}
    with B.patched(sram_gen, macro_outline=B.aligned_outline, write_lef=B.aligned_write_lef,
                   GENERATOR_VERSION=f"{sram_gen.GENERATOR_VERSION}+{B.ALIGN_VERSION}"):
        for s in SPECS:
            sheet = sram_gen.compile_macro(sram_gen.SramSpec(**s), a.out)
            lef = a.out / s["name"] / f"{s['name']}.lef"
            v = B.verify_lef(lef.read_text(), str(lef))[s["name"]]
            if not v["pass"]:
                raise SystemExit(f"{s['name']}: track alignment FAILED {json.dumps(v)[:400]}")
            ar, t = sheet["area"], sheet["timing"]
            index[s["name"]] = dict(spec=s, width_um=ar["macro_width_um"], height_um=ar["macro_height_um"],
                                    area_um2=round(ar["macro_width_um"] * ar["macro_height_um"], 1),
                                    track_alignment=v, timing={c: {k: t[c][k] for k in t[c] if "ps" in k}
                                                               for c in t if isinstance(t[c], dict)})
            print(s["name"], ar["macro_width_um"], "x", ar["macro_height_um"], "pass", v["pass"])
    (a.out / "index.json").write_text(json.dumps(dict(schema="opentallas.s81ph.gather_macros.v1",
        generator="tools/s81_ph/gather_macros.py (sram_gen + build_aligned_v2 rules)", macros=index), indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
