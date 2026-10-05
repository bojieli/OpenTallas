"""RoPE oracle checks the shipped configuration at the exact shard position."""

from pathlib import Path

from tools import v41_fullshape_rope_oracle as O


def test_200k_layer0_oracle_matches_independent_math():
    config = O.ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json"
    rec = O.build(199999, config)
    assert rec["position"] == 199999
    assert set(rec["modes"]) == {"plain", "yarn"}
    for mode in rec["modes"].values():
        assert mode["freq_count"] == 32
        assert len(mode["crom_pair_words_hex"]) == 32
        assert mode["independent_math_ulp_mismatches"] == 0
