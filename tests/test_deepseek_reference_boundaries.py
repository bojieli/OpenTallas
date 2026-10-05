"""Tests for joining vendor and accelerator DeepSeek boundary evidence."""

from tools.capture_deepseek_reference_boundaries import (
    compare_accelerator_boundaries,
)


def _boundary(digest: str, shape: list[int]) -> dict:
    return {"payload_sha256": digest, "shape": shape}


def test_comparison_ignores_transport_rank_when_raw_codes_match() -> None:
    reference = [_boundary("same", [1, 32, 4, 4096])]
    accelerator = {
        "lanes": [
            {
                "lane": "rom",
                "boundaries": [_boundary("same", [32, 4, 4096])],
            }
        ]
    }

    comparison = compare_accelerator_boundaries(reference, accelerator)[0]

    assert comparison["boundary_counts_equal"] is True
    assert comparison["exact_boundary_count"] == 1
    assert comparison["first_divergent_boundary"] is None
    assert comparison["first_divergence"] is None


def test_comparison_reports_the_first_payload_difference_per_lane() -> None:
    reference = [
        _boundary("zero", [1]),
        _boundary("reference", [1]),
    ]
    accelerator = {
        "lanes": [
            {
                "lane": "rom",
                "boundaries": [
                    _boundary("zero", [1]),
                    _boundary("rom", [1]),
                ],
            },
            {
                "lane": "hbm",
                "boundaries": [
                    _boundary("zero", [1]),
                    _boundary("hbm", [1]),
                ],
            },
        ]
    }

    comparisons = compare_accelerator_boundaries(reference, accelerator)

    assert [entry["lane"] for entry in comparisons] == ["rom", "hbm"]
    assert [entry["first_divergent_boundary"] for entry in comparisons] == [1, 1]
    assert [entry["exact_boundary_count"] for entry in comparisons] == [1, 1]
    assert comparisons[0]["first_divergence"]["reference"] == reference[1]
    assert (
        comparisons[0]["first_divergence"]["accelerator"]
        == (accelerator["lanes"][0]["boundaries"][1])
    )


def test_comparison_fails_closed_on_different_boundary_counts() -> None:
    reference = [_boundary("zero", [1]), _boundary("one", [1])]
    accelerator = {
        "lanes": [
            {
                "lane": "rom",
                "boundaries": [_boundary("zero", [1])],
            }
        ]
    }

    comparison = compare_accelerator_boundaries(reference, accelerator)[0]

    assert comparison["boundary_counts_equal"] is False
    assert comparison["boundaries_compared"] == 1
    assert comparison["exact_boundary_count"] == 1
    assert comparison["first_divergent_boundary"] == 1
    assert comparison["first_divergence"]["reference"] == reference[1]
    assert comparison["first_divergence"]["accelerator"] is None
