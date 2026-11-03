#!/usr/bin/env python3
"""DIE-HBM-61/MEM (11-03, OWNER TWO-STRIKES RE-FORM class 4 "macro channels"): right-width, no-repair, single-mask
SRAM masters for the HBM RE-FORM cores whose r2c2 SRAMs carry 410-793 M4 pins per W/E face.

Measured on the d44o kit netlists (yosys mem.json, wd_in / w_mask_in drivers per instance):
  * every HBM instance ties rr_en/rr_addr/cr_en/cr_sel to 0 (no repair used)  -> r0c0 (COORD 10-25 no-repair ruling);
  * every instance except sfustore ties w_mask_in to a constant (1 on the used bits, 0 above) -> one mask pin
    (mask_gran = bits), driven 1;
  * most 64x512 instances use only W of the 512 data bits (hfd_ep 306, q3_edge/cp_rxs llr 141/138, cp_rxs 30/16)
    -> a W-bit master; sfustore uses the 128x256 as a 512x32 store (32-bit lane mask, read mux after the macro)
    -> a 512x32 master.
Read/write cycle contract is unchanged (1r1w, one-cycle registered read, same read-before-write); no access cycle
is added.  pin_faces "rw": clock + read port on the W face, write port on the E face (one port per face).
Same generator, calibration and v2 track alignment as build_s81_vp_norepair_1025.py.  Originals are immutable;
names are new (_r0c0_g<mask_gran>), so every consuming kit binds a fresh master.

    python3 tools/mem_compiler/build_hbm_rightwidth_1103.py [--dry]   (--dry: print sizes, write nothing)
"""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sram_gen, build_aligned_v2 as aligned

# name, words, bits, mux, mask_gran, consumers (core: instances)
SPECS = [
    ("ot_sram_1r1w_64x306_m1_r0c0_g306", 64, 306, 1, 306, {"hfd_ep_static": 4}),
    ("ot_sram_1r1w_64x141_m1_r0c0_g141", 64, 141, 1, 141, {"ot_hfd_coll_q3_edge_core": 12, "ot_hbm_host_cp_rxs": 1}),
    ("ot_sram_1r1w_64x32_m1_r0c0_g32", 64, 32, 1, 32, {"ot_hbm_host_cp_rxs": 2}),
    ("ot_sram_1r1w_128x256_m1_r0c0_g256", 128, 256, 1, 256, {"ot_hbm_su_programme_pslice_c5": 100,
                                                            "ot_hbm_sm_vm_wr_q_t_lanes4": 1}),
    ("ot_sram_1r1w_256x256_m2_r0c0_g256", 256, 256, 2, 256, {"ot_hnx_idxn_keybuf_slice": 4, "ot_hbm_host_cp_rxs": 2,
                                                            "ot_hbm_idx_rootctl_static_am": 1}),
    ("ot_sram_1r1w_256x64_m2_r0c0_g64", 256, 64, 2, 64, {"ot_hnx_idxn_keybuf_slice": 1}),
    ("ot_sram_1r1w_512x32_m4_r0c0_g32", 512, 32, 4, 32, {"ot_hbm_su_static_sfustore_hw": 16}),
]


def build(root, dry=False):
    root = Path(root)
    out = Path(tempfile.mkdtemp(prefix="hbm_rw_")) if dry else root / "physical/asap7_memory_macros_v2"
    rows = []
    for name, w, b, m, g, use in SPECS:
        spec = sram_gen.SramSpec(name, w, b, m, 1, "1r1w", 0, 0, g, "rw")
        with aligned.patched(sram_gen, GENERATOR_VERSION=sram_gen.GENERATOR_VERSION + "+aligned-v2"), \
                aligned.patched(sram_gen, macro_outline=_aligned_outline_faces, write_lef=_aligned_write_lef_faces,
                                behavioural=_behavioural_scalar_mask):
            sheet = sram_gen.compile_macro(spec, out)
        a = sheet["area"]
        aligned.finish(out, name, None, (a["macro_width_um"], a["macro_height_um"]),
                       {"kind": "sram", "spec": sheet["spec"], "builder": "tools/mem_compiler/build_hbm_rightwidth_1103.py",
                        "consumers": use})
        sz = aligned.verify_lef((out / name / f"{name}.lef").read_text())[name]["size_um"]
        t = sheet.get("timing", {}).get("tt", {})
        rows.append(dict(name=name, size_um=sz, signal_pins=a["outline"]["signal_pins"],
                         pins_per_edge=a["outline"]["pins_per_edge"], clk_to_q_ps=t.get("clk_to_q_ps"),
                         setup_ps=t.get("setup_ps"), min_period_ps=t.get("min_period_ps"), consumers=use))
    return out, rows


def _aligned_outline_faces(core_w, core_h, pins, faces=None):
    """aligned_outline for the explicit "rw" face plan: per-edge pin count from the faces, then the v2 0.024 mod 0.048
    width/height rule (build_aligned_v2.aligned_outline semantics)."""
    import views
    w, h, info = views.macro_outline(core_w, core_h, pins, faces=faces)
    w2, h2 = aligned.align_up_um(w), aligned.align_up_um(h)
    info = dict(info); info["aligned_v2"] = {"v1_width_um": w, "v1_height_um": h, "width_um": w2, "height_um": h2}
    return w2, h2, info


_BEHAV = sram_gen.behavioural


def _behavioural_scalar_mask(spec, pins, header):
    """sram_gen.behavioural; a single mask bit (mask_gran == bits) is a scalar port, so index it without a select
    (iverilog/yosys reject a bit-select of a scalar)."""
    text = _BEHAV(spec, pins, header)
    if spec.mask_bits == 1:
        text = text.replace(f"w_mask_in[mg / {spec.mask_gran}]", "w_mask_in")
    return text


def _aligned_write_lef_faces(name, w, h, pins, props, faces=None):
    """build_aligned_v2.aligned_write_lef with the explicit face plan (SYMMETRY X Y: no R90)."""
    import views
    text = views.write_lef(name, w, h, pins, props, faces=faces)
    text = text.replace("# OpenTallas memory compiler (tools/mem_compiler), ASAP7 abstract view",
                        "# OpenTallas memory compiler (tools/mem_compiler), ASAP7 abstract view, track-aligned v2 "
                        "(build_hbm_rightwidth_1103.py)", 1)
    return aligned.drop_r90(text)


if __name__ == "__main__":
    out, rows = build(Path(__file__).resolve().parents[2], dry="--dry" in sys.argv)
    print(json.dumps(dict(out=str(out), macros=rows), indent=1))
