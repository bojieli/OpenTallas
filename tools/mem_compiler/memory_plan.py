#!/usr/bin/env python3
"""Map implemented reduced memory systems onto the compiled ASAP7 macros.

For the reduced Qwen ROM and HBM vehicles this lists each implemented memory,
its macro (or register file), instance count and area. For full models it
reports weight-ROM capacity arithmetic at the compiled density. DeepSeek V41x
uses HBM KV and dedicated engines; its adopted tile memory map remains open
until those ports and staging buffers are characterized. Writes
results/memory/memory_plan.json.

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


def qwen_kv_stream_memories() -> list[dict]:
    """Finite on-die buffers for KV that lives in HBM in both Qwen designs."""
    return [
        m("KV prefetch window", 256, 256, "1R1W per bank, concurrent", "HBM KV prefetch window",
          "rtl/hdc/kv/ot_hdc_kv_stream.sv:109-114", "ot_sram_1r1w_256x256_m2_r2c2", replicas=4,
          note="G = 4 banks; full KV capacity is in HBM"),
        m("KV tail", 128, 256, "1R1W per bank, 16-bit lane mask", "open and previous K tile",
          "rtl/hdc/kv/ot_hdc_kv_stream.sv:115-121", "ot_sram_1r1w_128x256_m1_r2c2", replicas=2),
        m("flush / V write-combine FIFOs", 4, 280, "1R1W", "tail-to-HBM and V write combining",
          "rtl/hdc/kv/ot_hdc_kv_stream.sv:538-582", RF),
    ]


def plan(index: dict) -> dict:
    macros = index["macros"]
    archs = {
        "hbm_comparator": {
            "description": "Qwen matched HBM comparator: KV through ot_hdc_kv_stream and weights "
                           "through ot_hdc_wstream; weight-window banks are not macro mapped here",
            "memories": qwen_core_memories("") + qwen_kv_stream_memories() + [
                m("weight ROM", None, 1024, "1R", "weights", "HBM",
                  note="streamed from HBM by rtl/hdc/hbm/ot_hdc_wstream.sv; no on-die weight ROM. "
                       "The streamer's BF*WS weight-window SRAM banks are not macro mapped here"),
            ],
            "hard_macros": [{"name": "HBM3E PHY", "area_mm2_per_stack": asap7.tech_value("hbm.hbm3e.phy_area_mm2_per_stack"),
                             "source": "configs/hardware/technology.json hbm.hbm3e.phy_area_mm2_per_stack (assumed)",
                             "status": "external IP, not a compiler output; footprint only"}],
        },
        "qwen3_8b_rom_reticle": {
            "description": "one die, weights in mask ROM and KV in HBM through ot_hdc_kv_stream "
                           "(rtl/chip/ot_chip_hdc_tile.sv)",
            "status": "partial_adopted_tile_map_reduced_rom_capacity_proxy",
            "memories": qwen_core_memories("") + qwen_kv_stream_memories() + [
                m("weight ROM", 49152, 1024, "1R", "reduced BF16 weight-image capacity proxy",
                  "rtl/chip/ot_chip_hdc_tile.sv:183", "ot_rom_8192x266_m8", tiles_w=4, tiles_d=6,
                  ecc_data_bits=256, note="current tile has WSA=17; its production bank geometry remains open"),
            ],
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
              "unmapped_architectures": {
                  "deepseek_v41_flash": {
                      "status": "pending_adopted_tile_memory_characterization",
                      "core": "rtl/hdc/v41x/ot_hdc_core_v41x.sv",
                      "kv_storage": "HBM with row staging; no full-cache SRAM macro allocation",
                      "reason": "KV HBM prefetch, dedicated engine banks and physical port mapping are not yet closed"
                  }
              },
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
