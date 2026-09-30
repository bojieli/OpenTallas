"""Economics section of the microarchitecture model (tools/uarch_model.py --economics): batch, energy, cost."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/uarch/economics.json"
sys.path.insert(0, str(ROOT / "tools"))


def _rec():
    return json.loads(REC.read_text())


def _all_curves(e):
    return {"qwen_rom.ar": e["qwen_rom"]["ar"]["rows"], "qwen_hbm.ar": e["qwen_hbm"]["ar"]["rows"],
            "qwen_hbm.dflash": e["qwen_hbm"]["dflash"]["rows"], "v41_rom.ar": e["v41_rom"]["ar"]["rows"],
            "v41_rom.mtp": e["v41_rom"]["mtp_m1"]["rows"], "v41_hbm.ar": e["v41_hbm"]["ar"]["rows"],
            "v41_hbm.mtp": e["v41_hbm"]["mtp"]["rows"], "gpu.qwen": e["gpu"]["qwen"]["rows"],
            "gpu.v41": e["gpu"]["v41"]["rows"]}


def test_record_is_source_pinned():
    e = _rec()
    assert e["schema"] == "opentallas.uarch.economics.v1"
    for q in ("tools/uarch_model.py", "configs/hardware/technology.json", "results/arch/v41_rack.json"):
        assert len(e["source_sha256"][q]) == 64


def test_batch_curves_are_physical():
    for name, rows in _all_curves(_rec()).items():
        b1 = rows[0]["per_user_tokens_s"]
        agg = [r["aggregate_tokens_s"] for r in rows]
        assert rows[0]["batch"] == 1, name
        # no user is faster than a lone user, and adding users never loses more than rounding of aggregate
        assert all(r["per_user_tokens_s"] <= b1 + 0.1 for r in rows), name
        assert all(b >= a * 0.98 for a, b in zip(agg, agg[1:])), name
        for r in rows:
            assert abs(r["per_user_ms_per_token"] - 1e3 / r["per_user_tokens_s"]) < 1e-2 * r["per_user_ms_per_token"]


def test_batch_one_matches_the_single_user_sections():
    e = _rec()
    # W15 (2026-09-29): V4.1 collectives and the Qwen TP-2 exchanges priced from the RTL measurement
    assert abs(e["v41_rom"]["ar"]["tokens_s_b1"] - 3808.8) < 1.0
    assert abs(e["v41_rom"]["mtp_m1"]["tokens_s_b1"] - 5856.5) < 1.0
    # W16 / root 2026-09-30: the Qwen ROM product is option C (4 dies, TP-4, G 6,144, W12 wires)
    assert abs(e["qwen_rom"]["ar"]["tokens_s_b1"] - 9367.6) < 1.0
    assert abs(e["qwen_hbm"]["ar"]["tokens_s_b1"] - 880.6) < 1.0
    assert abs(e["qwen_hbm"]["dflash"]["tokens_s_b1"] - 2671.0) < 1.0
    assert abs(e["v41_hbm"]["ar"]["tokens_s_b1"] - 2919.8) < 1.0
    assert abs(e["v41_hbm"]["mtp"]["tokens_s_b1"] - 5673.0) < 1.0
    assert abs(e["gpu"]["qwen"]["tokens_s_b1"] - 331.0) < 1.0
    assert abs(e["gpu"]["v41"]["tokens_s_b1"] - 277.7) < 1.0


def test_qwen_rom_batching_binds_on_the_kv_stream_not_the_lanes():
    q = _rec()["qwen_rom"]
    assert q["binding"] == "kv_stream"
    assert q["bounds_tokens_s"]["kv_stream"] < q["bounds_tokens_s"]["lanes"]
    # option C: each die streams its 2 of 8 KV heads from its own 4 stacks (16 stacks), twice the 2-die 11,920.9
    assert abs(q["ar"]["saturated_tokens_s"] - 2 * 11920.9) < 1.0


def test_v41_rom_saturation_is_the_stage_occupancy_bound():
    v = _rec()["v41_rom"]
    occ = max(v["stage_occupancy_us"].values())
    assert abs(v["ar"]["saturated_tokens_s"] - 1e6 / occ) < 0.01 * v["ar"]["saturated_tokens_s"]
    # time-multiplexed MTP (m = 1) re-issues every position: it helps the lone user and costs aggregate
    assert v["mtp_m1"]["tokens_s_b1"] > v["ar"]["tokens_s_b1"]
    assert v["mtp_m1"]["saturated_tokens_s"] < v["ar"]["saturated_tokens_s"]


def test_gpu_batch_calibration_reproduces_the_paper():
    c = _rec()["gpu"]["qwen"]["calibration"]
    for b, x in c["measured_tokens_s"].items():
        assert abs(c["fitted_tokens_s"][b] - x) / x < 0.05


def test_capacity_bounds_every_sweep():
    e = _rec()
    for name, rows in _all_curves(e).items():
        key = name.split(".")[0]
        cap = e["gpu"][name.split(".")[1]]["capacity_users"] if key == "gpu" else e[key]["capacity_users"]
        assert rows[-1]["batch"] == cap, name


def test_cost_rows():
    e = _rec()
    c = {r["design"]: r for r in e["cost"]}
    assert c["V4.1 ROM array (AR / MTP m = 1)"]["rom_mask_sets"] == 188
    assert c["Qwen ROM (AR, G = 6,144)"]["rom_mask_sets"] == 4          # option C: 4 ROM dies
    for r in e["cost"]:
        assert r["capex_per_system_usd"]["low"] <= r["capex_per_system_usd"]["high"]
        assert r["usd_per_tokens_s_saturated"]["low"] <= r["usd_per_tokens_s_b1"]["low"]


def test_v41_ledger_matches_power_ledger_on_the_busiest_stage():
    import uarch_model as U
    d = copy.deepcopy(U.PRESETS["proposal"])
    r, g = U._v41_graph(d, 1)
    pw = U.power_ledger(d, g, r["clock_hz"], r["tokens_s"], U.area_ledger(d))
    led = U.v41_rom_ledger(g, mac_ops=1)
    assert abs(led["stage_die_energy_J"][pw["busiest_stage"]] * 1e6 - pw["energy_per_token_uJ"]) < 0.02
    assert abs(1.0 / max(led["stage_occupancy_s"].values()) - pw["saturated_tokens_s_per_stage"]) < 0.2


LEV = ROOT / "results/uarch/economics_levers.json"


def _lev():
    return json.loads(LEV.read_text())


def test_levers_record_is_source_pinned():
    lv = _lev()
    assert lv["schema"] == "opentallas.uarch.economics_levers.v1"
    assert len(lv["source_sha256"]["tools/uarch_model.py"]) == 64


def test_static_power_policies_only_ever_save_and_never_touch_the_token_path():
    e, sp = _rec(), _lev()["static_power"]
    summ = {r["design"]: r for r in e["summary"]}
    for mode, name in (("ar", "V4.1 ROM AR"), ("mtp_m1", "V4.1 ROM MTP m = 1")):
        for wk in ("wake_1us", "wake_c6_133us"):
            blk = sp[mode][wk]
            assert blk["wake_on_token_path_us"] == 0.0
            assert blk["serdes_prewake_fits"]
            for pt in ("batch1", "saturated"):
                tot = [r["energy_mJ_per_token"] for r in blk[pt]]
                assert all(b <= a + 1e-6 for a, b in zip(tot, tot[1:])), (mode, wk, pt)
            # the ungated policy reproduces the economics section
            assert abs(blk["batch1"][0]["energy_mJ_per_token"] - summ[name]["energy_mJ_b1"]) < 2.0
            assert abs(blk["saturated"][0]["energy_mJ_per_token"] - summ[name]["energy_mJ_sat"]) < 2.0
        # with a 1 us wake every non-busiest stage power-gates at saturation, and all 29 at batch 1
        assert sp[mode]["wake_1us"]["batch1"][3]["stages_power_gated"] == 29
        assert sp[mode]["wake_1us"]["saturated"][3]["stages_power_gated"] >= 27


def test_adaptive_mtp_takes_the_better_mode_and_switches_near_thirteen_users():
    ad = _lev()["adaptive_mtp"]
    for k, v in ad.items():
        for r in v["rows"]:
            assert r["aggregate_tokens_s"] == max(r["ar_aggregate_tokens_s"], r["mtp_aggregate_tokens_s"])
        assert v["rows"][0]["mode"] == "MTP" and v["rows"][-1]["mode"] == "AR"
    rom = ad["v41_rom"]
    assert abs(rom["switch_users"] - rom["mtp_saturated"] / rom["ar_b1"]) < 0.01
    assert 12 < rom["switch_users"] < 14      # 13.3 with the W15-measured collectives (12.0 before)


def test_via_programmable_masks_bound_the_rom_nre():
    rows = [r for r in _lev()["rom_masks"]["rows"] if r["design"].startswith("V4.1")]
    full = next(r for r in rows if r["case"].startswith("full"))
    via = [r for r in rows if r["case"].startswith("via")]
    assert len(via) == 4
    assert all(r["nre_usd"] < full["nre_usd"] / 5 for r in via)
    assert all(r["usd_per_tokens_s_saturated_base_excluded"] <= r["usd_per_tokens_s_saturated"] for r in via)


def test_every_design_is_gated_alike():
    ga = _lev()["gated_alike"]
    designs = {r["design"] for r in ga["rows"]}
    for d in ("Qwen ROM AR (G = 6,144)", "Qwen HBM tier 3 AR", "Qwen HBM tier 3 DFlash", "V4.1 HBM tier 3 AR",
              "V4.1 HBM tier 3 MTP", "V4.1 ROM AR", "V4.1 ROM MTP m = 1"):
        assert d in designs
    summ = {r["design"]: r for r in _rec()["summary"]}
    for r in ga["rows"]:
        # gating only ever saves; the ungated column is the economics section's figure
        assert r["clock_and_power_gated_mJ_per_token"] <= r["clock_gated_mJ_per_token"] + 1e-6 <= r["ungated_mJ_per_token"] + 2e-6
        s = summ.get(r["design"])
        if s:
            ref = s["energy_mJ_b1"] if r["point"] == "batch1" else s["energy_mJ_sat"]
            assert abs(r["ungated_mJ_per_token"] - ref) < 2.0, r["design"]


def test_v41_hbm_timeline_reproduces_the_chain():
    import uarch_model as U
    for P, T_us in ((1, 342.5), (U.V41_POSITIONS, 617.5)):
        segs, _, _ = U.v41_hbm_timeline(P)
        assert abs(sum(d for d, _ in segs) * 1e6 - T_us) < 0.5


def test_gating_never_places_a_wake_in_a_short_gap():
    import uarch_model as U
    dm = U._domain(logic=10.0, clock=1e9, **U.CORE_WAKE)
    short = U.CORE_WAKE["wake"] + U.CORE_WAKE["bet"] - 1e-9
    # a gap shorter than wake + BET is only clock gated: power gating changes nothing there
    assert U._domain_energy(dm, 1e-5, 0.0, [short], 2) == U._domain_energy(dm, 1e-5, 0.0, [short], 1)
