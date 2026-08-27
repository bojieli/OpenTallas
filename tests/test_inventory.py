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
