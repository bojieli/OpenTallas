"""Four-die/four-stack V4.1 compressed-KV address, capacity and ring checks."""

import json
from pathlib import Path

import pytest

from runtime.prefill import v41_hbm_placement as H
from runtime.prefill.v41_main_kv_row import pack_main_row
from runtime.prefill.v41_aux_kv_rows import pack_index_row, pack_window_row


ROOT = Path(__file__).resolve().parents[1]


def test_regions_fit_shipping_stack_capacity_and_never_overlap():
    p = H.Placement()
    tech = json.loads((ROOT / "configs/hardware/technology.json").read_text())
    assert p.stack_capacity_bytes == tech["hbm"]["hbm3e"]["stack_capacity_bytes"]["value"]
    assert set(p.used_bytes) == {(d, s) for d in range(4) for s in range(4)}
    assert set(p.used_bytes.values()) == {59_023_360}
    for die in range(4):
        for stack in range(4):
            regions = sorted((r for r in p.regions.values() if r.die == die and r.stack == stack), key=lambda r: r.base)
            assert regions[0].base == 0 and regions[-1].end == p.used_bytes[(die, stack)]
            assert all(a.end <= b.base for a, b in zip(regions, regions[1:]))
            assert all(r.base % 32 == r.pitch % 32 == 0 and r.end <= p.stack_capacity_bytes for r in regions)
            assert all(r.base % H.INDEX_BLOCK == 0 for r in regions if r.role == "index")
    with pytest.raises(ValueError, match="capacity"):
        H.Placement(stack_capacity_bytes=59_023_359)


def test_every_reduced_address_is_unique_and_padded_rows_do_not_alias():
    p = H.Placement(max_context=512)
    seen = set()
    for owner in H.OWNERS:
        for role in ("main", "index"):
            for row in range(512 // H.RATIOS[owner]):
                a = p.compressed(role, owner, row)
                key = (a.die, a.stack, a.byte)
                assert key not in seen
                seen.add(key)
                assert a.byte % 32 == 0
                region = p.regions[(a.die, a.stack, role, owner)]
                assert region.base <= a.byte < region.end
                if role == "index":
                    assert a.pitch == 0 and a.size == 68
                    assert region.base <= a.scale_byte < region.end
                else:
                    assert a.size <= a.pitch and a.byte + a.pitch <= region.end
    # Every 16-row group is wholly on one die and stack; successive groups
    # rotate dies first, stacks second.
    assert [(p.compressed("main", 20, 16*g).die, p.compressed("main", 20, 16*g).stack)
            for g in range(16)] == [(g % 4, g // 4) for g in range(16)]
    with pytest.raises(ValueError, match="capacity"):
        p.compressed("main", 2, 256)


def test_owner_handoff_and_window_rollover_read_conversion():
    p = H.Placement(max_context=512)
    h = H.SparseHBM(p)
    main = pack_main_row([1] * 512, [0x38] * 32)  # 0.5 * scale 1
    index = pack_index_row([2] * 128, [127] * 4)  # 1 * scale 1
    window = pack_window_row([0x38] * 512, [127] * 16)  # 1 * scale 1
    assert h.write_compressed("main", 20, 0, main).size == 288
    index_addr = h.write_compressed("index", 20, 0, index)
    assert index_addr.pitch == 0 and index_addr.scale_byte is not None
    assert h.rows[(index_addr.die, index_addr.stack, index_addr.byte)] == index[:64]
    assert h.rows[(index_addr.die, index_addr.stack, index_addr.scale_byte)] == index[64:]
    assert h.read_compressed("main", 24, 0) == bytes([0x30] * 512)  # E4M3 0.5
    assert all(v == 1 for v in h.read_compressed("index", 36, 0))
    assert H.Placement.owner_for_layer(7) == 2
    assert H.Placement.owner_for_layer(8) == 8
    assert H.Placement.owner_for_layer(19) == 14
    assert H.Placement.owner_for_layer(20) == H.Placement.owner_for_layer(39) == 20
    with pytest.raises(ValueError, match="pure window"):
        h.read_compressed("main", 0, 0)
    addrs0 = h.write_window(24, 0, window)
    assert len({(a.die, a.stack, a.byte) for a in addrs0}) == 4
    assert all(a.stack == 0 and a.size == 528 and a.pitch == 544 for a in addrs0)
    assert all(v == 1 for v in h.read_window(24, 0, 3))
    h.write_window(24, 127, window)
    assert p.window(24, 0, 0).byte == p.window(24, 128, 0).byte
    h.write_window(24, 128, window)
    with pytest.raises(ValueError, match="stale"):
        h.read_window(24, 0, 0)
    assert all(v == 1 for v in h.read_window(24, 128, 0))


def test_rack_stage_14_scope_and_28_user_fill():
    # Rack stage 14 starts owner 20 and window layers 20/21. The generic
    # all-40-layer map is a conservative envelope, not its actual allocation.
    p = H.Placement(owners=(20,), window_layers=(20, 21))
    assert len(p.regions) == 4 * (4 * 2 + 2)
    assert sum(p.used_bytes[(0, s)] for s in range(4)) == 93_462_528
    assert max(p.used_bytes.values()) == 23_400_448
    assert 28 * max(p.used_bytes.values()) == 655_212_544
    assert 28 * max(p.used_bytes.values()) < H.STACK_CAPACITY_BYTES
    assert 28 * max(p.used_bytes.values()) < 36_000_000_000
    with pytest.raises(ValueError, match="owner"):
        p.compressed("main", 2, 0)
    with pytest.raises(ValueError, match="window"):
        p.window(19, 0, 0)


def test_owner_map_matches_pinned_config():
    config = json.loads((ROOT / "configs/models/candidates/deepseek-v4.1-flash.json").read_text())
    op = config["metadata"]["operator_config"]
    assert op["kv_source_layer_ids"] == list(H.OWNERS)
    assert op["index_source_layer_ids"] == [2, 8, 14, 20, 24, 28, 32, 36]
    assert {owner: op["compress_ratios"][owner] for owner in H.OWNERS} == H.RATIOS
    assert config["max_context_tokens"] == H.MAX_CONTEXT
    assert op["window_tokens"] == H.WINDOW_SLOTS
