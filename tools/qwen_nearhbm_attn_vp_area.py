#!/usr/bin/env python3
"""Area and strip power density of the verify-block lane sets (rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_vp.sv, VP > 1).

A lane set is one copy of the near-HBM attention datapath for one verify position: per stack R row engines
(512 lanes each: 4 q heads x 128 d), their exp pipes, Z tree, P.V tree, score and e memories, q registers, and one hub.
Copies share the HBM K/V stream: the request generator and the row FIFO are needed once (in the bench each copy still
has its own, kept in lockstep and checked; the shared version is the area basis "shared_stream").

Bases (all read from committed records, pinned by sha256 in the output):
  * frame: the floorplan r1 row-engine frame (claude/qwen-rom-floorplan-nearhbm-20261003 @ ced04cd96, model-r1.json
    row_engine.frame_area_um2, 6 per stack) -- the placed element the floorplan reserves;
  * units: synthesised SS screens (results/uarch/qwen_nearhbm_attn_rtl_20261003/ss_screens.json) composed lane by lane,
    the hub's synthesised area (pnr/hub_r3.host_synth_stat.txt), the repo SRAM macro and register bit.
Power: the r2 hot-spot model (model-r2.json hotspot / region_power, IEEE EPS HIR Thermal v0.9 limit 2.0 W/mm2 nominal).
Each lane set is its own frames at the same lane density, so the in-phase peak density is unchanged; the time-averaged
density falls by the ratio AR-token-time / verify-step-time per K/V phase (each lane set runs once per step).

    python3 tools/qwen_nearhbm_attn_vp_area.py --vp 2 --out results/rtl/qwen_rom_dspark_20261003/attn/area_power.json
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FP_COMMIT = "ced04cd96"
FP_DIR = "results/uarch/qwen_rom_floorplan_nearhbm_20261003"
NHB = ROOT / "results/uarch/qwen_nearhbm_attn_rtl_20261003"


def git_json(path):
    txt = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{FP_COMMIT}:{path}"])
    return json.loads(txt), hashlib.sha256(txt).hexdigest()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vp", type=int, default=2)
    ap.add_argument("--r", type=int, default=6, help="row engines per stack (6: the floorplan instance)")
    ap.add_argument("--ar-token-cycles", type=int, default=202590, help="AR token at 8K (pricing basis)")
    ap.add_argument("--verify-step-cycles", type=int, default=None,
                    help="verify step cycles for the duty ratio (default: AR token, i.e. the bound)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    r1, r1_sha = git_json(f"{FP_DIR}/model-r1.json")
    r2, r2_sha = git_json(f"{FP_DIR}/model-r2.json")
    ss = json.loads((NHB / "ss_screens.json").read_text())["units"]
    hub_txt = (NHB / "pnr/hub_r3.host_synth_stat.txt").read_text()
    hub_um2 = float(re.findall(r"Chip area for module '\\?ot_qwen_nearhbm_attn_hub': ([0-9.]+)", hub_txt)[-1])
    macros = json.loads((ROOT / "physical/asap7_memory_macros/index.json").read_text())["macros"]
    sram = macros["ot_sram_1r1w_1024x256_m2_r2c2"]["area_um2"]
    cells = json.loads((ROOT / "results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json").read_text())["cells"]
    ff = cells["ASR_area_um2"] + cells["INV_area_um2"]
    re_el = r1["row_engine"]
    R, HD, LN = a.r, 128, 512
    frame = re_el["frame_area_um2"]
    # unit composition of one row engine (lanes + scale + pads), per-stack blocks, one hub
    u = {k: ss[k]["synth_area_um2"] for k in ("prod", "add7", "mul6")}
    exp_p7 = json.loads((NHB / "ss_screens.json").read_text())["pipelined_sfu"]["screens"]["exp_p7"]["synth_area_um2"]
    row_fifo = 32 * HD * 8 * ff                                    # DQ = 32 rows of 1,024 b
    engine_wo_fifo = LN * (u["prod"] + u["add7"] + 32 * (8 - 7) * ff) + 4 * u["mul6"] + 64 * 32 * ff
    exp_quad = 4 * (2 * u["add7"] + exp_p7)
    pv_tree = LN * u["add7"] + 8 * LN * 32 * ff
    z_tree = 16 * u["add7"] + (2048 + 1024) * 32 * ff
    mems = 6 * sram
    q_regs = 8 * HD * 16 * ff
    per_stack_copy = R * (engine_wo_fifo + exp_quad) + pv_tree + z_tree + mems + q_regs
    units_copy = 4 * per_stack_copy + hub_um2                      # one more lane set, row FIFO shared
    units_first = units_copy + 4 * R * row_fifo
    frame_set = 4 * R * frame                                      # placed frames of one lane set (incl. its FIFO)
    frame_extra_shared = frame_set - 4 * R * row_fifo + hub_um2
    extra = a.vp - 1
    # power: r2 hot-spot model
    hs = r2["hotspot"]
    lim = hs["limit_w_per_mm2"]["nominal"]
    stA = r2["region_power"]["scenarios"]["A"]["strip"]
    static = r2["region_power"]["static_w_per_mm2"]
    duty_cap = hs["mitigation_if_sustained"]["duty_governor_max"]
    dyn_d = (lim - static) / duty_cap
    active_ar = (stA["avg"] - static) / dyn_d
    step = a.verify_step_cycles or a.ar_token_cycles
    active_vp = active_ar * a.ar_token_cycles / step
    rec = dict(
        schema="qwen-nearhbm-attn-vp-area-power.v1", vp=a.vp, row_engines_per_stack=R,
        area_mm2=dict(
            frame_basis=dict(per_lane_set=round(frame_set / 1e6, 2),
                             added_for_vp=round(extra * frame_extra_shared / 1e6, 2),
                             basis=f"{4 * R} floorplan r1 row-engine frames x {frame} um2 per lane set (incl. exp, Z, P.V, "
                                   "score SRAM, q), minus the shared row FIFO, plus one synthesised hub"),
            unit_basis=dict(per_lane_set_first=round(units_first / 1e6, 2), added_for_vp=round(extra * units_copy / 1e6, 2),
                            components_um2_per_stack=dict(row_engines_wo_fifo=round(R * engine_wo_fifo),
                                                         exp_quads=round(R * exp_quad), pv_tree=round(pv_tree),
                                                         z_tree=round(z_tree), score_e_sram=round(mems), q=round(q_regs)),
                            hub_um2=hub_um2,
                            basis="pre-layout synthesised SS units (prod, add7, mul6, exp_p LA7/LM7), register bit "
                                  f"{ff} um2, SRAM {sram} um2; no utilisation/CTS/PDN"),
            model_priced_per_extra_lane_set=14.7),
        power=dict(
            limit_w_per_mm2=hs["limit_w_per_mm2"], limit_source=hs["sources"][0]["ref"],
            limit_source_sha256=hs["sources"][0]["sha256_fetched_2026_10_03"],
            scenario="A (measured TT MAC 3.974 pJ)",
            in_phase_peak_w_per_mm2=stA["peak"],
            peak_note="each lane set occupies its own frames at the parent lane density: the in-phase peak (a PDN/IR load, "
                      "tau 1.22 ms >> phase) is unchanged by VP",
            ar_time_averaged_w_per_mm2=stA["avg"],
            vp_time_averaged_w_per_mm2=round(static + dyn_d * active_vp, 3),
            active_fraction=dict(ar=round(active_ar, 4), vp=round(active_vp, 4),
                                 basis=f"each lane set runs its K/V phases once per verify step of {step} cycles vs once "
                                       f"per AR token of {a.ar_token_cycles}"),
            duty_cap_sustained=duty_cap,
            verdict=("PASS single-user time-averaged vs 2.0 nominal and 1.0 conservative" if static + dyn_d * active_vp <= 1.0
                     else "CHECK"),
            sustained_note="a 100%-duty strip (aggregate saturation) still needs the r2 duty governor <= 0.483 or a "
                           "measured MAC <= 1.92 pJ; VP does not change that bound (intensive)"),
        sources_sha256={f"{FP_COMMIT}:{FP_DIR}/model-r1.json": r1_sha, f"{FP_COMMIT}:{FP_DIR}/model-r2.json": r2_sha,
                        "results/uarch/qwen_nearhbm_attn_rtl_20261003/ss_screens.json": sha(NHB / "ss_screens.json"),
                        "results/uarch/qwen_nearhbm_attn_rtl_20261003/pnr/hub_r3.host_synth_stat.txt":
                            sha(NHB / "pnr/hub_r3.host_synth_stat.txt"),
                        "tools/qwen_nearhbm_attn_vp_area.py": sha(__file__)})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(area=rec["area_mm2"]["frame_basis"], units=rec["area_mm2"]["unit_basis"]["added_for_vp"],
                          power={k: rec["power"][k] for k in ("in_phase_peak_w_per_mm2", "vp_time_averaged_w_per_mm2",
                                                              "verdict")}), indent=1))


if __name__ == "__main__":
    main()
