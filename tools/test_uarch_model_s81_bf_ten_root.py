"""A source-bound census must not silently become a physical capacity proof."""
import hashlib
import json

import pytest

from uarch_model_s81_bf_ten_root import model


def census_file(tmp_path, *, mutation=None):
    sinks = [5002, 4628, 3660, 4874, 5680, 5608, 5608, 5608, 6738, 6087]
    # Small synthetic geometry isolates admission checks from the PDK census.
    data = {"sequential_cells": 53493, "clock_cells_excluded": 3468,
            "mapped_netlist_sha256_zstd": "a" * 64, "routed_def_sha256_zstd": "b" * 64,
            "groups": {str(i): {"sinks": n, "area_um2": 100, "old_span_um": [100, 100]}
                       for i, n in enumerate(sinks)},
            "data_cut_edges": [{"source": 0, "destination": 1, "bits": 1246}]}
    if mutation:
        mutation(data)
    path = tmp_path / "census.json"
    path.write_text(json.dumps(data))
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_complete_census_does_not_admit_unknown_physical_cuts(tmp_path):
    path, digest = census_file(tmp_path)
    value = model(census_path=path, census_sha256=digest, columns=2)
    assert value["replicas"]["root_delivery_pins_total"] == 20
    assert value["four_lane_source_interface"]["total_pin_bits"] == 317
    assert value["routing"]["new_parent_channel_capacity"] is None
    assert value["area"]["new_total_area_um2"] is None
    assert value["physical_build_admissible"] is False
    assert value["native_physical_qualified"] is False
    assert value["production_throughput_qualified"] is False


def test_source_content_change_is_refused(tmp_path):
    path, digest = census_file(tmp_path)
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="hash mismatch"):
        model(census_path=path, census_sha256=digest)


@pytest.mark.parametrize("mutation", [
    lambda d: d["groups"]["0"].update(sinks=5001),
    lambda d: d["data_cut_edges"].append({"source": 0, "destination": 1, "bits": 1}),
    lambda d: d["data_cut_edges"][0].update(destination=10),
    lambda d: d.update(data_cut_edges=[]),
])
def test_rehashed_incomplete_or_ambiguous_source_is_refused(tmp_path, mutation):
    path, digest = census_file(tmp_path, mutation=mutation)
    with pytest.raises(ValueError):
        model(census_path=path, census_sha256=digest)


@pytest.mark.parametrize("columns", [0, -1, True, 1.5])
def test_replica_count_must_be_explicit_integer(tmp_path, columns):
    path, digest = census_file(tmp_path)
    with pytest.raises(ValueError, match="positive integer"):
        model(census_path=path, census_sha256=digest, columns=columns)
