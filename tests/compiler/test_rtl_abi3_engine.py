"""RTL 3.0 engine datapaths: the arithmetic must agree with the device.

W8.6 correlated the control plane with every engine stubbed, and said so.
These tests bind the other half:

1. the engine RTL transcribes the frozen storage-format and opcode registries,
   and carries no wildcard package import -- the form that made one simulator
   silently disagree with the other and that the pinned synthesiser rejects
   outright;
2. the vector set is reproducible, and every expectation in it is the golden
   device's own counter or its own written bytes rather than a hand-written
   number; and
3. both simulators replay every vector through the datapaths and print the
   exact marker derived from that execution, having made the same number of
   comparisons.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import (  # noqa: E402
    DType,
    Dma,
    Major,
    Selection,
    Tensor,
    Vector,
)
from runtime.sim import formats as sim_formats  # noqa: E402
from tools import build_abi3_engine_vectors as generator  # noqa: E402
from tools import rtl_abi3_engine_campaign as campaign  # noqa: E402

VECTOR_DIR = ROOT / "testdata/compiler/abi3_engine"
VECTOR_JSON = VECTOR_DIR / "abi3_engine_vectors.json"
FORMAT_PACKAGE = ROOT / "rtl/abi3/ot_a3_format_pkg.sv"
ENGINE_PACKAGE = ROOT / "rtl/abi3/ot_a3_engine_pkg.sv"
CAMPAIGN_JSON = ROOT / "results/rtl/abi3_engine_campaign.json"

ENGINE_RTL = (
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_mac_lane.sv",
    "rtl/abi3/ot_a3_selection_argmax.sv",
    "rtl/abi3/ot_a3_dma_index_mover.sv",
    "rtl/abi3/ot_a3_vector_add.sv",
    "rtl/abi3/ot_a3_vector_convert.sv",
    "rtl/abi3/ot_a3_vector_scale.sv",
    "rtl/abi3/ot_a3_vector_hadamard.sv",
    "rtl/abi3/ot_a3_vector_index_score.sv",
    "rtl/abi3/ot_a3_vector_compress_project.sv",
    "rtl/abi3/ot_a3_vector_mhc_post.sv",
    "rtl/abi3/ot_a3_engine_array.sv",
)

TOOLS_AVAILABLE = all(
    shutil.which(tool) is not None for tool in ("iverilog", "vvp", "g++")
)


def _raw_vectors() -> dict:
    return json.loads(VECTOR_JSON.read_text(encoding="utf-8"))


def _vectors() -> dict:
    vectors = _raw_vectors()
    assert vectors.get("schema") == generator.VECTOR_SCHEMA, (
        "retained W8.3 vectors are stale; regenerate them from the current "
        "ABI 3.0 functional engine before using this evidence"
    )
    return vectors


# ---------------------------------------------------------------------------
# 1. registry transcription and source hygiene
# ---------------------------------------------------------------------------
def test_format_package_transcribes_the_storage_format_registry() -> None:
    text = FORMAT_PACKAGE.read_text(encoding="utf-8")
    for name in ("BF16", "FP32", "U8", "U32", "FP8_E4M3FN", "MXFP4_E2M1",
                 "E8M0_SCALE"):
        match = re.search(rf"FMT_{name}\s*=\s*8'h([0-9a-f]{{2}})", text)
        assert match, f"format package does not define FMT_{name}"
        assert int(match.group(1), 16) == int(getattr(DType, name)), name


def test_engine_package_transcribes_the_opcode_registry() -> None:
    text = ENGINE_PACKAGE.read_text(encoding="utf-8")
    families = {
        "FAMILY_DMA": Major.DMA,
        "FAMILY_TENSOR": Major.TENSOR,
        "FAMILY_VECTOR": Major.VECTOR,
        "FAMILY_SELECTION": Major.SELECTION,
    }
    subs = {
        "DMA_GATHER": Dma.GATHER,
        "DMA_SCATTER": Dma.SCATTER,
        "TENSOR_MATMUL": Tensor.MATMUL,
        "VECTOR_ADD": Vector.ADD,
        "VECTOR_CONVERT": Vector.CONVERT,
        "VECTOR_SCALE": Vector.SCALE,
        "VECTOR_COMPRESS": Vector.COMPRESS,
        "VECTOR_MHC": Vector.MHC,
        "VECTOR_HADAMARD": Vector.HADAMARD,
        "VECTOR_INDEX_SCORE": Vector.INDEX_SCORE,
        "SELECTION_ARGMAX": Selection.ARGMAX,
    }
    for name, value in {**families, **subs}.items():
        match = re.search(rf"{name}\s*=\s*8'h([0-9a-f]{{2}})", text)
        assert match, f"engine package does not define {name}"
        assert int(match.group(1), 16) == int(value), name


def test_engine_rtl_carries_no_wildcard_package_import() -> None:
    """The form that made two simulators disagree, pinned shut.

    Under Icarus 11 a wildcard-imported identifier that appears only inside a
    module-instance port-connection expression is not resolved against the
    import: an implicit one-bit net of that name is created instead, and it
    then shadows the constant for the whole module.  ``DMA_SCATTER`` read as z,
    every DMA.SCATTER dispatched as unimplemented, and ``DMA_GATHER`` -- which
    never appeared in a port connection -- kept working.  Verilator resolved it
    correctly, so the two simulators disagreed and only the two-simulator rule
    made that visible.  The same change is also what makes these blocks
    synthesisable: the pinned Yosys 0.68 Verilog frontend rejects ``import``
    in a module header and in a module body alike.
    """
    for path in ENGINE_RTL:
        text = (ROOT / path).read_text(encoding="utf-8")
        body = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("//")
        )
        assert "import " not in body, (
            f"{path} carries a package import; use pkg::name instead"
        )


# ---------------------------------------------------------------------------
# 2. the vector set is the device's own observation
# ---------------------------------------------------------------------------
def test_vector_set_is_reproducible(tmp_path: Path) -> None:
    assert generator.build(["--output", str(tmp_path)]) == 0
    rebuilt = json.loads((tmp_path / "abi3_engine_vectors.json").read_text())
    assert rebuilt == _vectors()


def test_no_engine_is_stubbed_in_the_golden_execution() -> None:
    vectors = _vectors()
    assert vectors["abi"] == {"major": 3, "minor": 0}
    assert "no engine is stubbed" in vectors["engine_policy"]
    # A case that produced nothing would make the byte comparison vacuous.
    assert vectors["result_word_count"] > 0
    assert vectors["mac_count"] > 0


def test_new_vector_opcode_pairs_are_present_in_the_generated_campaign() -> None:
    pairs = {
        (entry["family"], entry["sub"]) for entry in _vectors()["families"]
    }
    expected = {
        (int(Major.VECTOR), int(Vector.CONVERT)),
        (int(Major.VECTOR), int(Vector.SCALE)),
        (int(Major.VECTOR), int(Vector.HADAMARD)),
        (int(Major.VECTOR), int(Vector.INDEX_SCORE)),
        (int(Major.VECTOR), int(Vector.COMPRESS)),
        (int(Major.VECTOR), int(Vector.MHC)),
    }
    assert expected <= pairs


def test_vector_rtl_scope_is_exact_and_fail_closed() -> None:
    scope = _vectors()["vector_rtl_scope"]
    integrated = {entry["opcode"]: entry for entry in scope["newly_integrated"]}
    assert set(integrated) == {
        "CONVERT",
        "SCALE",
        "HADAMARD",
        "INDEX_SCORE",
        "COMPRESS",
        "MHC",
    }
    assert integrated["CONVERT"]["covered"] == "unscaled one-input/one-output form"
    assert integrated["SCALE"]["uncovered_forms"] == [
        "aux0 2 logistic sigmoid",
        "general trailing-axis factor broadcasting",
    ]
    assert integrated["COMPRESS"]["uncovered_forms"] == [
        "aux0 1 COMPRESS_POOL",
        "aux0 2 COMPRESS_STATE_UPDATE",
    ]
    assert integrated["MHC"]["uncovered_forms"] == [
        "aux0 0 HYPER_CONNECT_PRE",
        "aux0 2 HYPER_CONNECT_HEAD",
    ]
    deferred = {
        entry["opcode"] for entry in scope["wholly_deferred_transcendental"]
    }
    assert deferred == {"SILU_MUL", "SOFTMAX", "SQRT_SOFTPLUS"}
    assert scope["standalone_outside_engine_array"] == [
        "RMS_NORM",
        "HEAD_RMS_NORM",
        "ROPE",
    ]
    assert "no transcendental behavior is approximated" in scope[
        "unsupported_policy"
    ]


def test_every_new_vector_case_publishes_its_explicit_rtl_field_mapping() -> None:
    new_subs = {
        int(Vector.CONVERT),
        int(Vector.SCALE),
        int(Vector.HADAMARD),
        int(Vector.INDEX_SCORE),
        int(Vector.COMPRESS),
        int(Vector.MHC),
    }
    cases = [
        case
        for case in _vectors()["cases"]
        if case["family"] == int(Major.VECTOR) and case["sub"] in new_subs
    ]
    assert cases
    identity_dtypes = {
        int(DType.U8),
        int(DType.U32),
        int(DType.BF16),
        int(DType.FP32),
        int(DType.FP8_E4M3FN),
        int(DType.MXFP4_E2M1),
        int(DType.E8M0_SCALE),
    }
    for case in cases:
        config = case["rtl_config"]
        assert config["covered_form"], case["name"]
        assert config["record"]["cfg_count"] == case["count"], case["name"]
        if (
            case["sub"] == int(Vector.CONVERT)
            and case["operand0_dtype"] == case["output_dtype"]
        ):
            assert case["output_dtype"] in identity_dtypes, case["name"]
        else:
            assert case["output_dtype"] in (
                int(DType.BF16), int(DType.FP32)
            ), case["name"]
        if case["operand2_dtype"]:
            assert case["operand2_sha256"]
        if case["operand3_dtype"]:
            assert case["operand3_sha256"]


def test_new_vector_late_faults_leave_the_whole_destination_untouched() -> None:
    expected = {
        "vector_convert_late_nonfinite",
        "vector_scale_late_nonfinite",
        "vector_hadamard_late_nonfinite",
        "vector_index_score_late_nonfinite",
        "vector_compress_project_late_nonfinite",
        "vector_mhc_post_late_nonfinite",
    }
    cases = {case["name"]: case for case in _vectors()["cases"]}
    assert expected <= set(cases)
    for name in expected:
        case = cases[name]
        assert case["expected_fault_code"] == generator.ERR_OPERAND_NONFINITE
        assert case["expected_result_count"] == 0
        assert case["expected_word_count"] == case["count"]
        assert case["flags"] & generator.FLAG_EXPECT_UNTOUCHED


def test_every_expectation_comes_from_the_golden_counters() -> None:
    """No expectation in the record is a number this repository chose."""
    for case in _vectors()["cases"]:
        counters = case["golden_counters"]
        if case["expected_fault_code"] != 0:
            if case["expectation_source"] == "device_fault":
                assert case["golden_status"] != 0, case["name"]
            else:
                assert case["expectation_source"] in {
                    "rtl_bounded_profile",
                    "rtl_descriptor_admission",
                }, case["name"]
                assert case["golden_status"] == 0, case["name"]
                assert case["expected_fault_code"] == generator.ERR_SHAPE
            assert case["expected_result_count"] == 0, case["name"]
            continue
        assert case["golden_status"] == 0, case["name"]
        if case["family"] == int(Major.TENSOR):
            assert case["expected_result_count"] == counters["tensor.output_elements"]
            assert case["expected_saturations"] == counters.get("tensor.saturations", 0)
            assert case["expected_work"] == case["rows"] * case["cols"] * case["depth"]
        elif case["family"] == int(Major.VECTOR):
            assert case["expected_saturations"] == counters.get("vector.saturations", 0)
            assert case["expected_result_count"] == case["expected_word_count"]
            assert case["expected_work"] == counters["vector.elements"]
            if case["sub"] == int(Vector.INDEX_SCORE):
                assert case["expected_work"] > case["expected_result_count"]
        elif case["family"] == int(Major.SELECTION):
            assert case["expected_work"] == counters["selection.vocabulary_elements"]
            assert (
                case["expected_tie_multiplicity"]
                == counters["selection.tie_multiplicity"]
            )
        else:
            moved = counters.get(
                "dma.scatter_elements", counters.get("dma.gather_elements", 0)
            )
            assert case["expected_result_count"] == moved, case["name"]


def test_every_device_refusal_is_classified_from_the_message_it_raised() -> None:
    faults = [case for case in _vectors()["cases"] if case["expected_fault_code"]]
    assert len(faults) == _vectors()["fault_case_count"]
    for case in faults:
        if case["expectation_source"] != "device_fault":
            assert case["expectation_source"] in {
                "rtl_bounded_profile",
                "rtl_descriptor_admission",
            }, case["name"]
            assert case["golden_status"] == 0, case["name"]
            assert case["golden_message"] == "", case["name"]
            assert case["expected_fault_code"] == generator.ERR_SHAPE
            continue
        assert case["golden_message"], case["name"]
        assert generator.classify_fault(case["golden_message"]) == (
            case["expected_fault_code"]
        ), case["name"]
        # A refusal must publish a window to check for partial writes.
        assert case["expected_word_count"] > 0, case["name"]

    sources = {}
    for case in faults:
        source = case["expectation_source"]
        sources[source] = sources.get(source, 0) + 1
    assert sources == {
        "device_fault": 17,
        "rtl_bounded_profile": 18,
        "rtl_descriptor_admission": 57,
    }


def test_negative_cases_cover_every_fault_class_the_datapaths_raise() -> None:
    """Every fault code produced by the correlated datapaths has a case."""
    observed = {case["expected_fault_code"] for case in _vectors()["cases"]}
    required = {
        generator.ERR_OPERAND_NONFINITE,
        generator.ERR_PRODUCT_RANGE,
        generator.ERR_ACCUMULATE_RANGE,
        generator.ERR_INDEX_RANGE,
        generator.ERR_SELECT_NONFINITE,
        generator.ERR_SCALE_RANGE,
        generator.ERR_SHAPE,
    }
    assert required <= observed


def test_matmul_cases_cover_the_operand_pairs_the_models_ship() -> None:
    pairs = {
        (case["operand0_dtype"], case["operand1_dtype"])
        for case in _vectors()["cases"]
        if case["family"] == int(Major.TENSOR) and not case["expected_fault_code"]
    }
    assert (int(DType.BF16), int(DType.BF16)) in pairs
    assert (int(DType.FP8_E4M3FN), int(DType.FP8_E4M3FN)) in pairs
    assert (int(DType.MXFP4_E2M1), int(DType.FP8_E4M3FN)) in pairs
    # Amendment A15's two-dimensional scale block must appear, since an
    # A8-only reader addresses it wrongly and every shape still agrees.
    assert any(
        case["block_rows_b"] > 1
        for case in _vectors()["cases"]
        if case["family"] == int(Major.TENSOR)
    )


def _image(name: str) -> list[int]:
    return [int(line, 16) for line in (VECTOR_DIR / name).read_text().splitlines()]


def test_at_least_one_case_can_see_its_own_reduction_order() -> None:
    """The BF16 output rounding hides the ordering the contract is named for.

    Reordering a binary32 reduction perturbs the accumulator by about one part
    in 2**24; the output rounds to BF16, which resolves one part in 2**8.  On
    ordinary operands ascending-K and descending-K therefore produce the same
    BF16 code at every output -- a reversed lane replayed against the vector
    set passed until this was fixed, because 147 of 585 accumulators in
    ``matmul_bf16_tile_edge`` differ in binary32 and none differ after
    rounding.  At least one case must therefore be constructed so that its
    *output* distinguishes the order, or the campaign checks the products, the
    accumulation width and the rounding, and not the association.
    """
    import numpy as np

    vectors = _vectors()
    stride = vectors["geometry"]["case_stride"]
    m0 = _image("e3_m0.hex")
    m1 = _image("e3_m1.hex")
    records = _image("e3_case.hex")

    def reduce_codes(products: np.ndarray) -> int:
        previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
        try:
            total = np.float32(0.0)
            for value in products:
                total = np.float32(total + value)
        finally:
            np.seterr(**previous)
        codes, _ = sim_formats.narrow_bf16_rne(np.array([total], dtype=np.float32))
        return int(codes[0])

    distinguishing = []
    for index, case in enumerate(vectors["cases"]):
        if case["family"] != int(Major.TENSOR) or case["expected_fault_code"]:
            continue
        if case["operand0_dtype"] != int(DType.BF16):
            continue
        row = records[index * stride : (index + 1) * stride]
        rows, cols, depth, a_base, b_base = row[2], row[3], row[4], row[8], row[9]
        left = np.array(m0[a_base : a_base + rows * depth], dtype=np.uint32)
        right = np.array(m1[b_base : b_base + cols * depth], dtype=np.uint32)
        activations = sim_formats.widen_bf16(
            left.astype(np.uint16).reshape(rows, depth)
        )
        weights = sim_formats.widen_bf16(
            right.astype(np.uint16).reshape(cols, depth)
        )
        seen = False
        previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
        try:
            for r in range(rows):
                for c in range(cols):
                    products = np.multiply(
                        activations[r], weights[c], dtype=np.float32
                    )
                    products[products == 0] = np.float32(0.0)
                    if reduce_codes(products) != reduce_codes(products[::-1]):
                        seen = True
                        break
                if seen:
                    break
        finally:
            np.seterr(**previous)
        if seen:
            distinguishing.append(case["name"])
    assert distinguishing, (
        "no BF16 contraction case distinguishes ascending-K from descending-K, "
        "so the campaign does not check the reduction order the contract fixes"
    )
    assert "matmul_bf16_reduction_order" in distinguishing


def test_a_case_sits_on_each_side_of_the_reference_schedule_switch() -> None:
    """Both schedules of the sequential contraction must be exercised.

    ``runtime.sim.backend`` computes the same contract two ways and switches on
    output-tile size alone.  The contract says they agree bit for bit; a vector
    set entirely on one side of the switch would never check that against the
    other, and the threshold could move without anything noticing.
    """
    from runtime.sim.backend import (
        SEQUENTIAL_KMAJOR_COL_TILE,
        SEQUENTIAL_KMAJOR_MIN_TILE,
    )

    below = above = False
    for case in _vectors()["cases"]:
        if case["family"] != int(Major.TENSOR) or case["expected_fault_code"]:
            continue
        if case["operand0_dtype"] == int(DType.BF16) and case[
            "operand1_dtype"
        ] == int(DType.BF16):
            continue          # the BF16 path uses the frozen kernel, not this
        tile = case["rows"] * min(case["cols"], SEQUENTIAL_KMAJOR_COL_TILE)
        if tile >= SEQUENTIAL_KMAJOR_MIN_TILE:
            above = True
        else:
            below = True
    assert below and above, (
        "the vector set must reach both the K-last and the K-major schedule of "
        "runtime.sim.backend.sequential_matmul_binary32"
    )


def test_scatter_cases_start_from_a_destination_that_is_not_zero() -> None:
    """A zero destination would let a scatter that never read it back pass."""
    scatters = [
        case for case in _vectors()["cases"]
        if case["family"] == int(Major.DMA)
        and case["sub"] == int(Dma.SCATTER)
        and not case["expected_fault_code"]
    ]
    assert scatters
    for case in scatters:
        # The destination window is larger than the scattered payload, so the
        # surviving prior rows are part of what is compared.
        assert case["expected_word_count"] > case["expected_result_count"]


def test_decode_probe_is_exhaustive_over_the_block_formats() -> None:
    probe = generator.decode_probe_entries()
    for dtype, count, table in (
        (DType.FP8_E4M3FN, 256, sim_formats.E4M3FN_VALUES),
        (DType.MXFP4_E2M1, 16, sim_formats.MXFP4_VALUES),
        (DType.E8M0_SCALE, 256, sim_formats.E8M0_VALUES),
    ):
        codes = {word for fmt, word, _, _ in probe if fmt == int(dtype)}
        assert codes == set(range(count)), dtype.name
        assert len(table) == count
    assert len(probe) == _vectors()["decode_probe_count"]


def test_descriptor_admission_carries_the_complete_numeric_profile(
    tmp_path: Path,
) -> None:
    """The adapter must not silently drop NUMERIC descriptor controls."""
    cases = {
        case.name: case
        for case in generator.build_cases(generator.engine_capability(), tmp_path)
    }
    baseline, metadata = generator.descriptor_admission(
        cases["vector_scale_constant_eighth"]
    )
    assert len(baseline) == generator.CASE_STRIDE - 32 == 48
    assert baseline[6] == (
        int(DType.BF16)
        | (int(DType.BF16) << 8)
        | (int(DType.BF16) << 16)
        | (int(DType.FP32) << 24)
    )
    assert baseline[7] == 1 << 16  # profile-valid; every control is zero
    assert baseline[46:] == [0, 0]  # epsilon and flags
    assert metadata["profile_accumulator_dtype"] == int(DType.FP32)

    corruptions = {
        "vector_descriptor_refusal_scale_profile_accumulator_mismatch": (
            6, 0x10101010
        ),
        "vector_descriptor_refusal_scale_profile_saturate": (7, 3 << 16),
        "vector_descriptor_refusal_scale_profile_nan_policy": (
            7, (1 << 24) | (1 << 16)
        ),
        "vector_descriptor_refusal_scale_profile_epsilon": (46, 1),
        "vector_descriptor_refusal_scale_profile_flags": (47, 1),
    }
    for name, (word, expected) in corruptions.items():
        case = cases[name]
        encoded, _ = generator.descriptor_admission(case)
        assert encoded[word] == expected, name
        assert case.rtl_expected_fault_code == generator.ERR_SHAPE


def test_arithmetic_probe_reaches_the_corners_the_engine_cases_do_not() -> None:
    """The engine cases alone would not exercise the interesting values.

    Real operands are normals of moderate exponent, mostly of one magnitude,
    which is the distribution under which a rounding or normalisation defect is
    least likely to show.  The probe must therefore reach signed zero, both
    smallest subnormals, the largest subnormal, the smallest normal, the
    largest finite and the nonfinite band, and its authority must be the exact
    Fraction reference rather than host floating point.
    """
    entries = generator.arith_probe_entries()
    assert len(entries) == _vectors()["arith_probe_count"]
    operands = {a for a, *_ in entries} | {b for _, b, *_ in entries}
    for required in (
        0x00000000, 0x80000000,          # signed zero
        0x00000001, 0x80000001,          # smallest subnormals
        0x007FFFFF | 0x80000000,         # largest subnormal
        0x00800000,                      # smallest normal
        0x7F7FFFFF, 0xFF7FFFFF,          # largest finite, both signs
    ):
        assert required in operands, hex(required)
    # The refusal path is reached, not merely available.
    assert any(add_err == 1 for _, _, add_err, *_ in entries)
    # And so is finite overflow, which is a different refusal: entry[2] is the
    # add's fault code and entry[4] the multiply's.
    assert any(entry[2] == 2 for entry in entries)
    assert any(entry[4] == 2 for entry in entries)
    assert "fractions.Fraction" in _vectors()["arith_reference"]
    assert "runtime.reference.formats" in _vectors()["arith_reference"]


@pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("iverilog", "vvp")),
    reason="Icarus and vvp are required",
)
def test_exact_product_add_primitive_against_fraction_reference(
    tmp_path: Path,
) -> None:
    """Broad finite-domain differential for the ordered-dot primitive."""
    entries = generator.product_add_probe_entries()
    assert len(entries) >= 5000
    inputs = {(acc, lhs, rhs) for acc, lhs, rhs, _, _ in entries}
    assert (0x0131C000, 0x8483, 0x35F2) in inputs
    assert (0x02BE8000, 0x1B83, 0x1A83) in inputs
    assert set(generator.PRODUCT_ADD_TIES) <= inputs
    assert all(((acc >> 23) & 0xFF) != 0xFF for acc, *_ in entries)
    assert all(((lhs >> 7) & 0xFF) != 0xFF for _, lhs, *_ in entries)
    assert all(((rhs >> 7) & 0xFF) != 0xFF for _, _, rhs, *_ in entries)
    assert any(error == 2 for *_, error, _ in entries), "finite overflow absent"
    # Both signed-zero inputs and exact opposite-sign cancellation must return
    # the canonical positive-zero encoding.
    for case in (
        (0x00000000, 0x0000, 0x3F80),
        (0x80000000, 0x8000, 0xBF80),
        (0x3F800000, 0xBF80, 0x3F80),
        (0xBF800000, 0x3F80, 0x3F80),
    ):
        matching = [entry for entry in entries if entry[:3] == case]
        assert matching and matching[0][3:] == (0, 0), tuple(map(hex, case))

    words = [len(entries)]
    for accumulator, lhs, rhs, error, result in entries:
        words.extend((accumulator, lhs | (rhs << 16), error, result))
    image = tmp_path / "product_add.hex"
    image.write_text("".join(f"{word:08x}\n" for word in words), encoding="ascii")
    executable = tmp_path / "product_add.vvp"
    compiled = subprocess.run(
        [
            shutil.which("iverilog") or "iverilog",
            "-g2012",
            "-s",
            "tb_a3_product_add",
            "-o",
            str(executable),
            str(ROOT / "rtl/ot_fp32_rne_pkg.sv"),
            str(ROOT / "rtl/test/tb_a3_product_add.sv"),
        ],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=120,
    )
    assert compiled.returncode == 0, compiled.stdout
    replayed = subprocess.run(
        [shutil.which("vvp") or "vvp", str(executable)],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=300,
    )
    assert replayed.returncode == 0, replayed.stdout
    assert (
        f"PASS exact product-add differential cases={len(entries)}"
        in replayed.stdout
    )


def test_only_the_sequential_contraction_contract_is_correlated() -> None:
    """The blocked contract is out of scope, and must stay out of the claim.

    Its association is the executing implementation's declared one, so
    "bit-exact against it" is not a well-posed statement about a different
    implementation.  The vector set therefore declares the sequential contract
    everywhere, and the campaign says so rather than leaving a reader to infer
    that every contraction the models use has been correlated.
    """
    reference = _vectors()["numeric_reference"]
    assert "sequential" in reference["bf16_bf16_fp32_sequential_rne_v1"]
    assert not any("blocked" in value for value in reference.values())


# ---------------------------------------------------------------------------
# 3. two-simulator replay
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not TOOLS_AVAILABLE, reason="Icarus, vvp and a C++ compiler are required"
)
def test_campaign_replays_both_simulators(tmp_path: Path) -> None:
    vectors = _vectors()
    summary = campaign.run(tmp_path / "build")
    assert summary["status"] == "pass", summary["cases"]
    assert [case["name"] for case in summary["cases"]] == ["iverilog", "verilator"]
    marker = vectors["required_marker"]
    for case in summary["cases"]:
        assert case["status"] == "pass"
        assert case["compile_returncode"] == 0
        assert case["run_returncode"] == 0
        assert case["marker_present"], case["run_log"]
        assert marker in case["run_log"]
        assert case["checks"] and case["checks"] > 0
        assert "/tmp/" not in case["compile_command"]
    # Two checkers that print the same marker after a different number of
    # comparisons are not two checks of the same thing.
    counts = {case["checks"] for case in summary["cases"]}
    assert len(counts) == 1, summary["checks_per_simulator"]
    assert "Verilator 5.05" in summary["tools"]["verilator"]["version"]
    assert "version 11.0" in summary["tools"]["iverilog"]["version"]
    assert summary["correlation"]["result_word_count"] > 0
    assert summary["correlation"]["mac_count"] > 0
    assert summary["correlation"]["fault_case_count"] > 0
    sensitivity = summary["mutation_sensitivity"]
    assert sensitivity["mutation_count"] == len(campaign.MUTATIONS)
    assert sensitivity["all_caught_by_both_simulators"]
    assert {item["id"] for item in sensitivity["mutations"]} == {
        item["id"] for item in campaign.MUTATIONS
    }
    for mutation in sensitivity["mutations"]:
        assert mutation["caught_by_both"], mutation["id"]
        assert mutation["exact_replacement"]["before"]
        assert mutation["exact_replacement"]["after"]
        for simulator in mutation["simulators"]:
            assert simulator["compile_returncode"] == 0
            assert simulator["run_returncode"] != 0
            assert not simulator["marker_present"]
            assert simulator["first_mismatch"].startswith("FAIL:")


def test_campaign_refuses_to_overwrite_an_existing_artifact(tmp_path: Path) -> None:
    target = tmp_path / "abi3_engine_campaign.json"
    target.write_text("{}\n", encoding="utf-8")
    assert campaign.main(["--output", str(target)]) == 2
    assert target.read_text(encoding="utf-8") == "{}\n"


@pytest.mark.skipif(
    not CAMPAIGN_JSON.exists(), reason="no retained campaign artifact"
)
def test_retained_campaign_artifact_is_bound_to_these_sources() -> None:
    vectors = _vectors()
    retained = json.loads(CAMPAIGN_JSON.read_text(encoding="utf-8"))
    assert retained["status"] == "pass"
    assert retained["required_marker"] == vectors["required_marker"]
    assert len(set(retained["checks_per_simulator"].values())) == 1
    assert retained["mutation_sensitivity"]["all_caught_by_both_simulators"]
    assert CAMPAIGN_JSON.read_bytes() == (
        json.dumps(retained, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    for path, digest in retained["source_sha256"].items():
        actual = campaign.sha256_file(ROOT / path)
        assert actual == digest, f"{path} changed since the campaign was recorded"


def test_retained_campaign_states_what_it_does_not_establish() -> None:
    retained = json.loads(CAMPAIGN_JSON.read_text(encoding="utf-8"))
    boundary = retained["claim_boundary"]["does_not_establish"]
    for key in (
        "blocked_contraction_contract",
        "exhaustive_arithmetic",
        "fault_position",
        "throughput_or_latency",
        "other_engine_families",
        "integration_with_the_control_plane",
        "memory_macros",
        "physical_realisability",
    ):
        assert key in boundary and boundary[key], key
