#!/usr/bin/env python3
"""Generate a private same-W-face CFGROM compiler abstract; no catalog mutation.

TT is a conservative latest-data envelope including the relocation RC.
FF preserves the old earliest-data envelope, so unmoved pins gain no hold credit.
These are analytical compiler bounds, not a routed macro or silicon characterization.
"""
from __future__ import annotations
import argparse
import dataclasses
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asap7
import build_aligned_v2 as aligned
import rom_gen
import views

SOURCE_NAME = "ot_rom_4096x72_m8"
NAME = SOURCE_NAME + "_wface_1113"
EXTRA_LENGTH_UM = 38.040 + 4.128
MOVED_BITS = 43

def build(out: Path) -> dict:
    if (out/NAME).exists():
        raise ValueError("private output master already exists; use a fresh output directory")
    spec = rom_gen.RomSpec(name=NAME, words=4096, bits=72, mux=8)
    pins = rom_gen.pins_for(spec)
    faces = ([(p,b) for p in pins for b in p.bits()], [])
    old_timing = rom_gen.timing_model
    prices = {}

    def outline(core_w, core_h, pp):
        w,h,info = views.macro_outline(core_w, core_h, pp, faces=faces)
        return aligned.align_up_um(w), aligned.align_up_um(h), dict(info, private_wface=True)

    def lef(name,w,h,pp,props):
        text = views.write_lef(name,w,h,pp,props,faces=faces)
        return aligned.drop_r90(text.replace(
            "# OpenTallas memory compiler (tools/mem_compiler), ASAP7 abstract view",
            "# PRIVATE same-W-face compiler ABSTRACT; analytical TT/FF envelopes, not routed",
            1))

    def timing(ss,area,cal,corner):
        t = old_timing(ss,area,cal,corner)
        assert corner in ("tt","ff")
        resistance,cap_per_um = asap7.SETRC["M4"]
        wire_r = resistance * EXTRA_LENGTH_UM
        wire_c = cap_per_um * EXTRA_LENGTH_UM
        intrinsic = t.out_r_kohm * wire_c + .38 * wire_r * wire_c
        prices[corner] = {"extra_return_length_um":EXTRA_LENGTH_UM,
            "extra_wire_r_kohm":wire_r,"extra_wire_c_ff":wire_c,
            "moved_bit_extra_intrinsic_ps":intrinsic,
            "moved_bit_extra_load_slope_ps_per_ff":wire_r,
            "library_envelope":"latest all-output bound" if corner=="tt"
                else "original earliest bound; no relocation hold credit"}
        extra_energy = MOVED_BITS * wire_c * t.voltage**2
        br = dict(t.breakdown, private_return_intrinsic_ps=intrinsic,
            private_return_wire_r_kohm=wire_r, private_return_wire_c_ff=wire_c)
        # TT slowest envelope can conservatively apply the worst moved-bit RC to all bits.
        # FF retains old timing/slew because 29 outputs and all inputs physically stay put.
        if corner == "tt":
            return dataclasses.replace(t, clk_to_q_ps=t.clk_to_q_ps+intrinsic,
                out_r_kohm=t.out_r_kohm+wire_r,
                out_slew_intrinsic_ps=math.hypot(t.out_slew_intrinsic_ps,2.2*intrinsic),
                read_energy_fj=t.read_energy_fj+extra_energy,breakdown=br)
        return dataclasses.replace(t,read_energy_fj=t.read_energy_fj+extra_energy,breakdown=br)

    with aligned.patched(asap7,CORNERS=("tt","ff")), aligned.patched(
            rom_gen,macro_outline=outline,write_lef=lef,timing_model=timing):
        sheet = rom_gen.compile_macro(spec,out)
    d=out/NAME
    base=asap7.ROOT/"physical/asap7_memory_macros_v2"/SOURCE_NAME
    original=json.loads((base/f"{SOURCE_NAME}.json").read_text())
    assert (sheet["area"]["macro_width_um"],sheet["area"]["macro_height_um"])==(38.04,62.952)
    ver=aligned.verify_lef((d/f"{NAME}.lef").read_text(),str(d/f"{NAME}.lef"))[NAME]
    assert ver["pass"]
    def body(p):
        return "\n".join(x for x in p.read_text().splitlines() if not x.strip().startswith("//"))
    for suffix in (".v","_bb.v"):
        assert body(d/f"{NAME}{suffix}").replace(NAME,SOURCE_NAME)==body(base/f"{SOURCE_NAME}{suffix}"),suffix
    rec={"status":"PRIVATE_COMPILER_ABSTRACT_NOT_SIGNED","master":NAME,"source_master":SOURCE_NAME,
        "outline_um":[38.04,62.952],"faces":{"W":"clk,ce_in,addr_in[11:0],rd_out[71:0]","E":[]},
        "moved_outputs":list(range(29,72)),"unmoved_outputs":list(range(29)),
        "physical_source":"real views.write_lef explicit face plan; unchanged array/periphery model",
        "internal_route_assumption":"42.168um Manhattan additional output return; no routed macro metal evidence",
        "RTL_body_identical_after_module_rename":True,"module_alias_required":True,"latency_edges":1,"timing_prices":prices,
        "SS_used":False,"track_verification":ver,
        "old_timing_tt":original["timing"]["tt"]["clk_to_q_ps"],
        "claim_boundary":sheet["claim_boundary"]}
    sheet["same_face_private"]=rec
    sheet["views"]={p.name:asap7.sha256_file(p) for p in d.iterdir() if p.suffix!=".json"}
    (d/f"{NAME}.json").write_text(json.dumps(sheet,indent=2,sort_keys=True)+"\n")
    (out/"CANDIDATE_NOT_ADOPTED.json").write_text(json.dumps(rec,indent=2)+"\n")
    return rec

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    rec=build(args.out)
    print(json.dumps({k:rec[k] for k in ("status","outline_um","RTL_body_identical_after_module_rename","timing_prices","SS_used")},indent=2))
