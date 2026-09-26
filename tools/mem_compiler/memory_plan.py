#!/usr/bin/env python3
"""Map every memory of the three architectures onto the compiled ASAP7 macros.

For each architecture of docs/TOKEN_PIPELINE_OPTIMIZATION_PLAN.md section 6
(HBM comparator, Qwen3-8B ROM reticle, DeepSeek-V4.1-Flash ROM array) this
lists each memory the RTL holds (sizes and port counts as the RTL and its
test benches declare them), the macro (or register file) it maps to, the
instance count and macro area -- for the reduced simulation vehicles -- and,
for the full models, the weight-ROM macro count, area and sweep bandwidth at
the compiled density.  Writes results/memory/memory_plan.json.

Every size is quoted with the file it came from; nothing here is a new
measurement of the architectures, only their memories expressed in macros.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asap7  # noqa: E402
import ecc  # noqa: E402

ROOT = asap7.ROOT
INDEX = ROOT / "physical/asap7_memory_macros/index.json"
OUT = ROOT / "results/memory/memory_plan.json"
RF = "register_file"


def m(name, words, bits, ports, holds, source, macro=None, tiles_w=1, tiles_d=1, replicas=1, note="",
      ecc_data_bits=None):
    return {"memory": name, "words": words, "bits": bits, "ports": ports, "holds": holds, "source": source,
            "macro": macro, "column_tiles": tiles_w, "depth_tiles": tiles_d, "replicas": replicas,
            "ecc_data_bits_per_tile": ecc_data_bits, "note": note}


def qwen_core_memories(kv_macro_note: str) -> list[dict]:
    return [
        m("program ROM", 4096, 1024, "1R", "program", "rtl/test/tb_hdc_core.sv:21-26", "ot_rom_4096x266_m8",
          tiles_w=4, ecc_data_bits=256),
        m("constant ROM", 4096, 64, "1R", "FP32 constant pairs", "rtl/test/tb_hdc_core.sv", "ot_rom_4096x72_m8",
          ecc_data_bits=64),
        m("vector memory", 4096, 32, "7R/6W per cycle (measured peak 7R/4W)", "activations",
          "rtl/hdc/ot_hdc_core.sv:66-89", RF,
          note="no macro organisation keeps the schedule; a banked 1R1W version with stalls exists on an "
               "unmerged branch (rtl/hdc/ot_hdc_vmem_banked.sv, 4 x 64 x 512 = ot_sram_1r1w_64x512_m1_r2c2, "
               "pin-limited at 2.5 Mb/mm2)"),
    ]


def plan(index: dict) -> dict:
    macros = index["macros"]
    archs = {
        "hbm_comparator": {
            "description": "the Qwen decode core with KV (and, when its RTL lands, weights) streamed from HBM",
            "memories": qwen_core_memories("") + [
                m("KV prefetch window", 256, 256, "1R1W per bank, concurrent", "KV prefetch window",
                  "rtl/hdc/kv/ot_hdc_kv_stream.sv:109-114", "ot_sram_1r1w_256x256_m2_r2c2", replicas=4,
                  note="G = 4 banks"),
                m("KV tail", 128, 256, "1R1W per bank, 16-bit lane mask", "open and previous K tile",
                  "rtl/hdc/kv/ot_hdc_kv_stream.sv:115-121", "ot_sram_1r1w_128x256_m1_r2c2", replicas=2),
                m("flush / V write-combine FIFOs", 4, 280, "1R1W", "tail->HBM and V write combining",
                  "rtl/hdc/kv/ot_hdc_kv_stream.sv:538-582", RF),
                m("weight ROM", None, 1024, "1R", "weights", "HBM",
                  note="streamed from HBM; no on-die weight macro. The weight streamer's prefetch buffers have "
                       "no RTL on main yet, so they are not mapped"),
            ],
            "hard_macros": [{"name": "HBM3E PHY", "area_mm2_per_stack": asap7.tech_value("hbm.hbm3e.phy_area_mm2_per_stack"),
                             "source": "configs/hardware/technology.json hbm.hbm3e.phy_area_mm2_per_stack (assumed)",
                             "status": "external IP, not a compiler output; footprint only"}],
        },
        "qwen3_8b_rom_reticle": {
            "description": "one die, weights in mask ROM, KV in on-die SRAM (reduced vehicle wrapper: "
                           "rtl/hdc/ot_hdc_memsys.sv)",
            "memories": qwen_core_memories("") + [
                m("weight ROM", 49152, 1024, "1R", "BF16 weights (45,056 words used)", "rtl/hdc/ot_hdc_memsys.sv",
                  "ot_rom_8192x266_m8", tiles_w=4, tiles_d=6, ecc_data_bits=256),
                m("KV SRAM", 1024, 512, "4R (one per lane group) + 1W (32-bit element)", "KV cache (64 positions)",
                  "rtl/test/tb_hdc_core.sv:72-78", "ot_sram_1r1w_1024x256_m2_r2c2", tiles_w=2, replicas=4,
                  note="one replica per read port; every write goes to all replicas"),
            ],
        },
        "deepseek_v41_rom_array": {
            "description": "universal die personalised per die by via mask; reduced vehicle "
                           "deepseek-v4.1-flash-reduced-v2 (rtl/test/tb_hdc_core_v41.sv)",
            "memories": [
                m("program ROM", 16384, 1536, "1R", "program (4,416 instructions)", "rtl/test/tb_hdc_core_v41.sv",
                  "ot_rom_4096x266_m8", tiles_w=6, tiles_d=4, ecc_data_bits=256),
                m("weight ROM", 169984, 1024, "2R (wrom, ewrom)", "matrix-engine weights (169,844 used)",
                  "rtl/test/tb_hdc_core_v41.sv:99-100", "ot_rom_8192x266_m8", tiles_w=4, tiles_d=21,
                  replicas=2, ecc_data_bits=256, note="two concurrent read ports -> two copies"),
                m("quantised weight ROM", 57344, 4352, "1R", "FP8/FP4 weights (54,080 used)",
                  "rtl/test/tb_hdc_core_v41.sv", "ot_rom_8192x266_m8", tiles_w=17, tiles_d=7, ecc_data_bits=256),
                m("hyper-connection ROM", 8192, 96, "1R", "FP32 HC weights", "rtl/test/tb_hdc_core_v41.sv",
                  "ot_rom_8192x104_m8", ecc_data_bits=96),
                m("Engram table ROM", 385590, 2112, "1R", "Engram rows, 264 B each", "rtl/test/tb_hdc_core_v41.sv",
                  "ot_rom_8192x274_m8", tiles_w=8, tiles_d=48, ecc_data_bits=264),
                m("constant ROM", 32768, 64, "5R", "constants, token map (28,492 used)",
                  "rtl/test/tb_hdc_core_v41.sv:106-107", "ot_rom_4096x72_m8", tiles_d=8, replicas=5, ecc_data_bits=64),
                m("KV SRAM", 32768, 512, "4R + 1W (32-bit element)", "KV (2 MiB)", "rtl/test/tb_hdc_core_v41.sv",
                  "ot_sram_1r1w_1024x256_m2_r2c2", tiles_w=2, tiles_d=32, replicas=4),
                m("vector memory", 65536, 32, "12R/10W incl. 2 x 1,024-bit reads", "activations (256 KiB)",
                  "rtl/hdc/v41/ot_hdc_core_v41.sv:55-139", RF,
                  note="register file; a banked 8-bank 1R1W organisation exists on an unmerged branch"),
            ],
            "per_die_content_signature": "each ROM instance's CRC-32 via-map signature (rom_gen.py personalise) and "
                                         "the die signature over them (rom_gen.die_signature): same LEF/Liberty "
                                         "on every die, a different via map and signature per die",
        },
    }
    for arch in archs.values():
        total_area = 0.0
        total_inst = 0
        for mem in arch["memories"]:
            name = mem["macro"]
            if name in macros:
                e = macros[name]
                inst = mem["column_tiles"] * mem["depth_tiles"] * mem["replicas"]
                mem["instances"] = inst
                mem["macro_area_um2"] = e["area_um2"]
                mem["area_um2"] = round(inst * e["area_um2"], 1)
                mem["fmax_mhz_ss"] = e["fmax_mhz"]["ss"]
                mem["fmax_mhz_tt"] = e["fmax_mhz"]["tt"]
                total_area += mem["area_um2"]
                total_inst += inst
        arch["macro_instances"] = total_inst
        arch["macro_area_mm2"] = round(total_area / 1e6, 4)
        limited = [mm for mm in arch["memories"] if "fmax_mhz_ss" in mm]
        arch["slowest_macro_fmax_mhz"] = {
            "ss": min(mm["fmax_mhz_ss"] for mm in limited), "tt": min(mm["fmax_mhz_tt"] for mm in limited)}
    return archs


def full_scale(index: dict) -> dict:
    """Full-model weight ROM in compiled macros (SECDED (266,256) tiles)."""
    out = {}
    cases = {
        "Qwen3-8B BF16 weights": (16_381_470_720, "configs/models/qwen3-8b.json checkpoint_bytes"),
        "Qwen3-8B at 4 bits per weight": (16_381_470_720 // 4, "BF16 checkpoint / 4"),
        "DeepSeek-V4.1-Flash per die (510.29 GB / 188 dies)": (
            510_286_023_000 / 188, "results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json "
                                   "ROM-N5-native-HBMKV-array-hw-hybrid-x188"),
        "DeepSeek-V4.1-Flash Engram tables (both)": (
            (384_006_168 + 384_016_682) * 264, "configs/models/candidates/deepseek-v4.1-flash.json metadata.engram"),
    }
    reticle = 815.0
    for macro in ("ot_rom_16384x266_m16", "ot_rom_8192x266_m8"):
        e = index["macros"][macro]
        data_bits = e["spec"]["words"] * 256
        rows = {}
        for label, (nbytes, src) in cases.items():
            n = math.ceil(nbytes * 8 / data_bits)
            area = n * e["area_um2"] / 1e6
            bw = n * 256 / 8 * e["fmax_mhz"]["tt"] * 1e6
            rows[label] = {"bytes": nbytes, "source": src, "instances": n, "macro_area_mm2": round(area, 1),
                           "fraction_of_815_mm2_reticle": round(area / reticle, 3),
                           "sweep_bandwidth_bytes_s_tt": bw,
                           "full_sweep_time_us_tt": round(nbytes / bw * 1e6, 3)}
        out[macro] = {"data_bits_per_instance": data_bits, "ecc": "SECDED (266,256): 3.9% check bits",
                      "cases": rows}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    index = json.loads(INDEX.read_text())
    result = {"schema": "opentallas.memory-plan.v1", "generated_by": "tools/mem_compiler/memory_plan.py",
              "macro_index_sha256": asap7.sha256_file(INDEX), "architectures": plan(index),
              "full_scale_weight_rom": full_scale(index),
              "claim_boundary": "macro counts and areas from the compiled ASAP7 abstracts; ASAP7 is predictive, "
                                "the full-model rows are capacity arithmetic at the compiled density, not a floorplan"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for k, a in result["architectures"].items():
        print(f"{k}: {a['macro_instances']} macros, {a['macro_area_mm2']} mm2, slowest SS {a['slowest_macro_fmax_mhz']['ss']:.0f} MHz")
    for mac, f in result["full_scale_weight_rom"].items():
        for label, r in f["cases"].items():
            print(f"  {mac} {label}: {r['instances']} inst, {r['macro_area_mm2']} mm2 "
                  f"({r['fraction_of_815_mm2_reticle']} reticles), sweep {r['full_sweep_time_us_tt']} us")
    return 0


if __name__ == "__main__":
    sys.exit(main())
