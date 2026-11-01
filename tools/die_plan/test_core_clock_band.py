import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import core_clock_band as policy


def typed_core(kit):
    (kit / "boundary_guard_context.json").write_text(json.dumps({"source_core_json": "core.json"}))
    (kit / "core.json").write_text(json.dumps({"clock_contract": {
        "kind": "hard_core_latency", "ruling": "COORD 10-24",
        "target_applies_at": "parent partition tap",
    }}))


def test_ordinary_typed_core_publishes_intrinsic_latency(tmp_path):
    typed_core(tmp_path)
    assert policy.band_policy(tmp_path) == "info"


def test_geometry_only_interior_entry_is_not_a_clock_model(tmp_path):
    typed_core(tmp_path)
    (tmp_path / "master_slice.json").write_text(json.dumps({"islands": [{"name": "entry"}]}))
    assert policy.band_policy(tmp_path) == "info"


def test_partition_cannot_borrow_core_mean_policy(tmp_path):
    assert policy.band_policy(tmp_path) == "gate"
    typed_core(tmp_path)
    (tmp_path / "core.json").write_text('{"clock_contract":{"kind":"partition_tap"}}')
    assert policy.band_policy(tmp_path) == "gate"


@pytest.mark.parametrize("explicit", [None, "gate", "info"])
def test_promised_clock_model_keeps_its_policy(tmp_path, explicit):
    typed_core(tmp_path)
    tree = {"nodes": [{"name": "root"}]}
    if explicit is not None:
        tree["model_qualification"] = {"band_policy": explicit}
    (tmp_path / "master_slice.json").write_text(json.dumps({"core_tree": tree}))
    assert policy.band_policy(tmp_path) == (explicit or "gate")


def test_malformed_explicit_model_is_not_an_info_escape(tmp_path):
    typed_core(tmp_path)
    (tmp_path / "master_slice.json").write_text(json.dumps({"core_tree": {
        "nodes": [{"name": "root"}], "model_qualification": {"band_policy": "ignore"},
    }}))
    with pytest.raises(ValueError):
        policy.band_policy(tmp_path)


def test_empty_promised_model_does_not_borrow_typed_info(tmp_path):
    typed_core(tmp_path)
    (tmp_path / "master_slice.json").write_text('{"core_tree":{}}')
    assert policy.band_policy(tmp_path) == "gate"


def test_invalid_promised_model_fails_closed(tmp_path):
    typed_core(tmp_path)
    (tmp_path / "master_slice.json").write_text('{"core_tree":null}')
    with pytest.raises(ValueError):
        policy.band_policy(tmp_path)


def test_broken_typed_reference_still_rejected(tmp_path):
    typed_core(tmp_path)
    j = json.loads((tmp_path / "core.json").read_text())
    j["clock_contract"]["io_reference_ps"] = {"kind": "plan_declared", "tt": 250, "ff": 202.5}
    (tmp_path / "core.json").write_text(json.dumps(j))
    with pytest.raises(ValueError):
        policy.band_policy(tmp_path)
