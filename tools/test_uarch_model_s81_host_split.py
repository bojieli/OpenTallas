"""HOST partition admission requires actual source/bit/clock inventories."""
import hashlib
import json

import pytest

from uarch_model_s81_host_split import model


def fixture(tmp_path, *, change_abi=None, change_whole=None, change_row=None):
    source = tmp_path / "source.sv"
    source.write_text("module source; endmodule\n")
    row = {"source_sha256": {"source.sv": hashlib.sha256(source.read_bytes()).hexdigest()},
           "storage": {"data_fifo_bits": [792, 776, 792, 792], "control_fifo_bits": 280,
                       "new_projected_sd_fifo_bits": 3432, "original_sd_fifo_bits": 2312,
                       "added_sd_fifo_bits": 1120,
                       "pointer_decode_replication": {"shared_cross_leaf_pointer_wires": 0}}}
    abi = {"full_abi_bits": 292, "ports": [{"abi_bit": i, "producer": f"leaf.bit{i}"} for i in range(292)]}
    whole = {"parent_registers": 0,
             "actual_children": [{"clocks": [f"clock{2*i}", f"clock{2*i+1}"]} for i in range(6)],
             "clock_sources": {"total_physical_entry_pins": 12, "old_entry_pins": 5, "added_entry_pins": 7}}
    if change_abi:
        change_abi(abi)
    if change_whole:
        change_whole(whole)
    if change_row:
        change_row(row)
    files = {"host_split_model.json": row, "source_graph.json": abi, "whole_host_graph.json": whole}
    hashes = {}
    for name, data in files.items():
        path = tmp_path / name
        path.write_text(json.dumps(data))
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(model_path=tmp_path / "host_split_model.json", root=tmp_path,
                model_sha256=hashes.pop("host_split_model.json"), graph_hashes=hashes)


def test_measured_component_does_not_qualify_parent_or_token(tmp_path):
    value = model(**fixture(tmp_path))
    assert value["actual_clock_delivery_pins"] == 12
    assert value["actual_parent_area_delta_um2"] is None
    assert not value["physical_build_admissible"]
    assert not value["normal_token_calendar_qualified"]
    assert not value["production_throughput_qualified"]


@pytest.mark.parametrize("mutation", [
    lambda g: g["ports"][-1].update(abi_bit=0),
    lambda g: g["ports"][-1].update(producer="leaf.bit0"),
])
def test_missing_or_aliased_producer_is_refused(tmp_path, mutation):
    with pytest.raises(ValueError, match="292 ABI"):
        model(**fixture(tmp_path, change_abi=mutation))


def test_duplicate_clock_is_refused(tmp_path):
    with pytest.raises(ValueError, match="clock source inventory"):
        model(**fixture(tmp_path, change_whole=lambda g: g["actual_children"][0].update(clocks=["clock0", "clock0"])))


@pytest.mark.parametrize("mutation", [
    lambda r: r["storage"].update(added_sd_fifo_bits=1121),
    lambda r: r["storage"]["pointer_decode_replication"].update(shared_cross_leaf_pointer_wires=1),
])
def test_unpriced_storage_or_shared_pointer_is_refused(tmp_path, mutation):
    with pytest.raises(ValueError, match="storage or independent pointer"):
        model(**fixture(tmp_path, change_row=mutation))


def test_source_rtl_drift_is_refused(tmp_path):
    args = fixture(tmp_path)
    (tmp_path / "source.sv").write_text("changed after source pin\n")
    with pytest.raises(ValueError, match="implemented source differs"):
        model(**args)
