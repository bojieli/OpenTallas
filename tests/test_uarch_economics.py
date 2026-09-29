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
    assert abs(e["v41_rom"]["ar"]["tokens_s_b1"] - 4166.8) < 1.0
    assert abs(e["v41_rom"]["mtp_m1"]["tokens_s_b1"] - 6063.0) < 1.0
    assert abs(e["qwen_rom"]["ar"]["tokens_s_b1"] - 9967.8) < 1.0
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
    assert abs(q["ar"]["saturated_tokens_s"] - 11920.9) < 1.0          # arch_budget_qwen3 batch_model agrees


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
    assert c["Qwen ROM (AR, G = 6,144)"]["rom_mask_sets"] == 2
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
