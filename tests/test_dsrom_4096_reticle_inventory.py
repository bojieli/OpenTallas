"""Static source contract checks; no RTL build or capacity/depth sweep."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("inventory", ROOT / "tools/dsrom_4096_reticle_inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


@pytest.fixture(scope="module")
def model():
    return inventory.build()


def test_generated_record_reproduces_all_fields(model):
    record = ROOT / "results/uarch/dsrom_4096_reticle_inventory_20261002/inventory.json"
    assert json.loads(record.read_text()) == model


def test_leaf_clock_pg_obs_and_fixed_capacity(model):
    leaf = model["macro_catalog"]["ot_rom_4096x274_m8"]
    assert leaf["outline_um"] == [125.28, 62.91]
    assert leaf["pin_uses"] == {"CLOCK": 1, "SIGNAL": 287, "POWER": 1, "GROUND": 1}
    assert {p["name"] for p in leaf["clock_and_PG_pins"]} == {"clk", "VDD", "VSS"}
    assert {o["layer"] for o in leaf["OBS"]} == {"M1", "M2", "M3", "M4"}
    assert leaf["capacity_bits"] == 4096 * 274
    assert model["busiest_die"]["total_macros"] == 19092
    assert model["element_envelope"]["reference_total_physical_ROMs_layer_dies"] == 3127360


def test_complete_element_area_and_ports_no_doublecount(model):
    e = model["element_envelope"]
    for name, frame in [("q_pair", 64825.596), ("BF16_column_pair", 142971.9984)]:
        c = e["classes"][name]
        assert c["frame_area_um2"] == pytest.approx(frame)
        assert c["logical_slots"] * c["ROMs_per_logical_slot"] == c["physical_ROMs"] == 4
        assert c["gross_storage_bits"] == 4489216
        assert c["ROM_macro_area_um2"] == pytest.approx(31525.4592)
        assert c["ROM_data_bitcell_area_um2"] + c["ROM_peripheral_taps_control_outline_area_um2"] == pytest.approx(c["ROM_macro_area_um2"])
        assert c["ROM_macro_area_um2"] + c["adjacent_compute_control_wires_margin_reservation_um2"] == pytest.approx(frame)
        assert c["pure_compute_measured_area_um2"] is None
        p = c["source_port_contract"]
        assert p["q_stream_total_bits"] == p["q_activation_codes_bits"] + p["q_activation_exponents_bits"] + p["q_stream_valid_pair_block_slotvalid_position_bits"]
        assert c["boundary_bits_per_cycle"] == p["q_stream_total_bits"] + p["BF16_stream_data_bits"] + p["BF16_stream_metadata_bits"]
        assert p["return_partial_NB2_bits"] == 2 * p["return_partial_per_NB_bits"]


@pytest.mark.parametrize("mutation", ["old_depth", "drop_bf", "drop_macro", "drop_layer", "duplicate_expert", "admission"])
def test_mutated_inventory_fails(model, mutation):
    x = copy.deepcopy(model)
    if mutation == "old_depth":
        x["product"]["rows"] = 8192
    elif mutation == "drop_bf":
        x["per_stage_per_rank"][0]["BF16_column_pairs"] = 0
    elif mutation == "drop_macro":
        x["per_stage_per_rank"][0]["total_ROM4096_instances"] -= 1
    elif mutation == "drop_layer":
        x["nonexpert_and_BF16_ownership"]["layer_candidate_obligations"].pop()
    elif mutation == "duplicate_expert":
        x["nonexpert_and_BF16_ownership"]["layer_candidate_obligations"][0]["routed_expert_candidate_owners"][0]["expert_ids"][1] += 1
    else:
        x["physical_admission"] = True
    with pytest.raises(AssertionError):
        inventory.validate_inventory(x)


def test_single_shared_candidate_and_unchanged_intensity(model):
    lever = model["selected_primary_lever"]
    assert lever["fixed_depth"] == 4096 and lever["no_depth_sweep"]
    assert lever["candidate_partition_count"] is None
    assert lever["minimum_partition_count"] is None
    assert lever["per_element_arithmetic_intensity_unchanged"]
    classes = model["element_envelope"]["classes"]
    assert classes["q_pair"]["arithmetic"]["fp4_macs_per_cycle"] == 128
    assert classes["q_pair"]["arithmetic"]["fp4_weight_macs_per_byte"] == pytest.approx(128 / 68.5)
    assert classes["BF16_column_pair"]["arithmetic"]["macs"] == 32
    assert classes["BF16_column_pair"]["arithmetic"]["activation_macs_per_byte"] == 0.5
    assert not model["physical_admission"]
