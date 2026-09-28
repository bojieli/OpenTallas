"""Evidence and refusal gates for the bounded V4.1 L0 implementation proposal."""

import copy
import json

import pytest

from tools import v41_l0_implementation_contract as C


def test_contract_is_current_and_blocked():
    saved = json.loads(C.OUT.read_text())
    assert C.derive() == saved
    C.validate(saved)
    assert saved["total_latency_cycles"] is None
    assert saved["critical_path_budget"]["selected_topology_budget_cycles"] is None
    assert saved["critical_path_budget"]["component_inputs"][0]["known_local_floor_cycles"] == 5120
    assert all(x["allocated_cycles"] is None for x in saved["critical_path_budget"]["component_inputs"])
    assert saved["clock"]["achieved_hz"] is None
    assert saved["contexts"][0]["binding_status"] == "exact_instruction_and_selected_image"
    assert saved["contexts"][1]["binding_status"] == "missing_position_and_selected_ID_binding"


def test_all_real_descriptors_and_dependencies_are_present():
    c = C.derive()
    ops = c["operations"]
    assert [o["pc"] for o in ops] == list(range(111))
    collectives = [o for o in ops if o["unit"] == "COLL"]
    assert len(collectives) == 12
    assert [o["collective_descriptor"]["input_64B_words"] for o in collectives] == [
        20, 8, 320, 36, 6, 36, 36, 36, 36, 36, 36, 80]
    assert [o["service"]["measured_cycles"] for o in collectives] == [
        190, 176, 525, 208, 176, 208, 208, 208, 208, 208, 208, 257]
    assert ops[55]["dependency_edges"]["raw_producer_pcs"]["ACT6"] == 54
    assert ops[35]["address_fields"]["me_wbase"]["unit"] == \
        "logical_engine_ROM_word_unmapped_to_physical_macro"
    assert ops[55]["address_fields"]["coll_src"]["unit"] == "VM_FP32_element"


@pytest.mark.parametrize("change", [
    lambda c: c.update(total_latency_cycles=8000),
    lambda c: c["resource_interfaces"]["collective_stage_VM"].update(write_ports_64B_per_cycle=3),
    lambda c: c["operations"][55]["collective_descriptor"].update(input_elements=1),
    lambda c: c["operations"][55]["service"].update(measured_cycles=1),
    lambda c: c["operations"][55]["address_fields"]["coll_src"].update(unit="HBM_byte"),
    lambda c: c["operations"][55]["dependency_edges"].update(isa_wait_completion_pcs=[56]),
    lambda c: c["source_sha256"].update({C.COLL: "0" * 64}),
])
def test_rejects_unsupported_latency_capacity_interface_or_source(change):
    c = copy.deepcopy(C.derive())
    change(c)
    with pytest.raises(AssertionError):
        C.validate(c)
