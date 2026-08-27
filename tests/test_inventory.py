from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_inventory_storage_is_exhaustively_classified() -> None:
    for path in sorted((ROOT / "data" / "inventory").glob("*.json")):
        inventory = json.loads(path.read_text(encoding="utf-8"))
        assert inventory["tensor_count"] > 0
        assert inventory["dense_bytes"] + inventory["routed_bytes"] == inventory["checkpoint_bytes"]
        assert (
            inventory["decode_dense_bytes"]
            + inventory["decode_routed_bytes"]
            + inventory["draft_dense_bytes"]
            + inventory["draft_routed_bytes"]
            + inventory["resident_only_bytes"]
            == inventory["checkpoint_bytes"]
        )
        assert sum(inventory["dtype_bytes"].values()) == inventory["checkpoint_bytes"]
        assert sum(inventory["decode_layer_dense_bytes"].values()) <= inventory[
            "decode_dense_bytes"
        ]
        assert sum(inventory["decode_layer_routed_bytes"].values()) <= inventory[
            "decode_routed_bytes"
        ]
        assert len(inventory["source_revision"] if "source_revision" in inventory else inventory["revision"]) == 40


def test_qwen_inventory_matches_pinned_all_bf16_release() -> None:
    inventory = json.loads(
        (ROOT / "data" / "inventory" / "qwen3-8b.json").read_text(encoding="utf-8")
    )
    assert inventory["repo"] == "Qwen/Qwen3-8B"
    assert inventory["revision"] == "b968826d9c46dd6066d109eabc6255188de91218"
    assert inventory["checkpoint_bytes"] == 2 * 8_190_735_360
    assert inventory["dtype_bytes"] == {"BF16": inventory["checkpoint_bytes"]}
    assert inventory["resident_only_bytes"] == 151_936 * 4_096 * 2
    assert inventory["decode_routed_bytes"] == 0
