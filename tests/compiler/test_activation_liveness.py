"""Backend-neutral activation arena allocation tests."""

from __future__ import annotations

import pytest

from compiler.backends.activation_liveness import (
    ActivationLivenessError,
    LiveBuffer,
    allocate_live_buffers,
)


def test_closed_disjoint_intervals_reuse_one_exact_slot() -> None:
    arenas, allocation = allocate_live_buffers(
        [
            LiveBuffer("a", 4096, "bf16", 0, 1),
            LiveBuffer("b", 4096, "bf16", 2, 4),
            # Starts at a's last use, so the closed intervals overlap.
            LiveBuffer("c", 4096, "bf16", 1, 1),
        ],
        slot_prefix="live",
    )

    assert allocation == {"a": "live0000", "c": "live0001", "b": "live0000"}
    assert len(arenas) == 2
    assert [tenant.key for tenant in arenas[0].tenants] == ["a", "b"]
    assert arenas[0].tenants[0].last_use < arenas[0].tenants[1].first_use


def test_size_dtype_and_exclusive_requests_never_alias() -> None:
    arenas, allocation = allocate_live_buffers(
        [
            LiveBuffer("base", 64, "bf16", 0, 0),
            LiveBuffer("wide", 128, "bf16", 1, 1),
            LiveBuffer("typed", 64, "u32", 1, 1),
            LiveBuffer("private", 64, "bf16", 1, 1, exclusive=True),
            LiveBuffer("later", 64, "bf16", 2, 2),
        ]
    )

    assert len(arenas) == 4
    assert allocation["base"] == allocation["later"]
    assert allocation["wide"] != allocation["base"]
    assert allocation["typed"] != allocation["base"]
    assert allocation["private"] != allocation["base"]
    assert arenas[int(allocation["private"].removeprefix("arena"))].exclusive


@pytest.mark.parametrize(
    "buffers",
    [
        [LiveBuffer("", 1, "u8", 0, 0)],
        [LiveBuffer("bad-size", 0, "u8", 0, 0)],
        [LiveBuffer("bad-type", 1, "", 0, 0)],
        [LiveBuffer("bad-range", 1, "u8", 2, 1)],
        [LiveBuffer("same", 1, "u8", 0, 0), LiveBuffer("same", 1, "u8", 1, 1)],
    ],
)
def test_invalid_lifetime_requests_fail_closed(buffers: list[LiveBuffer]) -> None:
    with pytest.raises(ActivationLivenessError):
        allocate_live_buffers(buffers)
