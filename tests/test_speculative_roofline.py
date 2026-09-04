"""The speculative layer must be additive, exact at the identity, and repeatable.

Five things are pinned here, and they are the five ways this layer could be
wrong without anyone noticing:

1. **It reduces to the published figure.** At ``gamma = 0`` with no drafter, one
   speculative cycle is one ordinary decode step, and ``tau = 1`` accepted token
   per cycle is one token per step. If that identity does not hold to the digit,
   every speculative number is measured from the wrong baseline.
2. **``tau`` is clamped to ``[1, gamma+1]``.** DFlash equation (1) defines ``tau``
   as accepted tokens per cycle INCLUDING the bonus token, so a block of
   ``gamma`` proposals can never yield more than ``gamma+1``. An acceptance
   length published at one block size must not be silently reused at a smaller
   one.
3. **A profile that cannot support its own grade is refused.** Every parameter
   carries a value, a grade and a source, and the grades are the ones
   ``configs/hardware/technology.json`` defines and no others.
4. **Two runs are byte-identical.** An artifact that changes without its inputs
   changing cannot be used as evidence.
5. **The roofline artifacts it reads are unchanged.** This layer is additive or
   it is nothing.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "run_speculative_roofline.py"
PROFILES = ROOT / "configs" / "studies" / "speculative_profiles.json"
TECHNOLOGY = ROOT / "configs" / "hardware" / "technology.json"
#: The smallest committed roofline artifact, used wherever one study is enough.
#: It carries only Qwen3-8B, which is dense, so the rules that exist because a
#: model is a mixture of experts cannot be exercised on it.
SAMPLE = ROOT / "results" / "roofline" / "quantised_variant" / "n5_vs_b200" / "analytical.json"
#: The smallest committed artifact carrying a fine-grained MoE target, for the
#: expert-union and per-region rules, which are the identity on a dense model.
MOE_SAMPLE = ROOT / "results" / "roofline" / "context_ladder" / "n6_vs_a100" / "pro-32k" / "analytical.json"


def _load_tool():
    spec = importlib.util.spec_from_file_location("run_speculative_roofline", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The tool defines dataclasses, and ``dataclasses`` resolves annotations
    # through ``sys.modules[cls.__module__]``, so the module must be registered
    # before it is executed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


@pytest.fixture(scope="module")
def config():
    return json.loads(PROFILES.read_text())


def _load_sample(tool, path):
    from opentallas.schema import ModelProfile
    from opentallas.workload import kv_traffic

    body = json.loads(path.read_text())
    technology = tool.Technology.load(TECHNOLOGY)
    models = {
        name: ModelProfile.load(ROOT / entry["path"]) for name, entry in body["inputs"]["models"].items()
    }
    designs = {design["name"]: design for design in body["designs"]}
    balance = body["technology_derivations"]["efficiencies"]["stage_balance"]["value"]
    kv = {
        (name, int(entry["context_tokens"])): kv_traffic(models[name], int(entry["context_tokens"]))
        for name, entry in body["inputs"]["models"].items()
    }
    return {
        "body": body,
        "technology": technology,
        "models": models,
        "designs": designs,
        "balance": balance,
        "kv": kv,
    }


@pytest.fixture(scope="module")
def sample(tool):
    return _load_sample(tool, SAMPLE)


@pytest.fixture(scope="module")
def moe_sample(tool):
    return _load_sample(tool, MOE_SAMPLE)


def _feasible(sample):
    return [point for point in sample["body"]["points"] if point["feasible"]]


def _decompose(tool, sample, point):
    model = sample["models"][point["model"]]
    kv = sample["kv"][(point["model"], int(point["context_tokens"]))]
    return tool.decompose(
        point,
        sample["designs"][point["design"]],
        model,
        sample["technology"],
        kv,
        sample["balance"],
    )


# --------------------------------------------------------------------------
# 1. the identity, and the reduction to the published figure
# --------------------------------------------------------------------------


def test_every_feasible_point_reconstructs_from_its_own_published_terms(tool, sample):
    problems = []
    for point in _feasible(sample):
        _, issues = _decompose(tool, sample, point)
        problems.extend(issues)
    assert problems == [], problems[:5]


def test_at_gamma_zero_with_no_drafter_the_cycle_is_the_published_step(tool, sample):
    points = _feasible(sample)
    assert points
    for point in points:
        base, issues = _decompose(tool, sample, point)
        assert issues == []
        cycle = tool.speculative_cycle(
            point,
            sample["designs"][point["design"]],
            sample["models"][point["model"]],
            sample["technology"],
            base,
            None,
            0,
            "in_rom" if point["weight_store"] == "rom" else "in_hbm",
            0.0,
        )
        assert cycle["cycle_s"] == pytest.approx(point["step_time_s"], rel=1e-12)
        assert cycle["tau_break"] == pytest.approx(1.0, rel=1e-12)
        # tau = 1 accepted token per cycle is exactly the autoregressive rate.
        assert 1.0 / cycle["cycle_s"] == pytest.approx(point["per_user_tokens_s"], rel=1e-12)
        assert cycle["cycle_thermal_scale"] == pytest.approx(point["thermal_scale"], rel=1e-9)


def test_the_verification_pass_charges_exactly_n_positions_of_compute(tool, sample):
    checked = 0
    for point in _feasible(sample):
        if point["weight_store"] == "rom" and point["weight_amortization"] in tool.COMPUTE_IN_ROM_POLICIES:
            continue  # the multiply IS the sweep; there is no separate compute term
        base, _ = _decompose(tool, sample, point)
        for gamma in (1, 3, 7):
            cycle = tool.speculative_cycle(
                point,
                sample["designs"][point["design"]],
                sample["models"][point["model"]],
                sample["technology"],
                base,
                None,
                gamma,
                "in_rom" if point["weight_store"] == "rom" else "in_hbm",
                0.0,
            )
            assert cycle["verify_compute_s"] == pytest.approx(base.compute_s * (gamma + 1), rel=1e-12)
        checked += 1
    assert checked > 0


def test_one_rom_sweep_serves_the_whole_block_on_a_batched_array(tool, sample):
    checked = 0
    for point in _feasible(sample):
        if point["weight_store"] != "rom" or point["weight_amortization"] != "batched":
            continue
        base, _ = _decompose(tool, sample, point)
        for gamma in (1, 4, 15):
            cycle = tool.speculative_cycle(
                point,
                sample["designs"][point["design"]],
                sample["models"][point["model"]],
                sample["technology"],
                base,
                None,
                gamma,
                "in_rom",
                0.0,
            )
            assert cycle["weight_ratio_verify"] == pytest.approx(1.0, rel=1e-12)
        checked += 1
    assert checked > 0


def _drafter(tool, model, *, block_passes=1.0, sequential=0.0, already=True, dense=None, routed=None, stored=0.0, layers=1):
    """A drafter constructed for a specific invariant, not for a real profile."""

    return tool.Drafter(
        profile="test",
        model=model.name,
        layers=layers,
        dense_bytes=model.dense_weight_bytes if dense is None else dense,
        routed_bytes=model.routed_weight_bytes if routed is None else routed,
        stored_bytes=stored,
        already_in_checkpoint=already,
        block_passes=block_passes,
        sequential_passes_per_draft_token=sequential,
        grade="assumed",
        source="constructed by tests/test_speculative_roofline.py",
        note="",
    )


def test_a_draft_pass_on_a_batched_rom_array_costs_exactly_one_full_sweep(tool, sample):
    """The locality rule, pinned including the token_slots factor.

    One draft pass through the array takes the full-array sweep time, which is
    exactly what one target pass takes on a `batched` design -- and both are on
    one user's critical path, so both carry `token_slots`. Dropping that factor
    understates the draft pass by the pipeline depth, which on a 30-device
    hybrid machine is four.
    """

    checked = 0
    for point in _feasible(sample):
        if point["weight_store"] != "rom" or point["weight_amortization"] != "batched":
            continue
        base, _ = _decompose(tool, sample, point)
        model = sample["models"][point["model"]]
        cycle = tool.speculative_cycle(
            point,
            sample["designs"][point["design"]],
            model,
            sample["technology"],
            base,
            _drafter(tool, model),
            7,
            "in_rom",
            0.0,
        )
        assert cycle["draft_weight_s"] == pytest.approx(base.weight_s, rel=1e-12)
        checked += 1
        if checked >= 40:
            break
    assert checked > 0


def test_each_sequential_draft_application_costs_one_more_full_sweep(tool, sample):
    checked = 0
    for point in _feasible(sample):
        if point["weight_store"] != "rom" or point["weight_amortization"] != "batched":
            continue
        base, _ = _decompose(tool, sample, point)
        model = sample["models"][point["model"]]
        gamma = 7
        without = tool.speculative_cycle(
            point, sample["designs"][point["design"]], model, sample["technology"], base,
            _drafter(tool, model, sequential=0.0), gamma, "in_rom", 0.0,
        )
        with_bias = tool.speculative_cycle(
            point, sample["designs"][point["design"]], model, sample["technology"], base,
            _drafter(tool, model, sequential=1.0), gamma, "in_rom", 0.0,
        )
        assert with_bias["draft_weight_s"] == pytest.approx(
            without["draft_weight_s"] * (1 + gamma), rel=1e-12
        )
        checked += 1
        if checked >= 20:
            break
    assert checked > 0


def test_a_drafter_the_size_of_the_target_costs_the_target_pass_on_hbm(tool, sample):
    checked = 0
    for point in _feasible(sample):
        if point["weight_store"] == "rom":
            continue
        base, _ = _decompose(tool, sample, point)
        model = sample["models"][point["model"]]
        cycle = tool.speculative_cycle(
            point,
            sample["designs"][point["design"]],
            model,
            sample["technology"],
            base,
            _drafter(tool, model),
            7,
            "in_hbm",
            0.0,
        )
        # One draft pass over the whole target's weights is exactly the
        # verification pass's own weight term, token_slots included.
        assert cycle["draft_weight_s"] == pytest.approx(cycle["verify_weight_s"], rel=1e-12)
        checked += 1
        if checked >= 40:
            break
    assert checked > 0


def test_the_rom_versus_gpu_ratio_under_speculation_carries_no_tau(tool, sample):
    """Two acceptance rates, one ratio: tau is a model property and cancels."""

    points = {point["family"]: point for point in _feasible(sample) if point["batch_size"] == 1}
    assert "rom" in points and "gpu" in points
    cycles = {}
    for family, point in points.items():
        base, _ = _decompose(tool, sample, point)
        cycles[family] = tool.speculative_cycle(
            point,
            sample["designs"][point["design"]],
            sample["models"][point["model"]],
            sample["technology"],
            base,
            None,
            7,
            "in_rom" if family == "rom" else "in_hbm",
            0.0,
        )["cycle_s"]
    ratios = [
        (tau / cycles["rom"]) / (tau / cycles["gpu"])
        for tau in (1.5, 6.49)
    ]
    assert ratios[0] == pytest.approx(ratios[1], rel=1e-12)
    assert ratios[0] == pytest.approx(cycles["gpu"] / cycles["rom"], rel=1e-12)


def _cycle(tool, sample, point, base, gamma, placement, drafter=None, share=0.0):
    return tool.speculative_cycle(
        point,
        sample["designs"][point["design"]],
        sample["models"][point["model"]],
        sample["technology"],
        base,
        drafter,
        gamma,
        placement,
        share,
    )


def _pick(sample, predicate, limit):
    chosen = [point for point in _feasible(sample) if predicate(point)]
    return chosen[:limit]


# --------------------------------------------------------------------------
# 1b. every scaling rule the report publishes, pinned exactly
#
# The eight rows of the report's own scaling table are eight independent
# claims. Five of them used to be unguarded, and a mutation campaign showed
# each could be broken without a single test failing while thousands of
# published break-even values moved by factors from 0.125x to 8x. Every rule
# now has an assertion at gamma >= 1, which is where each one stops being the
# identity.
# --------------------------------------------------------------------------


def test_the_verification_pass_reads_the_context_once_and_only_the_writes_multiply(tool, sample):
    """`K_v = K * (read + n*write)/(read + write)`.

    The block shares one prefix, so a wider block does NOT re-read the context.
    Charging the read per position instead is invisible at gamma 0 and moves
    thousands of break-even values at every gamma above it.
    """

    checked = 0
    for point in _pick(sample, lambda p: True, 60):
        base, _ = _decompose(tool, sample, point)
        total = base.kv_read_bytes + base.kv_write_bytes
        if total <= 0 or base.kv_s <= 0:
            continue
        for gamma in (1, 5, 16):
            n = gamma + 1
            expected = base.kv_s * (base.kv_read_bytes + n * base.kv_write_bytes) / total
            cycle = _cycle(tool, sample, point, base, gamma, _placement(point))
            assert cycle["verify_kv_s"] == pytest.approx(expected, rel=1e-12)
            assert cycle["kv_ratio_verify"] == pytest.approx(expected / base.kv_s, rel=1e-12)
        checked += 1
    assert checked > 0


def test_only_the_payload_half_of_a_link_event_scales_with_positions(tool, sample):
    """`L_v = lat + xfer * n`, with the latency half recovered independently.

    The latency half is a per-cycle cost and the payload half is a per-position
    one. The split is pinned two ways: the closed form, and the increment from
    one gamma to the next, which must be exactly one payload and never a
    latency.
    """

    checked = 0
    for point in _pick(sample, lambda p: True, 60):
        base, _ = _decompose(tool, sample, point)
        if base.link_s <= 0:
            continue
        # The whole link term at gamma 0 is one event: latency plus one payload.
        assert base.link_latency_only_s + base.link_transfer_s == pytest.approx(base.link_s, rel=1e-12)
        assert _cycle(tool, sample, point, base, 0, _placement(point))["verify_link_s"] == pytest.approx(
            base.link_s, rel=1e-12
        )
        previous = None
        for gamma in (1, 2, 3, 7, 16):
            n = gamma + 1
            cycle = _cycle(tool, sample, point, base, gamma, _placement(point))
            assert cycle["verify_link_s"] == pytest.approx(
                base.link_latency_only_s + base.link_transfer_s * n, rel=1e-12
            )
            if previous is not None and gamma == 3:
                # gamma 2 -> 3 is exactly one more payload, and no more latency.
                assert cycle["verify_link_s"] - previous == pytest.approx(base.link_transfer_s, rel=1e-9)
            previous = cycle["verify_link_s"]
        checked += 1
    assert checked > 0


def test_the_per_layer_floor_is_paid_once_however_many_positions_ride_it(tool, sample):
    """`F_v = F` exactly, at every gamma. One traversal of the layers."""

    checked = 0
    for point in _pick(sample, lambda p: True, 60):
        base, _ = _decompose(tool, sample, point)
        if base.fixed_s <= 0:
            continue
        for gamma in (0, 1, 5, 16):
            cycle = _cycle(tool, sample, point, base, gamma, _placement(point))
            assert cycle["verify_fixed_s"] == pytest.approx(base.fixed_s, rel=1e-12)
        checked += 1
    assert checked > 0


def test_a_compute_in_rom_verification_pass_costs_one_sweep_per_position(tool, sample):
    """`W_v = W * n` on a `per_stream` design: the multiply IS the sweep."""

    checked = 0
    for point in _pick(
        sample, lambda p: p["weight_store"] == "rom" and p["weight_amortization"] == "per_stream", 40
    ):
        base, _ = _decompose(tool, sample, point)
        for gamma in (1, 4, 15):
            cycle = _cycle(tool, sample, point, base, gamma, "in_rom")
            assert cycle["weight_ratio_verify"] == pytest.approx(float(gamma + 1), rel=1e-12)
            assert cycle["verify_weight_s"] == pytest.approx(base.weight_s * (gamma + 1), rel=1e-12)
        checked += 1
    assert checked > 0


def test_a_per_region_verification_pass_costs_the_busiest_region_its_widened_load(tool, moe_sample):
    """`W_v = W * R(mb*n)/R(mb)`, with `R` taken from the roofline itself.

    `R` is recomputed here through `opentallas.roofline.expected_max_region_load`
    rather than through the tool's own helper, so the assertion pins the rule
    and not the implementation. It must also be strictly greater than one: a
    wider block puts more of itself on the busiest region.
    """

    from opentallas.roofline import expected_max_region_load

    imbalance = moe_sample["technology"].efficiency("expert_router_imbalance").value

    def region_passes(model, draws):
        passes = expected_max_region_load(max(1, model.num_experts), draws, max(1, model.experts_per_token))
        passes *= max(imbalance, 1e-9)
        return min(max(1.0, passes), float(draws))

    checked = 0
    for point in _pick(
        moe_sample, lambda p: p["weight_store"] == "rom" and p["weight_amortization"] == "per_region", 40
    ):
        base, _ = _decompose(tool, moe_sample, point)
        model = moe_sample["models"][point["model"]]
        if model.num_experts <= 1:
            continue
        for gamma in (1, 4, 15):
            expected = region_passes(model, base.microbatch * (gamma + 1)) / region_passes(model, base.microbatch)
            cycle = _cycle(tool, moe_sample, point, base, gamma, "in_rom")
            assert cycle["weight_ratio_verify"] == pytest.approx(expected, rel=1e-12)
            assert cycle["weight_ratio_verify"] > 1.0
        checked += 1
    assert checked > 0


def test_a_bandwidth_machine_pays_the_expert_union_widening(tool, moe_sample):
    """`W_v = W * t(mb*n)/t(mb)` on HBM, and the ratio is strictly above one.

    This is the mechanism behind the headline that a GPU comparator pays for a
    wider block where a batched ROM array does not. Regressing it to invariance
    is worth more than a factor of two on some published break-evens, so the
    sign is pinned as well as the value.
    """

    checked = 0
    for point in _pick(moe_sample, lambda p: p["weight_store"] != "rom", 40):
        base, _ = _decompose(tool, moe_sample, point)
        model = moe_sample["models"][point["model"]]
        design = moe_sample["designs"][point["design"]]
        if model.routed_weight_bytes <= 0:
            continue
        for gamma in (1, 7, 15):
            kwargs = dict(
                scale=base.scale,
                num_experts=model.num_experts,
                experts_per_token=model.experts_per_token,
                peak_bytes_s=float(design["weight_read_bytes_s"]),
                devices=int(point["device_count"]),
            )
            block = tool._hbm_weight_time(
                model.dense_weight_bytes, model.routed_weight_bytes, draws=base.microbatch * (gamma + 1), **kwargs
            )
            single = tool._hbm_weight_time(
                model.dense_weight_bytes, model.routed_weight_bytes, draws=base.microbatch, **kwargs
            )
            cycle = _cycle(tool, moe_sample, point, base, gamma, "in_hbm")
            assert cycle["weight_ratio_verify"] == pytest.approx(block / single, rel=1e-12)
            assert cycle["weight_ratio_verify"] > 1.0
        checked += 1
    assert checked > 0


def test_a_drafter_held_off_the_array_is_charged_one_bandwidth_read(tool, sample):
    """The `in_kv_store` drafter never pays the ROM fabric's sweep count.

    Its read is served by the KV store's bandwidth, so it is one read of
    `dense + routed * coverage(mb*n)` for the whole block. Multiplying it by the
    array sweep count -- 16x at a block of 16 on a `per_stream` design -- would
    charge a fabric cost to a transfer that never enters the fabric, and it used
    to be a third of one study's `cannot pay at any acceptance rate` verdicts.
    """

    checked = 0
    for point in _pick(
        sample,
        lambda p: p["weight_store"] == "rom" and p["weight_amortization"] in tool.COMPUTE_IN_ROM_POLICIES,
        40,
    ):
        base, _ = _decompose(tool, sample, point)
        model = sample["models"][point["model"]]
        design = sample["designs"][point["design"]]
        gamma = 15
        drafter = _drafter(tool, model, block_passes=1.0)
        cycle = _cycle(tool, sample, point, base, gamma, "in_kv_store", drafter=drafter)
        draws = base.microbatch * (gamma + 1)
        coverage = (
            tool._coverage(model.num_experts, model.experts_per_token, draws)
            if model.routed_weight_bytes > 0
            else 0.0
        )
        one_read = base.scale * (model.dense_weight_bytes + model.routed_weight_bytes * coverage)
        expected = one_read / float(design["kv_read_bytes_s"]) * base.slots
        assert cycle["draft_weight_s"] == pytest.approx(expected, rel=1e-12)
        # And it does not move when the array's sweep count does: the same
        # drafter on a batched design would be charged the same bytes.
        assert cycle["draft_weight_s"] == pytest.approx(
            tool._engaged_bytes(
                model.dense_weight_bytes,
                model.routed_weight_bytes,
                amortization="batched",
                weight_store="hbm",
                draws=draws,
                scale=base.scale,
                num_experts=model.num_experts,
                experts_per_token=model.experts_per_token,
                imbalance=1.0,
            )
            / float(design["kv_read_bytes_s"])
            * base.slots,
            rel=1e-12,
        )
        checked += 1
    assert checked > 0


def _placement(point):
    return "in_rom" if point["weight_store"] == "rom" else "in_hbm"


# --------------------------------------------------------------------------
# 2. the clamp DFlash equation (1) requires
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tau, gamma, expected, clamped",
    [
        (7.87, 3, 4.0, True),   # a block-16 acceptance reused at block 4
        (7.87, 15, 7.87, False),
        (0.5, 3, 1.0, True),    # never below one: the target's bonus token always lands
        (5.0, 4, 5.0, False),   # exactly at the cap of a block-4 budget
        (5.0, 5, 5.0, False),   # DSpark's paper block: gamma 5, cap 6, not a clamp
        (5.0, 7, 5.0, False),   # DSpark's served block: gamma 7, cap 8, not a clamp
        (16.0, 16, 16.0, False),  # DFlash block 16: gamma 16, cap 17
        (5.0, 3, 4.0, True),
    ],
)
def test_tau_is_clamped_to_the_dflash_interval(tool, tau, gamma, expected, clamped):
    value, was_clamped = tool._clamp_tau(tau, gamma)
    assert value == pytest.approx(expected)
    assert was_clamped is clamped
    assert 1.0 <= value <= gamma + 1


def test_every_published_acceptance_length_respects_its_own_cap(config):
    for name, profile in config["profiles"].items():
        acceptance = profile["acceptance_length"]
        key = profile["served_gamma_parameter"]
        # gamma IS the block size on both sources' own definition; there is no
        # block_size - 1 anywhere in either paper.
        gamma = int(profile["parameters"][key]["value"])
        assert acceptance["range_high"] <= gamma + 1, (
            f"{name}: a published acceptance of {acceptance['range_high']} exceeds the "
            f"gamma+1 = {gamma + 1} cap at the served block size"
        )
        assert acceptance["includes_bonus_token"] is True


def test_gamma_is_the_block_size_each_source_defines(tool, sample, config):
    """No `block_size - 1` anywhere: the sources define gamma as the block.

    DFlash: "the block size IS the speculation budget ... with block size 16
    (gamma=16), the acceptance length ranges from 1 to 17". DSpark: "gamma input
    tokens (anchor + gamma-1 masks) yield gamma draft logits". Deriving gamma as
    block_size - 1 verifies one position short and publishes a cap one too low.
    """

    expected = {"released_dspark": 7, "sota_block_diffusion": 16}
    for name, want in expected.items():
        profile = config["profiles"][name]
        key = profile["served_gamma_parameter"]
        assert int(profile["parameters"][key]["value"]) == want
        study = tool.process_study(
            SAMPLE, name, profile, sample["technology"], [int(v) for v in config["gamma_ladder"]], False
        )
        assert study["served_gamma"] == want
        for row in study["points"]:
            for variant in row["variants"].values():
                served = variant["served"]["low"]
                assert served["gamma"] == want
                assert served["positions_per_verify"] == want + 1
                assert served["tau_cap"] == float(want + 1)
    # The ladder must contain the block sizes the sources actually configure,
    # and every one of those must be a parameter the profile names rather than
    # a number inferred from prose.
    ladder = set(int(value) for value in config["gamma_ladder"])
    assert {5, 7, 8, 16} <= ladder
    for name, profile in config["profiles"].items():
        named = profile["block_size_parameters"]
        assert named, name
        for key in named:
            value = int(profile["parameters"][key]["value"])
            assert value in ladder, f"{name}: block size {value} from {key} is off the ladder"
        assert profile["served_gamma_parameter"] in named


def test_the_xiaomi_cross_check_quotes_a_cycle_from_xiaomis_own_block_size(tool, sample, config):
    """A block-8 acceptance length may never be applied to a block-16 cycle.

    The sample study carries no Pro-scale GPU point, so the model label on its
    GPU rows is rewritten here to exercise the selection. What is asserted is
    the function's own rule: the cycle it publishes comes from `cross_check`,
    which is evaluated at `mimo_block_size`, and never from `served`, which is
    evaluated at this profile's own block of 16.
    """

    profile = config["profiles"]["sota_block_diffusion"]
    study = tool.process_study(
        SAMPLE, "sota_block_diffusion", profile, sample["technology"],
        [int(value) for value in config["gamma_ladder"]], False,
    )
    mimo = int(profile["parameters"][profile["cross_check_gamma_parameter"]]["value"])
    assert study["cross_check_gamma"] == mimo
    assert study["served_gamma"] != mimo
    for row in study["points"]:
        if row["family"] != "rom":
            row["model"] = "DeepSeek-V4-Pro-0813"
    check = tool.xiaomi_cross_check([study], profile, config)
    assert check is not None and check["rows"]
    assert check["block_size"] == mimo
    assert check["positions_per_verify"] == mimo + 1
    lookup = {
        (row["design"], row["batch_size"], row["context_tokens"]): row
        for row in study["points"]
    }
    for entry in check["rows"]:
        assert entry["gamma"] == mimo
        source = lookup[(entry["design"], entry["batch_size"], entry["context_tokens"])]
        cross = source["variants"]["in_hbm"]["cross_check"]
        served = source["variants"]["in_hbm"]["served"]
        assert cross["low"]["gamma"] == mimo
        assert entry["tau_break_draft_kv_low"] == pytest.approx(cross["low"]["tau_break"], rel=1e-12)
        assert entry["tau_break_draft_kv_low"] != pytest.approx(served["low"]["tau_break"], rel=1e-12)
        for workload, values in entry["speculative_by_workload"].items():
            assert values["per_user_tokens_s_draft_kv_low"] == pytest.approx(
                values["tau"] / cross["low"]["cycle_s"], rel=1e-12
            ), workload
    # And the acceptance lengths it applies are the ones published at that block.
    assert int(profile["external_acceptance_cross_check"]["block_size"]) == mimo


def test_the_xiaomi_active_parameter_count_is_graded_assumed(config):
    """The blog states 1T total and no active count, so it cannot be `published`.

    `configs/hardware/technology.json` defines `published` as stated by the
    vendor for a shipping part. A number the vendor does not state is `assumed`,
    and it must say so where a reader meets it.
    """

    entry = config["cross_checks"]["xiaomi_mimo_ultraspeed"]["active_parameters"]
    assert entry["grade"] == "assumed"
    assert "assumed" in entry["note"].lower()
    assert "does not state" in entry["source"].lower() or "no primary source" in entry["source"].lower()


def test_every_acceptance_length_names_a_page_a_reader_can_open(config):
    """A source string with no URL and no arXiv id cannot be checked by anyone."""

    for name, profile in config["profiles"].items():
        source = profile["acceptance_length"]["source"]
        assert "http" in source or "arXiv:" in source, f"{name}: {source}"
        measured = profile["acceptance_length"]["measured_on"]
        assert set(measured) >= {"model", "batch_size", "hardware", "workload_mix"}


def test_the_markov_bias_rank_matches_the_committed_tensor_shapes(config):
    """Two rank-256 tables, not one rank-512 one: the byte total cannot tell them apart."""

    rank = config["profiles"]["released_dspark"]["parameters"]["markov_bias_rank"]
    assert rank["value"] == 256
    external = config["profiles"]["released_dspark"]["external_draft_traffic_decomposition"]
    vocabulary = 129280
    assert 2 * vocabulary * rank["value"] * 2 == external["bytes_per_draft_token"]


# --------------------------------------------------------------------------
# 3. a profile that cannot support its own grade is refused
# --------------------------------------------------------------------------


def test_a_parameter_without_a_source_is_refused(tool, config):
    broken = json.loads(json.dumps(config))
    profile = broken["profiles"]["sota_block_diffusion"]
    del profile["parameters"]["draft_layers"]["source"]
    with pytest.raises(SystemExit, match="carries no source"):
        tool.build_payload(
            "sota_block_diffusion", broken, tool.Technology.load(TECHNOLOGY), [SAMPLE], verify_shas=False
        )


def test_a_grade_outside_the_defined_vocabulary_is_refused(tool, config):
    broken = json.loads(json.dumps(config))
    broken["profiles"]["sota_block_diffusion"]["parameters"]["draft_layers"]["grade"] = "reported"
    with pytest.raises(SystemExit, match="not one of the grades"):
        tool.build_payload(
            "sota_block_diffusion", broken, tool.Technology.load(TECHNOLOGY), [SAMPLE], verify_shas=False
        )


def test_an_acceptance_length_without_a_grade_is_refused(tool, config):
    broken = json.loads(json.dumps(config))
    del broken["profiles"]["released_dspark"]["acceptance_length"]["grade"]
    with pytest.raises(SystemExit, match="acceptance_length carries no grade"):
        tool.build_payload(
            "released_dspark", broken, tool.Technology.load(TECHNOLOGY), [SAMPLE], verify_shas=False
        )


def test_the_committed_profiles_use_only_the_grades_technology_json_defines(config):
    defined = set(json.loads(TECHNOLOGY.read_text())["grade_definitions"])

    def walk(node):
        if isinstance(node, dict):
            if "grade" in node:
                assert node["grade"] in defined, node["grade"]
                assert "source" in node or "evidence" in node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(config)


def test_the_tool_refuses_to_write_into_the_roofline_trees(tool):
    with pytest.raises(SystemExit, match="refusing to write"):
        tool._guard_output(ROOT / "results" / "roofline" / "n5_vs_b200" / "analytical.json")
    with pytest.raises(SystemExit, match="refusing to write"):
        tool._guard_output(ROOT / "results" / "roofline")
    # Its own tree, and anywhere outside the repository, are allowed.
    tool._guard_output(ROOT / "results" / "roofline" / "speculative" / "x" / "analytical.json")
    tool._guard_output(Path("/tmp") / "somewhere" / "analytical.json")


def test_the_tool_does_not_reach_into_the_study_driver():
    source = TOOL.read_text()
    assert "run_roofline_studies" not in source.replace(
        "never imports the study driver", ""
    ).replace('"tools/run_roofline_studies.py"', "").replace(
        "``tools/run_roofline_studies.py``", ""
    )
    assert "evaluate(" not in source


# --------------------------------------------------------------------------
# 4 and 5. repeatable, and additive
# --------------------------------------------------------------------------


def _digests(paths):
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    }


def _run(tool, output_root):
    argv = sys.argv
    sys.argv = [
        "run_speculative_roofline.py",
        "--study",
        "quantised_variant",
        "--output-root",
        str(output_root),
        "--force",
    ]
    try:
        assert tool.main() == 0
    finally:
        sys.argv = argv


def test_two_runs_are_byte_identical_and_leave_the_roofline_artifacts_alone(tool, tmp_path):
    sources = [
        path
        for path in sorted((ROOT / "results" / "roofline").rglob("analytical.json"))
        if "speculative" not in path.parts
    ]
    assert sources
    before = _digests(sources)

    first = tmp_path / "first"
    second = tmp_path / "second"
    _run(tool, first)
    _run(tool, second)

    after = _digests(sources)
    assert before == after, "the speculative layer modified a roofline artifact"

    produced = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
    assert produced, "no artifact was written"
    for relative in produced:
        left = (first / relative).read_bytes()
        right = (second / relative).read_bytes()
        assert left == right, f"{relative} is not byte-identical across two runs"


def test_the_written_artifact_states_its_pins_and_its_gate(tool, tmp_path):
    _run(tool, tmp_path)
    body = json.loads((tmp_path / "sota_block_diffusion" / "analytical.json").read_text())
    assert body["inputs"]["technology_sha256"] == hashlib.sha256(TECHNOLOGY.read_bytes()).hexdigest()
    assert body["inputs"]["profile_config_sha256"] == hashlib.sha256(PROFILES.read_bytes()).hexdigest()
    assert body["inputs"]["input_pins_verified"] is True
    assert body["produced_by"]["writes_only_under"] == "results/roofline/speculative"
    for study in body["studies"]:
        assert study["reconstruction_gate"]["failures"] == 0
        assert study["reconstruction_gate"]["feasible_points_checked"] > 0
        for row in study["points"]:
            for variant in row["variants"].values():
                assert variant["tau_break_draft_kv_low"] is None or variant["tau_break_draft_kv_low"] > 0
                assert variant["tau_break_draft_kv_high"] >= variant["tau_break_draft_kv_low"]


def test_a_stale_technology_pin_stops_the_run(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "_sha256", lambda path: "0" * 64)
    with pytest.raises(SystemExit, match="Refusing to mix"):
        tool.process_study(
            SAMPLE,
            "sota_block_diffusion",
            json.loads(PROFILES.read_text())["profiles"]["sota_block_diffusion"],
            tool.Technology.load(TECHNOLOGY),
            [1, 2, 3],
            True,
        )
