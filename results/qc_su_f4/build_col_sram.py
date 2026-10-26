#!/usr/bin/env python3
"""QC-SU-F4 (COORD 13:25 ruling 3): NATIVE column-shaped SRAM view for the QC SU vmr / rp1 cores (no rotation).

The F3 re-floorplan needs each 1024 x 256 1R1W SRAM as a column with its pin ends north / south.  Rotating the existing
ot_sram_1r1w_1024x256_m2_r2c2 (R90/R270) is illegal (LEF SYMMETRY X Y; FinFET macros never rotate).  This builds the
same memory (1024 words x 256 bits, 1R1W, 2 spare rows + 2 spare IO columns) with the column organisation done in the
generator: column mux 1 (one word per physical row) and 2 stacked banks (bitlines stay 512 cells), pins = the same
"split" halves as the m2 macro but on the TOP (first half: clk, r_ce, r_addr, rd_out, w_ce, w_addr, wd[0..]) and BOTTOM
(rest) edges as M5 pins (sram_gen --pin-faces ns), through the SAME aligned-v2 rules (H, W = 0.024 mod 0.048, SYMMETRY
X Y, checker-verified in R0/MX/MY/R180).  Writes physical/asap7_memory_macros_v2_col/<name>/ (+ index.json) and checks
that the existing v2 m2 macro is reproduced byte-identically by the patched generator (no change to any pinned view).
    python3 results/qc_su_f4/build_col_sram.py [OUTDIR]
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))
import asap7  # noqa: E402
import build_aligned_v2 as B  # noqa: E402
import sram_gen as S  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "physical/asap7_memory_macros_v2_col"
REF = "ot_sram_1r1w_1024x256_m2_r2c2"
NEW = S.SramSpec("ot_sram_1r1w_1024x256_m1b2_r2c2_ns", 1024, 256, mux=1, banks=2, ports="1r1w", spare_rows=2,
                 spare_cols=2, pin_faces="ns")


def build(spec, out):
    with B.patched(S, macro_outline=B.aligned_outline, write_lef=B.aligned_write_lef,
                   GENERATOR_VERSION=f"{S.GENERATOR_VERSION}+{B.ALIGN_VERSION}"):
        return S.compile_macro(spec, out)


# 1. no regression: the reference macro from the patched generator == the committed v2 view (every file but the sheet)
ref_dir = ROOT / "physical/asap7_memory_macros_v2" / REF
ref_spec = json.loads((ref_dir / f"{REF}.json").read_text())["spec"]
with tempfile.TemporaryDirectory() as t:
    build(S.SramSpec(**ref_spec), Path(t))
    same = {f.name: (Path(t) / REF / f.name).read_bytes() == f.read_bytes()
            for f in sorted(ref_dir.iterdir()) if f.suffix in (".lef", ".lib", ".v")}
print("reference", REF, "byte-identical:", same)
if not all(same.values()):
    raise SystemExit("patched generator changed the reference view")

# 2. the column view
OUT.mkdir(parents=True, exist_ok=True)
sheet = build(NEW, OUT)
lef = (OUT / NEW.name / f"{NEW.name}.lef").read_text()
ver = B.verify_lef(lef, str(OUT / NEW.name))[NEW.name]
if not ver["pass"]:
    raise SystemExit(f"column view not on track in every orientation: {json.dumps(ver)[:800]}")
ref_sheet = json.loads((ref_dir / f"{REF}.json").read_text())
a, ra = sheet["area"], ref_sheet["area"]
rep = {"schema": "opentallas.qc-su-f4.column-sram.v1", "builder": "results/qc_su_f4/build_col_sram.py",
       "generator": sheet["generator"], "spec": sheet["spec"], "replaces_in_floorplan": REF,
       "size_um": [a["macro_width_um"], a["macro_height_um"]], "ref_size_um": [ra["macro_width_um"], ra["macro_height_um"]],
       "area_um2": round(a["macro_area_um2"], 1), "ref_area_um2": round(ra["macro_area_um2"], 1),
       "symmetry": ver["symmetry"], "allowed_orientations": ver["allowed_orientations"], "pin_layers": list(ver["layers"]),
       "track_check": ver["layers"], "outline": a["outline"],
       "timing_ps": {c: {k: round(sheet["timing"][c][k], 1) for k in ("clk_to_q_ps", "setup_ps", "hold_ps", "min_period_ps")}
                     for c in sheet["timing"]},
       "ref_timing_ps": {c: {k: round(ref_sheet["timing"][c][k], 1) for k in ("clk_to_q_ps", "setup_ps", "hold_ps", "min_period_ps")}
                         for c in ref_sheet["timing"]},
       "port_delta": "identical ports except rr_addr: 2 x clog2(rows) = 2 x 10 = 20 bits (m2: 2 x 9 = 18); "
                     "the cores tie the repair pins to 0 (rr_addr(18'd0) -> 20'd0)",
       "views": sheet["views"]}
(OUT / "index.json").write_text(json.dumps({NEW.name: rep}, indent=1, sort_keys=True) + "\n")
print(json.dumps({k: rep[k] for k in ("size_um", "ref_size_um", "area_um2", "ref_area_um2", "symmetry",
                                        "allowed_orientations", "pin_layers", "timing_ps", "ref_timing_ps")}, indent=0))
