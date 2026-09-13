"""The V4.1 FP4 main-KV dequantize block: reference, RTL shape and evidence.

Four things are checked here, and a failure of any of them means the retained
campaign is no longer evidence:

* the reference in ``runtime/reference/fp4_kv.py`` computes the contract
  ``fp4_e2m1_s16_e4m3_to_fp8_v1`` exactly, agrees with a third implementation
  (PyTorch's own FP8 cast) everywhere the contract and that cast both define a
  result, and fails closed on a poisoned scale or a partial group;
* the three-party IR addition the block serves is present;
* the RTL holds NO model geometry: the scale group is an operand field, the
  lane count and extent bound are parameters, and no dimension of the V4.1
  model appears as a localparam;
* the retained dual-simulator campaign still binds the sources on disk, still
  reports agreement, and still measures an initiation interval of one.

Absence of the artifact is a failure here, not "not evaluable".
"""

from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.fp4_kv import (  # noqa: E402
    CONTRACT,
    DEFAULT_SCALE_GROUP,
    FP4KVReferenceError,
    dequantize_element_to_fp8,
    dequantize_to_fp8,
    element_value,
    finite_scale_codes,
    prove_binary32_intermediate_is_exact,
    quantize_to_fp4,
    scale_code_is_nonfinite,
    scale_value,
)
from tools import run_a3_v41_fp4kv_rtl_campaign as campaign_tool  # noqa: E402
from tools.build_a3_v41_fp4kv_vectors import VECTOR_FILES, build  # noqa: E402

RTL = ROOT / "rtl/abi3/ot_a3_vector_fp4kv_dequant.sv"
TESTBENCH = ROOT / "rtl/test/tb_a3_v41_fp4kv_dequant.sv"
VECTOR_DIR = ROOT / "testdata/rtl/a3_v41_fp4kv"
ARTIFACT = ROOT / "results/rtl/a3_v41_fp4kv_dequant_campaign.json"


@pytest.fixture(scope="module")
def artifact() -> dict:
    if not ARTIFACT.is_file():
        pytest.fail(f"{ARTIFACT.relative_to(ROOT)} is missing")
    return json.loads(ARTIFACT.read_text())


# --------------------------------------------------------------------------
# the reference
# --------------------------------------------------------------------------


def test_every_product_is_exact_so_the_contract_is_one_rounding() -> None:
    assert prove_binary32_intermediate_is_exact() == 16 * len(finite_scale_codes())


@pytest.mark.parametrize(
    ("code", "scale", "expected", "why"),
    (
        (0x1, 0x3C, 0x34, "0.5 x 1.5 = 0.75 = 12 x 2**-4"),
        (0x2, 0x3C, 0x3C, "1.0 x 1.5 is the scale itself"),
        (0x9, 0x3C, 0xB4, "the sign is the XOR of both operand signs"),
        (0x1, 0x01, 0x00, "2**-10 is half the smallest subnormal: tie to even"),
        (0x3, 0x01, 0x02, "3 x 2**-10 ties up to the even significand"),
        (0x7, 0x7E, 0x7E, "6 x 448 clamps to the finite endpoint"),
        (0xF, 0x7E, 0xFE, "and clamps with its sign"),
        (0x0, 0x7E, 0x00, "a zero element is zero at any scale"),
        (0x7, 0x00, 0x00, "a zero scale is zero for any element"),
        (0x8, 0x3C, 0x00, "E2M1 negative zero decodes to canonical +0"),
        (0x2, 0x80, 0x00, "E4M3FN negative zero likewise"),
    ),
)
def test_hand_derived_elements(code: int, scale: int, expected: int, why: str) -> None:
    result, saturated = dequantize_element_to_fp8(code, scale)
    assert result == expected, why
    product = element_value(code) * scale_value(scale)
    assert saturated == (abs(product) > 448), why


def test_saturation_is_a_property_of_the_exact_product() -> None:
    # 3 x 160 = 480 rounds back down to 448, and is still a saturation: the
    # repository's encode_e4m3fn_rne reports the range violation, not the
    # rounded outcome.
    scale = next(
        code
        for code in finite_scale_codes()
        if scale_value(code) == Fraction(160)
    )
    result, saturated = dequantize_element_to_fp8(0x5, scale)  # 3 x 160
    assert (result, saturated) == (0x7E, True)


def test_torch_agrees_wherever_both_define_a_result() -> None:
    torch = pytest.importorskip("torch")
    values: list[float] = []
    expected: list[int] = []
    for code in range(16):
        for scale in finite_scale_codes():
            product = element_value(code) * scale_value(scale)
            if abs(product) > 448:
                continue
            values.append(float(product))
            expected.append(dequantize_element_to_fp8(code, scale)[0])
    observed = (
        torch.tensor(values, dtype=torch.float64)
        .to(torch.float8_e4m3fn)
        .view(torch.uint8)
        .tolist()
    )
    differences = [
        (value, wanted, got)
        for value, wanted, got in zip(values, expected, observed)
        if wanted != got and not (wanted == 0 and got in (0x00, 0x80))
    ]
    assert differences == []
    assert len(values) == 3812


def test_a_nan_scale_poisons_its_group() -> None:
    assert scale_code_is_nonfinite(0x7F)
    assert scale_code_is_nonfinite(0xFF)
    assert not scale_code_is_nonfinite(0x7E)
    with pytest.raises(FP4KVReferenceError):
        dequantize_to_fp8([1] * 16, [0x7F], group=16)


def test_a_partial_group_has_no_defined_scale() -> None:
    with pytest.raises(FP4KVReferenceError):
        dequantize_to_fp8([1] * 24, [0x3C, 0x3C], group=16)
    with pytest.raises(FP4KVReferenceError):
        dequantize_to_fp8([1] * 32, [0x3C], group=16)


def test_the_group_is_an_argument_not_a_constant() -> None:
    codes = list(range(16)) * 4
    for group in (8, 12, 16, 32, 64):
        if len(codes) % group:
            continue
        scales = [0x3C] * (len(codes) // group)
        result = dequantize_to_fp8(codes, scales, group=group)
        assert len(result.fp8_codes) == len(codes)
        assert result.group == group
    assert DEFAULT_SCALE_GROUP == 16


def test_the_passthrough_operand_is_a_byte_copy() -> None:
    result = dequantize_to_fp8([], [], group=16, passthrough=[0x7F, 0xFF, 0x00, 0x12])
    assert result.fp8_codes == (0x7F, 0xFF, 0x00, 0x12)
    assert result.passthrough_count == 4


def test_the_representative_quantizer_round_trips_within_a_step() -> None:
    values = [Fraction(index - 8, 3) for index in range(16)]
    quantized = quantize_to_fp4(values, group=16)
    assert len(quantized.e2m1_codes) == 16
    assert len(quantized.e4m3_scale_codes) == 1
    scale = scale_value(quantized.e4m3_scale_codes[0])
    for value, code in zip(values, quantized.e2m1_codes):
        assert abs(element_value(code) * scale - value) <= scale


# --------------------------------------------------------------------------
# the three-party IR addition this block serves
# --------------------------------------------------------------------------


def test_the_dtype_and_kind_reach_one_engine_sub_opcode() -> None:
    from compiler.ir.v3.kernel_ir import DTYPES, OPERATION_KINDS
    from compiler.ir.v3.lowering import KERNEL_TO_ENGINE
    from runtime.abi3.constants import Major, Vector

    assert "fp4_e2m1_s16_e4m3" in DTYPES
    assert "mxfp4_e2m1" in DTYPES, "the MXFP4 dtype must stay distinct"
    assert "DEQUANTIZE" in OPERATION_KINDS
    lowered = KERNEL_TO_ENGINE["DEQUANTIZE"]
    assert (lowered.family, lowered.sub) == (Major.VECTOR, Vector.CONVERT)
    assert lowered.inputs == 3, "slot three is the passthrough operand"


def test_the_rtl_names_the_contract_and_its_source() -> None:
    text = RTL.read_text()
    assert CONTRACT in text
    assert "SRC-DSV41-FLASH-MODEL" in text
    assert "runtime/reference/fp4_kv.py" in text
    assert "mxfp4" in text.lower(), "the block must say what it is NOT"


# --------------------------------------------------------------------------
# no frozen model geometry
# --------------------------------------------------------------------------


def _operator_module(text: str) -> str:
    start = text.index("module ot_a3_vector_fp4kv_dequant")
    return text[start:]


def test_every_geometry_knob_is_a_parameter_or_an_operand_field() -> None:
    module = _operator_module(RTL.read_text())
    header = module[: module.index(");")]
    for name in ("LANES", "SCALE_GROUP_DEFAULT", "MAX_ELEMENTS"):
        assert re.search(rf"parameter integer {name}\s*=", header), name
    # The scale group is a RUNTIME field, so a group the datapath can compute is
    # never refused for want of re-elaboration.
    assert "input  wire [31:0]             cfg_group" in module
    assert "cfg_count" in module and "cfg_passthrough" in module


def test_no_model_dimension_is_frozen_into_the_rtl() -> None:
    text = RTL.read_text()
    frozen = [
        line.strip()
        for line in text.splitlines()
        if re.match(r"\s*localparam", line)
        and re.search(r"\b(512|1024|128|40|384)\b", line)
    ]
    assert frozen == [], f"a model dimension reached a localparam: {frozen}"
    # head_dim, the V4.1 latent width, may be NAMED in the header's explanation
    # of what is deliberately absent, but must never reach a declaration.
    declarations = [
        line
        for line in text.splitlines()
        if not line.strip().startswith("//")
        and re.search(r"\b(head_dim|512)\b", line)
    ]
    assert declarations == [], f"a model dimension reached the datapath: {declarations}"


def test_the_testbench_elaborates_more_than_one_lane_count() -> None:
    text = TESTBENCH.read_text()
    lanes = sorted({int(value) for value in re.findall(r"\.LANES\((\d+)\)", text)})
    assert lanes == [1, 4, 8]


# --------------------------------------------------------------------------
# the retained evidence
# --------------------------------------------------------------------------


def test_the_checked_in_vectors_are_source_current(tmp_path: Path) -> None:
    generated = tmp_path / "vectors"
    build(generated)
    drifted = [
        name
        for name in VECTOR_FILES
        if (generated / name).read_bytes() != (VECTOR_DIR / name).read_bytes()
    ]
    assert drifted == []


def test_the_retained_campaign_binds_its_sources_and_passed() -> None:
    assert campaign_tool.validate_retained() == []


def test_the_campaign_measured_an_initiation_interval_of_one(artifact: dict) -> None:
    assert artifact["status"] == "pass"
    assert artifact["simulators_agree"] is True
    assert artifact["pipeline"]["initiation_interval"] == 1
    assert artifact["pipeline"]["registered_stages"] == 7
    assert artifact["pipeline"]["measured_worst_case_stall_cycles"] == 0
    for lanes, row in artifact["per_lane_count"].items():
        assert row["worst_case_stall_cycles"] == 0, lanes
        assert row["legal_cases"] > 0, lanes
        assert row["refused_cases"] > 0, lanes


def test_the_campaign_covers_the_whole_pair_space_and_both_simulators(
    artifact: dict,
) -> None:
    assert artifact["coverage"]["exhaustive_pair_space_is_complete"] is True
    assert artifact["coverage"]["exhaustive_element_scale_pairs"] == 16 * 254
    tools = artifact["tools"]
    assert "5.050" in tools["verilator"]["version"]
    assert "Icarus" in tools["iverilog"]["version"]
    assert artifact["synthesis_frontend"]["dividers_or_modulo"] == 0
    assert artifact["synthesis_frontend"]["multiplier_cells"] == 1


def test_the_campaign_states_what_it_does_not_establish(artifact: dict) -> None:
    boundary = artifact["claim_boundary"]
    for key in (
        "establishes_asap7_or_sky130_frequency",
        "establishes_area_or_power",
        "is_placed_or_routed",
        "integrates_the_shipped_engine_array",
        "executes_an_abi3_descriptor_or_program",
        "establishes_a_model_token_or_tpot",
        "establishes_the_vendor_forward_quantizer_scale_selection",
        "reads_the_pinned_vendor_inference_model_py",
        "covers_a_partial_final_scale_group",
    ):
        assert boundary[key] is False, key
    assert len(artifact["not_established"]) >= 4
