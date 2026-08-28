from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.dispatch import (
    BF16_MAX_ENCODING,
    MODEL_SOURCE_SHA256,
    DispatchReferenceError,
    ExpertDispatchGroup,
    ExpertDispatchResult,
    dispatch_routed_experts_bf16,
)
from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    encode_binary32_rne,
)


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(_f32(value)).code


VALID_HIDDEN = (((_bf16(1),),),)
VALID_INDICES = ((0,),)
VALID_WEIGHTS = ((_f32(1),),)
LAYER0_HASH_ROUTE_PAYLOAD_SHA256 = (
    "b310d7aa41cf4967e3db21bb0b00b12357f4423b4347e71760a29d340031b897"
)
LOCKED_LOOKUP_EXPERT_IDS_SHA256 = (
    "53f915c3357a903cf63adb24469987436ea5f4102f0c8bfd8fa62165b5229c83"
)


def test_dispatch_reference_is_bound_to_pinned_model_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )


def test_dispatch_groups_experts_and_preserves_duplicate_selected_slots() -> None:
    hidden = (
        ((_bf16(1), _bf16(2)), (_bf16(3), _bf16(4))),
        ((_bf16(5), _bf16(6)), (_bf16(7), _bf16(8))),
    )
    indices = (
        (2, 0, 2),
        (1, 2, 0),
        (3, 3, 1),
        (0, 1, 2),
    )
    weights = tuple(
        tuple(_f32(token * 3 + slot + 1) for slot in range(3))
        for token in range(4)
    )

    assert dispatch_routed_experts_bf16(
        hidden,
        indices,
        weights,
        expert_count=4,
        top_k=3,
    ) == ExpertDispatchResult(
        batch_size=2,
        sequence_length=2,
        hidden_width=2,
        expert_count=4,
        top_k=3,
        groups=(
            ExpertDispatchGroup(
                expert_id=0,
                token_indices=(0, 1, 3),
                selected_slots=(1, 2, 0),
                hidden_bf16_rows=(hidden[0][0], hidden[0][1], hidden[1][1]),
                routed_weight_codes=(weights[0][1], weights[1][2], weights[3][0]),
            ),
            ExpertDispatchGroup(
                expert_id=1,
                token_indices=(1, 2, 3),
                selected_slots=(0, 2, 1),
                hidden_bf16_rows=(hidden[0][1], hidden[1][0], hidden[1][1]),
                routed_weight_codes=(weights[1][0], weights[2][2], weights[3][1]),
            ),
            ExpertDispatchGroup(
                expert_id=2,
                token_indices=(0, 0, 1, 3),
                selected_slots=(0, 2, 1, 2),
                hidden_bf16_rows=(
                    hidden[0][0],
                    hidden[0][0],
                    hidden[0][1],
                    hidden[1][1],
                ),
                routed_weight_codes=(
                    weights[0][0],
                    weights[0][2],
                    weights[1][1],
                    weights[3][2],
                ),
            ),
            ExpertDispatchGroup(
                expert_id=3,
                token_indices=(2, 2),
                selected_slots=(0, 1),
                hidden_bf16_rows=(hidden[1][0], hidden[1][0]),
                routed_weight_codes=(weights[2][0], weights[2][1]),
            ),
        ),
    )


def test_dispatch_checkpoint_derived_hash_route_known_answer() -> None:
    # The eight rows executed and independently checked in
    # docs/DEEPSEEK_V4_LOOKUP_EVIDENCE.md. Expert 35 appears in two different
    # token/slot locations and must form one ordered group.
    assert LAYER0_HASH_ROUTE_PAYLOAD_SHA256 == (
        "b310d7aa41cf4967e3db21bb0b00b12357f4423b4347e71760a29d340031b897"
    )
    assert LOCKED_LOOKUP_EXPERT_IDS_SHA256 == (
        "53f915c3357a903cf63adb24469987436ea5f4102f0c8bfd8fa62165b5229c83"
    )
    hidden = (tuple((_bf16(token + 1),) for token in range(8)),)
    indices = (
        (254, 222, 245, 200, 53, 35),
        (60, 125, 103, 159, 26, 243),
        (231, 125, 152, 11, 175, 35),
        (180, 179, 162, 221, 122, 118),
        (124, 226, 169, 96, 15, 209),
        (72, 144, 177, 61, 136, 51),
        (168, 0, 144, 124, 115, 44),
        (146, 142, 188, 18, 115, 175),
    )
    weights = tuple(
        tuple(_f32(token * 10 + slot + 1) for slot in range(6))
        for token in range(8)
    )
    observed = dispatch_routed_experts_bf16(
        hidden,
        indices,
        weights,
        expert_count=256,
        top_k=6,
    )
    group = next(group for group in observed.groups if group.expert_id == 35)
    assert group == ExpertDispatchGroup(
        expert_id=35,
        token_indices=(0, 2),
        selected_slots=(5, 5),
        hidden_bf16_rows=(hidden[0][0], hidden[0][2]),
        routed_weight_codes=(weights[0][5], weights[2][5]),
    )
    assert sum(len(group.token_indices) for group in observed.groups) == 48


def test_dispatch_matches_independent_nested_loop_randomly() -> None:
    rng = random.Random(0xD15A7C)
    for _ in range(1_000):
        batch_size = rng.randint(1, 4)
        sequence_length = rng.randint(1, 6)
        hidden_width = rng.randint(1, 8)
        expert_count = rng.randint(1, 24)
        top_k = rng.randint(1, expert_count)
        hidden = tuple(
            tuple(
                tuple(_bf16(rng.randint(-128, 128)) for _ in range(hidden_width))
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        token_count = batch_size * sequence_length
        indices = tuple(
            tuple(rng.randrange(expert_count) for _ in range(top_k))
            for _ in range(token_count)
        )
        weights = tuple(
            tuple(_f32(Fraction(rng.randrange(1_000), 1_000)) for _ in range(top_k))
            for _ in range(token_count)
        )

        observed = dispatch_routed_experts_bf16(
            hidden,
            indices,
            weights,
            expert_count=expert_count,
            top_k=top_k,
        )
        flat_hidden = tuple(vector for sequence in hidden for vector in sequence)
        expected_groups = []
        for expert_id in range(expert_count):
            assignments = [
                (token_index, selected_slot)
                for token_index in range(token_count)
                for selected_slot in range(top_k)
                if indices[token_index][selected_slot] == expert_id
            ]
            if not assignments:
                continue
            expected_groups.append(
                ExpertDispatchGroup(
                    expert_id=expert_id,
                    token_indices=tuple(item[0] for item in assignments),
                    selected_slots=tuple(item[1] for item in assignments),
                    hidden_bf16_rows=tuple(
                        flat_hidden[token_index]
                        for token_index, _ in assignments
                    ),
                    routed_weight_codes=tuple(
                        weights[token_index][selected_slot]
                        for token_index, selected_slot in assignments
                    ),
                )
            )
        assert observed == ExpertDispatchResult(
            batch_size=batch_size,
            sequence_length=sequence_length,
            hidden_width=hidden_width,
            expert_count=expert_count,
            top_k=top_k,
            groups=tuple(expected_groups),
        )
        assert sum(len(group.token_indices) for group in observed.groups) == (
            token_count * top_k
        )


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_dispatch_order_matches_pinned_torch_where_expression(device: str) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")

    rng = random.Random(0x70A7E)
    token_count = 257
    expert_count = 256
    top_k = 6
    indices = tuple(
        tuple(rng.randrange(expert_count) for _ in range(top_k))
        for _ in range(token_count)
    )
    hidden = (tuple((_bf16(token),) for token in range(token_count)),)
    weights = tuple(tuple(_f32(slot + 1) for slot in range(top_k)) for _ in indices)
    observed = dispatch_routed_experts_bf16(
        hidden,
        indices,
        weights,
        expert_count=expert_count,
        top_k=top_k,
    )
    observed_by_expert = {group.expert_id: group for group in observed.groups}
    tensor = torch.tensor(indices, dtype=torch.int64, device=device)
    counts = torch.bincount(tensor.flatten(), minlength=expert_count).cpu().tolist()
    for expert_id, count in enumerate(counts):
        token_indices, selected_slots = torch.where(tensor == expert_id)
        expected_pairs = tuple(
            zip(
                token_indices.cpu().tolist(),
                selected_slots.cpu().tolist(),
                strict=True,
            )
        )
        assert len(expected_pairs) == count
        if count == 0:
            assert expert_id not in observed_by_expert
            continue
        group = observed_by_expert[expert_id]
        assert tuple(zip(group.token_indices, group.selected_slots, strict=True)) == (
            expected_pairs
        )


@pytest.mark.parametrize(
    ("hidden", "indices", "weights", "experts", "top_k", "match"),
    [
        ((), (), (), 1, 1, "at least one batch"),
        (((),), (), (), 1, 1, "at least one position"),
        ((((_bf16(1),),), ((),)), (), (), 1, 1, "rectangular rank-3"),
        ((((),),), ((0,),), ((_f32(1),),), 1, 1, "at least one BF16"),
        (
            (((_bf16(1),), (_bf16(1), _bf16(2))),),
            ((0,), (0,)),
            ((_f32(1),), (_f32(1),)),
            1,
            1,
            "rectangular rank-3",
        ),
        ((((True,),),), VALID_INDICES, VALID_WEIGHTS, 1, 1, "16-bit BF16"),
        (
            (((BF16_MAX_ENCODING + 1,),),),
            ((0,),),
            ((_f32(1),),),
            1,
            1,
            "16-bit BF16",
        ),
        ((((0x7F80,),),), VALID_INDICES, VALID_WEIGHTS, 1, 1, "finite BF16"),
        (VALID_HIDDEN, (), (), 1, 1, "token count"),
        (VALID_HIDDEN, ((0, 0),), VALID_WEIGHTS, 1, 1, "top_k"),
        (VALID_HIDDEN, ((True,),), VALID_WEIGHTS, 1, 1, "must be in"),
        (VALID_HIDDEN, ((1,),), VALID_WEIGHTS, 1, 1, "must be in"),
        (VALID_HIDDEN, VALID_INDICES, (), 1, 1, "token count"),
        (
            VALID_HIDDEN,
            VALID_INDICES,
            ((_f32(1), _f32(2)),),
            1,
            1,
            "top_k",
        ),
        (VALID_HIDDEN, VALID_INDICES, ((True,),), 1, 1, "binary32"),
        (VALID_HIDDEN, VALID_INDICES, ((1 << 32,),), 1, 1, "binary32"),
        (VALID_HIDDEN, VALID_INDICES, ((0x7F800000,),), 1, 1, "finite"),
        (VALID_HIDDEN, VALID_INDICES, ((_f32(-1),),), 1, 1, "nonnegative"),
        (VALID_HIDDEN, VALID_INDICES, VALID_WEIGHTS, 0, 1, "expert_count"),
        (VALID_HIDDEN, VALID_INDICES, VALID_WEIGHTS, 1, 0, "top_k"),
        (VALID_HIDDEN, ((0, 0),), ((_f32(1), _f32(1)),), 1, 2, "exceed"),
    ],
)
def test_invalid_dispatch_requests_fail_closed(
    hidden, indices, weights, experts: int, top_k: int, match: str
) -> None:
    with pytest.raises(DispatchReferenceError, match=match):
        dispatch_routed_experts_bf16(
            hidden,
            indices,
            weights,
            expert_count=experts,
            top_k=top_k,
        )
