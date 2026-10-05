"""Tests for the retained DeepSeek ROM/HBM activation-boundary diagnostic."""

from tools.bisect_deepseek_lane_activations import compare_boundaries


def _row(index: int, digest: str) -> dict:
    return {
        "boundary": index,
        "boundary_kind": "layer_input",
        "dtype": "BF16",
        "shape": [1, 4, 4096],
        "elements": 16384,
        "payload_sha256": digest,
    }


def test_compare_boundaries_accepts_identical_raw_payloads() -> None:
    rows = [_row(0, "a"), _row(1, "b")]
    comparison = compare_boundaries(
        {"boundaries": rows}, {"boundaries": [dict(row) for row in rows]}
    )

    assert comparison == {
        "boundaries_compared": 2,
        "boundary_counts_equal": True,
        "all_boundaries_equal": True,
        "first_divergent_boundary": None,
        "first_divergence": None,
    }


def test_compare_boundaries_reports_first_payload_mismatch() -> None:
    left = [_row(0, "same"), _row(1, "rom")]
    right = [_row(0, "same"), _row(1, "hbm")]
    comparison = compare_boundaries(
        {"boundaries": left}, {"boundaries": right}
    )

    assert comparison["boundary_counts_equal"] is True
    assert comparison["all_boundaries_equal"] is False
    assert comparison["first_divergent_boundary"] == 1
    assert comparison["first_divergence"] == {
        "rom": left[1],
        "hbm": right[1],
    }


def test_compare_boundaries_fails_closed_on_a_missing_boundary() -> None:
    left = [_row(0, "same"), _row(1, "extra")]
    right = [_row(0, "same")]
    comparison = compare_boundaries(
        {"boundaries": left}, {"boundaries": right}
    )

    assert comparison["boundaries_compared"] == 1
    assert comparison["boundary_counts_equal"] is False
    assert comparison["all_boundaries_equal"] is False
    assert comparison["first_divergent_boundary"] == 1
    assert comparison["first_divergence"] == {"rom": left[1], "hbm": None}


def test_compare_boundaries_includes_transaction_and_phase_identity() -> None:
    rom = _row(0, "same") | {"transaction": 0, "phase": "prefill"}
    hbm = _row(0, "same") | {"transaction": 1, "phase": "decode"}

    comparison = compare_boundaries(
        {"boundaries": [rom]}, {"boundaries": [hbm]}
    )

    assert comparison["all_boundaries_equal"] is False
    assert comparison["first_divergent_boundary"] == 0
    assert comparison["first_divergence"] == {"rom": rom, "hbm": hbm}
