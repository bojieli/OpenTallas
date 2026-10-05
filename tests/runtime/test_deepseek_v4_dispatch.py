from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import random

import pytest

from runtime.reference.dispatch import (
    BF16_MAX_ENCODING,
    MODEL_SOURCE_SHA256,
    DispatchReferenceError,
    ExpertDispatchGroup,
    ExpertDispatchResult,
    ExpertOutputGroup,
    ExpertReduceResult,
    dispatch_routed_experts_bf16,
    reduce_expert_outputs_bf16,
)
from runtime.reference.formats import (
    binary32_add,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    decode_bf16,
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


def _dispatch_for_reduce() -> ExpertDispatchResult:
    hidden = (((_bf16(1), _bf16(2)), (_bf16(3), _bf16(4))),)
    return dispatch_routed_experts_bf16(
        hidden,
        ((2, 0, 2), (1, 2, 0)),
        ((_f32(1), _f32(2), _f32(3)), (_f32(4), _f32(5), _f32(6))),
        expert_count=3,
        top_k=3,
    )


def _routed_for_reduce() -> tuple[ExpertOutputGroup, ...]:
    return (
        ExpertOutputGroup(0, ((_bf16(1), _bf16(2)), (_bf16(3), _bf16(4)))),
        ExpertOutputGroup(1, ((_bf16(5), _bf16(6)),)),
        ExpertOutputGroup(
            2,
            (
                (_bf16(7), _bf16(8)),
                (_bf16(9), _bf16(10)),
                (_bf16(11), _bf16(12)),
            ),
        ),
    )


def test_expert_reduce_preserves_duplicate_slots_and_adds_shared_last() -> None:
    dispatch = _dispatch_for_reduce()
    routed = _routed_for_reduce()
    shared = (((_bf16(13), _bf16(14)), (_bf16(15), _bf16(16))),)

    assert reduce_expert_outputs_bf16(dispatch, routed, shared) == ExpertReduceResult(
        output_bf16_codes=(((_bf16(30), _bf16(34)), (_bf16(34), _bf16(38))),),
        output_saturation_count=0,
    )


def _independent_expert_reduce(
    dispatch: ExpertDispatchResult,
    routed: tuple[ExpertOutputGroup, ...],
    shared: tuple[tuple[tuple[int, ...], ...], ...],
) -> ExpertReduceResult:
    token_count = dispatch.batch_size * dispatch.sequence_length
    shared_flat = tuple(row for sequence in shared for row in sequence)
    output = []
    saturation_count = 0
    for token_index in range(token_count):
        output_row = []
        for column in range(dispatch.hidden_width):
            expert_codes = []
            for dispatch_group, output_group in zip(
                dispatch.groups, routed, strict=True
            ):
                slots = []
                for source_token, row in zip(
                    dispatch_group.token_indices,
                    output_group.output_bf16_rows,
                    strict=True,
                ):
                    if source_token != token_index:
                        continue
                    decoded = decode_bf16(row[column])
                    assert decoded.value is not None
                    slots.append(encode_binary32_rne(decoded.value))
                if slots:
                    expert_codes.append(binary32_balanced_sum(slots))
            shared_value = decode_bf16(shared_flat[token_index][column])
            assert shared_value.value is not None
            combined = binary32_add(
                binary32_balanced_sum(expert_codes),
                encode_binary32_rne(shared_value.value),
            )
            converted = binary32_bits_to_bf16_rne(combined)
            saturation_count += int(converted.saturated)
            output_row.append(converted.code)
        output.append(tuple(output_row))
    shaped = tuple(
        tuple(
            output[batch * dispatch.sequence_length + position]
            for position in range(dispatch.sequence_length)
        )
        for batch in range(dispatch.batch_size)
    )
    return ExpertReduceResult(shaped, saturation_count)


def test_expert_reduce_matches_independent_randomized_composition() -> None:
    rng = random.Random(0x4558_5052_4544_5543)
    palette = (
        0,
        0x0001,
        0x8001,
        _bf16(Fraction(1, 4)),
        _bf16(Fraction(-1, 4)),
        _bf16(1),
        _bf16(-1),
        _bf16(2),
        _bf16(-2),
        _bf16(8),
        _bf16(-8),
    )
    for _ in range(200):
        batch_size = rng.randint(1, 3)
        sequence_length = rng.randint(1, 4)
        hidden_width = rng.randint(1, 8)
        expert_count = rng.randint(2, 12)
        top_k = rng.randint(1, min(6, expert_count))
        hidden = tuple(
            tuple(
                tuple(rng.choice(palette) for _ in range(hidden_width))
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
            tuple(_f32(Fraction(1, top_k)) for _ in range(top_k))
            for _ in range(token_count)
        )
        dispatch = dispatch_routed_experts_bf16(
            hidden,
            indices,
            weights,
            expert_count=expert_count,
            top_k=top_k,
        )
        routed = tuple(
            ExpertOutputGroup(
                group.expert_id,
                tuple(
                    tuple(rng.choice(palette) for _ in range(hidden_width))
                    for _ in group.token_indices
                ),
            )
            for group in dispatch.groups
        )
        shared = tuple(
            tuple(
                tuple(rng.choice(palette) for _ in range(hidden_width))
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        assert reduce_expert_outputs_bf16(dispatch, routed, shared) == (
            _independent_expert_reduce(dispatch, routed, shared)
        )


def test_expert_reduce_counts_final_saturation_and_poisons_intermediate_overflow() -> (
    None
):
    one_dispatch = dispatch_routed_experts_bf16(
        (((0,),),),
        ((0,),),
        ((_f32(1),),),
        expert_count=1,
        top_k=1,
    )
    saturated = reduce_expert_outputs_bf16(
        one_dispatch,
        (ExpertOutputGroup(0, ((0x7F7F,),)),),
        (((0x7B00,),),),
    )
    assert saturated == ExpertReduceResult((((0x7F7F,),),), 1)

    overflow_dispatch = dispatch_routed_experts_bf16(
        (((0,),),),
        ((0, 1),),
        ((_f32(1), _f32(1)),),
        expert_count=2,
        top_k=2,
    )
    with pytest.raises(DispatchReferenceError, match="binary32 accumulation overflow"):
        reduce_expert_outputs_bf16(
            overflow_dispatch,
            (
                ExpertOutputGroup(0, ((0x7F7F,),)),
                ExpertOutputGroup(1, ((0x7F7F,),)),
            ),
            (((0,),),),
        )


def test_expert_reduce_rejects_malformed_output_groups() -> None:
    dispatch = _dispatch_for_reduce()
    routed = _routed_for_reduce()
    cases = (
        (object(), "must be a sequence"),
        (routed[:-1], "align one-for-one"),
        ((object(), *routed[1:]), "must be an ExpertOutputGroup"),
        ((replace(routed[0], expert_id=1), *routed[1:]), "must match dispatch"),
        (
            (
                replace(routed[0], output_bf16_rows=routed[0].output_bf16_rows[:1]),
                *routed[1:],
            ),
            "row count",
        ),
        (
            (
                replace(
                    routed[0],
                    output_bf16_rows=((_bf16(1),), *routed[0].output_bf16_rows[1:]),
                ),
                *routed[1:],
            ),
            "hidden width",
        ),
        (
            (
                replace(
                    routed[0],
                    output_bf16_rows=(
                        (True, _bf16(2)),
                        *routed[0].output_bf16_rows[1:],
                    ),
                ),
                *routed[1:],
            ),
            "16-bit BF16",
        ),
        (
            (
                replace(
                    routed[0],
                    output_bf16_rows=(
                        (0x7F80, _bf16(2)),
                        *routed[0].output_bf16_rows[1:],
                    ),
                ),
                *routed[1:],
            ),
            "finite BF16",
        ),
    )
    shared = (((_bf16(1), _bf16(2)), (_bf16(3), _bf16(4))),)
    for malformed, match in cases:
        with pytest.raises(DispatchReferenceError, match=match):
            reduce_expert_outputs_bf16(dispatch, malformed, shared)


def test_expert_reduce_rejects_malformed_shared_output() -> None:
    dispatch = _dispatch_for_reduce()
    routed = _routed_for_reduce()
    cases = (
        (object(), "must be a sequence"),
        ((), "at least one batch"),
        ((((_bf16(1), _bf16(2)),),), "shape must match"),
        (
            (
                ((_bf16(1), _bf16(2)), (_bf16(3), _bf16(4))),
                ((_bf16(1), _bf16(2)), (_bf16(3), _bf16(4))),
            ),
            "shape must match",
        ),
        ((((_bf16(1),), (_bf16(2),)),), "shape must match"),
        ((((True, _bf16(2)), (_bf16(3), _bf16(4))),), "16-bit BF16"),
        ((((0x7F80, _bf16(2)), (_bf16(3), _bf16(4))),), "finite BF16"),
    )
    for malformed, match in cases:
        with pytest.raises(DispatchReferenceError, match=match):
            reduce_expert_outputs_bf16(dispatch, routed, malformed)


def test_expert_reduce_rejects_forged_dispatch_invariants() -> None:
    dispatch = _dispatch_for_reduce()
    groups = dispatch.groups
    group0, group1, group2 = groups
    malformed_groups = (
        ((object(),), "must be an ExpertDispatchGroup"),
        ((group1, group0, group2), "ascending expert IDs"),
        ((replace(group0, expert_id=3), group1, group2), "expert_id must be in"),
        (
            (
                replace(
                    group0,
                    token_indices=(),
                    selected_slots=(),
                    hidden_bf16_rows=(),
                    routed_weight_codes=(),
                ),
                group1,
                group2,
            ),
            "must be nonempty",
        ),
        ((replace(group0, selected_slots=(1,)), group1, group2), "lengths must match"),
        (
            (replace(group0, token_indices=(0, 2)), group1, group2),
            "token_index must be in",
        ),
        (
            (replace(group0, selected_slots=(1, 3)), group1, group2),
            "selected_slot must be in",
        ),
        (
            (
                group0,
                group1,
                replace(
                    group2,
                    token_indices=tuple(reversed(group2.token_indices)),
                    selected_slots=tuple(reversed(group2.selected_slots)),
                    hidden_bf16_rows=tuple(reversed(group2.hidden_bf16_rows)),
                    routed_weight_codes=tuple(reversed(group2.routed_weight_codes)),
                ),
            ),
            "must ascend by token then selected slot",
        ),
        (
            (
                group0,
                replace(group1, token_indices=(0,), selected_slots=(1,)),
                group2,
            ),
            "each token/selected-slot pair exactly once",
        ),
        (
            (
                replace(
                    group0, hidden_bf16_rows=((_bf16(1),), group0.hidden_bf16_rows[1])
                ),
                group1,
                group2,
            ),
            "must have hidden width",
        ),
        (
            (
                replace(
                    group0,
                    hidden_bf16_rows=((0x7F80, _bf16(2)), group0.hidden_bf16_rows[1]),
                ),
                group1,
                group2,
            ),
            "finite BF16",
        ),
        (
            (
                group0,
                group1,
                replace(
                    group2,
                    hidden_bf16_rows=(
                        (_bf16(99), _bf16(2)),
                        *group2.hidden_bf16_rows[1:],
                    ),
                ),
            ),
            "one hidden row",
        ),
        (
            (
                replace(
                    group0, routed_weight_codes=(True, group0.routed_weight_codes[1])
                ),
                group1,
                group2,
            ),
            "must be binary32",
        ),
        (
            (
                replace(
                    group0,
                    routed_weight_codes=(0x7F800000, group0.routed_weight_codes[1]),
                ),
                group1,
                group2,
            ),
            "finite binary32",
        ),
        (
            (
                replace(
                    group0,
                    routed_weight_codes=(_f32(-1), group0.routed_weight_codes[1]),
                ),
                group1,
                group2,
            ),
            "nonnegative",
        ),
        ((group0, group1), "each token/selected-slot pair exactly once"),
    )
    shared = (((_bf16(1), _bf16(2)), (_bf16(3), _bf16(4))),)
    routed = _routed_for_reduce()
    scalar_cases = (
        (replace(dispatch, batch_size=0), "dispatch.batch_size"),
        (replace(dispatch, sequence_length=True), "dispatch.sequence_length"),
        (replace(dispatch, hidden_width=0), "dispatch.hidden_width"),
        (replace(dispatch, expert_count=0), "dispatch.expert_count"),
        (replace(dispatch, top_k=0), "dispatch.top_k"),
        (replace(dispatch, expert_count=2), "must not exceed"),
    )
    with pytest.raises(DispatchReferenceError, match="ExpertDispatchResult"):
        reduce_expert_outputs_bf16(object(), routed, shared)
    for malformed, match in scalar_cases:
        with pytest.raises(DispatchReferenceError, match=match):
            reduce_expert_outputs_bf16(malformed, routed, shared)
    for malformed, match in malformed_groups:
        with pytest.raises(DispatchReferenceError, match=match):
            reduce_expert_outputs_bf16(
                replace(dispatch, groups=malformed), routed, shared
            )


def _require_governed_development_stack(torch, device: str) -> None:
    if str(torch.__version__) != "2.10.0+cu128":
        pytest.skip("development observation is pinned to PyTorch 2.10.0+cu128")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    if device == "cuda" and (
        torch.version.cuda != "12.8" or torch.cuda.get_device_capability() != (12, 0)
    ):
        pytest.skip("CUDA development observation is pinned to CUDA 12.8 and SM120")


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_source_duplicate_advanced_index_update_is_backend_dependent(
    device: str,
) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    _require_governed_development_stack(torch, device)
    output = torch.zeros(2, 1, dtype=torch.float32, device=device)
    token_indices = torch.tensor((0, 0, 1), dtype=torch.int64, device=device)
    contributions = (
        torch.tensor(
            ((_bf16(1),), (_bf16(2),), (_bf16(3),)),
            dtype=torch.uint16,
        )
        .view(torch.bfloat16)
        .to(device)
    )
    output[token_indices] += contributions
    observed = tuple(float(value) for value in output[:, 0].cpu().tolist())
    assert observed == ((2.0, 3.0) if device == "cpu" else (1.0, 3.0))


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_source_no_duplicate_reduction_matches_bounded_target_corpus(
    device: str,
) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    _require_governed_development_stack(torch, device)

    rng = random.Random(0x4558_5052_4544_5543)
    token_count = 16
    hidden_width = 128
    expert_count = 8
    top_k = 6
    indices = tuple(
        tuple(rng.sample(range(expert_count), top_k)) for _ in range(token_count)
    )
    dispatch = dispatch_routed_experts_bf16(
        (tuple((0,) * hidden_width for _ in range(token_count)),),
        indices,
        tuple(tuple(_f32(1) for _ in range(top_k)) for _ in range(token_count)),
        expert_count=expert_count,
        top_k=top_k,
    )

    def random_bf16() -> int:
        numerator = rng.randint(-255, 255)
        exponent = rng.randint(-12, 12)
        value = Fraction(numerator * (1 << max(exponent, 0)), 1 << max(-exponent, 0))
        return _bf16(value)

    routed = tuple(
        ExpertOutputGroup(
            group.expert_id,
            tuple(
                tuple(random_bf16() for _ in range(hidden_width))
                for _ in group.token_indices
            ),
        )
        for group in dispatch.groups
    )
    shared = (
        tuple(
            tuple(random_bf16() for _ in range(hidden_width))
            for _ in range(token_count)
        ),
    )
    target = reduce_expert_outputs_bf16(dispatch, routed, shared)

    native = torch.zeros(token_count, hidden_width, dtype=torch.float32, device=device)
    for dispatch_group, output_group in zip(dispatch.groups, routed, strict=True):
        token_indices = torch.tensor(
            dispatch_group.token_indices, dtype=torch.int64, device=device
        )
        contributions = (
            torch.tensor(output_group.output_bf16_rows, dtype=torch.uint16)
            .view(torch.bfloat16)
            .to(device)
        )
        native[token_indices] += contributions
    shared_tensor = (
        torch.tensor(shared, dtype=torch.uint16).view(torch.bfloat16).to(device)
    )
    native += shared_tensor[0]
    observed = tuple(
        tuple(int(code) for code in row)
        for row in native.to(torch.bfloat16).cpu().view(torch.uint16).tolist()
    )
    assert observed == target.output_bf16_codes[0]


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
