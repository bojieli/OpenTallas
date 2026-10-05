import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import w19_hc_simd_proof as proof


def test_contract_shape_and_scratch_are_explicit():
    c = proof.contract()
    assert (c["modeled_sms"], c["modeled_fp32_lanes_per_sm"]) == (32, 128)
    assert c["coefficient_bytes"] == 1966080
    assert c["global_scratch_bytes"] == 589824
    assert c["tree_passes"] == 12
    assert c["hardware_adopted"] is False


def test_tree_order_cancellation_witness():
    _, w, x = list(proof.controls())[1]
    assert np.all(proof.reference(w, x).view(np.uint32) == 0)
    # Serial chunk reduction yields 1; adjacent pair padded tree yields +0.
    assert np.float32(np.float32(np.float32(2**25) + 1) - 2**25) + 1 == 1


def test_subnormal_survives_and_zero_is_positive():
    _, w, x = list(proof.controls())[3]
    assert np.all(proof.reference(w, x).view(np.uint32) == 1)
    w.fill(-0.0)
    assert np.all(proof.reference(w, x).view(np.uint32) == 0)


def test_padded_reduction_boundaries_match_golden():
    _, w, x = next(proof.controls())
    stages = list(proof.reference_stages(w, x))
    assert [s.shape[1] for s in stages] == [4096, 2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]
    assert np.all(stages[0][:, 2560:].view(np.uint32) == 0)
    assert np.array_equal(stages[-1][:, 0].view(np.uint32), proof.reference(w, x).view(np.uint32))


@pytest.mark.parametrize("bad", ["shape", "dtype", "activation", "nan"])
def test_reject_unsupported_fixture(bad):
    _, w, x = next(proof.controls())
    if bad == "shape":
        w = w[:, :-1]
    elif bad == "dtype":
        w = w.astype(np.float16)
    elif bad == "activation":
        x[0] = np.float32(1.000001)
    else:
        w[0, 0] = np.nan
    with pytest.raises(ValueError):
        proof.reference(w, x)
