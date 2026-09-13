"""``ot_a3_vector_rope`` retires a span of positions, and decode is unchanged.

A VECTOR.ROPE launch used to be one position, because nothing in the qualified
``ot_ta_rope_bf16_sram_engine`` iterates positions: its coefficient row is loaded
once per command and on the last coefficient index falls through to the input
stage.  The golden device reports the SAME 83 launches for prefill as for decode,
each covering a span of 16 positions, so that refusal is what stands between the
reduced program and a token value the reference oracle can check.

A span of two or more now runs on ``ot_a3_rope_lane_pipe`` -- six registered
stages, one element per cycle, the same six ``ot_fp32_rne_pkg`` calls in the same
order as the qualified core.  A span of exactly one still runs on the unchanged
core, which is why the decode path is bit-identical by construction here rather
than by argument.  The two claims this file makes by measurement are that the
lane agrees with the qualified core word for word at span 1, and that it agrees
with an independent Python oracle at every span and geometry it admits.
"""

from __future__ import annotations

import random
import re
import shutil
import struct
import subprocess

import pytest

from pathlib import Path

from runtime.reference.formats import binary32_bits_to_bf16_rne
from runtime.reference.tensor_accelerator_rope import rope_bf16

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The pinned Verilator, not the 4.038 that may be on PATH.  The second
#: simulator is the point: a span that only one simulator agrees with the oracle
#: on is a simulator artefact, not a datapath.
PINNED_VERILATOR = (
    Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
)

SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_rope_lane_pipe.sv",
    "rtl/ot_ta_command_decoder.sv",
    "rtl/ot_ta_rope_bf16_sram_engine.sv",
    "rtl/abi3/ot_a3_vector_rope.sv",
    "rtl/test/tb_a3_rope_span.sv",
)

#: The shipped Qwen3-8B RoPE geometry, and a reduced one.  Both are positive
#: controls: the point of the span work is that neither is frozen.
SHIPPED = dict(QUERY_HEADS=32, KEY_HEADS=8, HEAD_WIDTH=128)
REDUCED = dict(QUERY_HEADS=8, KEY_HEADS=4, HEAD_WIDTH=16)

needs_iverilog = pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="iverilog/vvp not available",
)


needs_pinned_verilator = pytest.mark.skipif(
    not PINNED_VERILATOR.is_file(),
    reason="pinned verilator 5.050 not installed",
)


def _fp32(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _build(work: Path, **params: int) -> Path:
    key = "_".join(f"{name}{value}" for name, value in sorted(params.items()))
    binary = (work / f"rope_{key}.vvp").resolve()
    if binary.exists():
        return binary
    command = ["iverilog", "-g2012", "-s", "tb_a3_rope_span"]
    for name, value in params.items():
        command.append(f"-Ptb_a3_rope_span.{name}={value}")
    command += ["-o", str(binary), *SOURCES]
    built = subprocess.run(
        command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=900
    )
    assert built.returncode == 0, built.stderr
    return binary


def _hex_words(text: str) -> list[int]:
    words: list[int] = []
    for line in text.splitlines():
        line = line.strip()
        if re.fullmatch(r"[0-9a-fA-F]{1,8}", line):
            words.append(int(line, 16))
    return words


def _operands(rows: int, cols: int, span: int, seed: int):
    """Position-major BF16 operand blocks and FP32 coefficient rows."""

    rng = random.Random(seed)
    # Ordinary magnitudes: the subject is the span and the geometry, not
    # saturation, which the engine reports separately.
    codes = [
        (_fp32(rng.uniform(-2.0, 2.0)) >> 16) & 0xFFFF
        for _ in range(rows * cols * span)
    ]
    coefficients = [_fp32(rng.uniform(-1.0, 1.0)) for _ in range(2 * cols * span)]
    return codes, coefficients


def _write(work: Path, codes: list[int], coefficients: list[int]) -> None:
    (work / "rope_in.hex").write_text("".join(f"{c:08x}\n" for c in codes))
    (work / "rope_coef.hex").write_text(
        "".join(f"{c:08x}\n" for c in coefficients)
    )


def _run(binary: Path, work: Path, rows: int, span: int, *extra: str,
         runner: tuple[str, ...] = ("vvp",)):
    """Run one case.  A Verilator --binary executable takes no interpreter."""

    executed = subprocess.run(
        [*runner, str(binary), f"+rows={rows}", f"+span={span}", *extra],
        cwd=work,
        capture_output=True,
        text=True,
        timeout=7200,
    )
    assert executed.returncode == 0, executed.stdout + executed.stderr
    # Verilator prints its own $finish line after the bench's; take the
    # bench's report wherever it lands.
    reports = [
        line for line in executed.stdout.splitlines() if line.startswith("ROPE")
    ]
    assert reports, executed.stdout + executed.stderr
    report = reports[-1]
    fields = {
        name: int(value, 16 if name == "canary" else 10)
        for name, value in re.findall(r"(\w+)=([0-9a-f]+)", report)
    }
    words: list[int] = []
    if fields["err"] == 0:
        words = [w & 0xFFFF for w in _hex_words((work / "rope_out.hex").read_text())]
    return report, fields, words


def _reference(codes, coefficients, rows: int, cols: int, span: int) -> list[int]:
    """Rotate each position against ITS OWN coefficient row, independently."""

    expected: list[int] = []
    block = rows * cols
    for position in range(span):
        cosine, sine = [], []
        for column in range(cols):
            base = position * 2 * cols
            cosine.append(
                binary32_bits_to_bf16_rne(coefficients[base + column]).code
            )
            sine.append(
                binary32_bits_to_bf16_rne(coefficients[base + cols + column]).code
            )
        heads = [
            codes[position * block + head * cols:position * block + (head + 1) * cols]
            for head in range(rows)
        ]
        # The oracle rotates a query and a key matrix against one row; a
        # VECTOR.ROPE launch declares one operand, so the second is a stub.
        result = rope_bf16(heads, heads[:1], cosine, sine)
        for row in result.query_values:
            expected.extend(row)
    return expected


def _case(work, binary, geometry, rows, span, seed):
    cols = geometry["HEAD_WIDTH"]
    codes, coefficients = _operands(rows, cols, span, seed)
    _write(work, codes, coefficients)
    report, fields, words = _run(binary, work, rows, span)
    assert fields["err"] == 0, report
    assert fields["results"] == fields["writes"] == rows * cols * span, report
    # Nothing was written past the declared count.
    assert fields["canary"] == 0xDEADBEEF, report
    expected = _reference(codes, coefficients, rows, cols, span)
    assert len(words) == len(expected), report
    assert words == expected, (
        f"{geometry} rows={rows} span={span}: first mismatch at "
        f"{next(i for i, (a, b) in enumerate(zip(words, expected)) if a != b)}"
    )
    return report, fields, words


@needs_iverilog
@pytest.mark.parametrize("geometry", (REDUCED, SHIPPED), ids=("reduced", "shipped"))
def test_span_one_runs_on_the_qualified_core_and_is_bit_exact(geometry, tmp_path):
    """The decode path: the unchanged core, both declared operands."""

    binary = _build(tmp_path, **geometry, MAX_POSITION_SPAN=65536)
    for rows in (geometry["QUERY_HEADS"], geometry["KEY_HEADS"]):
        report, _, _ = _case(tmp_path, binary, geometry, rows, 1, 0x5150 + rows)
        print(report)


@needs_iverilog
@pytest.mark.parametrize("geometry", (REDUCED, SHIPPED), ids=("reduced", "shipped"))
def test_the_pipelined_lane_matches_the_qualified_core_at_span_one(
    geometry, tmp_path
):
    """The lane's arithmetic is the core's, measured on the same operands.

    This is what licenses routing a span to the lane at all: LANE_AT_SPAN1
    sends a one-position launch down the pipelined path, and the output image
    must be identical word for word to the qualified core's on the identical
    operand stream.
    """

    core = _build(tmp_path, **geometry, MAX_POSITION_SPAN=65536, LANE_AT_SPAN1=0)
    lane = _build(tmp_path, **geometry, MAX_POSITION_SPAN=65536, LANE_AT_SPAN1=1)
    cols = geometry["HEAD_WIDTH"]
    for rows in (geometry["QUERY_HEADS"], geometry["KEY_HEADS"]):
        codes, coefficients = _operands(rows, cols, 1, 0x9E11 + rows)
        _write(tmp_path, codes, coefficients)
        core_report, core_fields, core_words = _run(core, tmp_path, rows, 1)
        lane_report, lane_fields, lane_words = _run(lane, tmp_path, rows, 1)
        assert core_fields["err"] == lane_fields["err"] == 0
        assert core_words == lane_words, f"{core_report}\n{lane_report}"
        assert core_words == _reference(codes, coefficients, rows, cols, 1)
        # The lane is also the faster of the two by construction; reported so a
        # regression in the pipelining shows up as a number, not a feeling.
        print(f"core {core_report}")
        print(f"lane {lane_report}")
        assert lane_fields["cycles"] < core_fields["cycles"]


@needs_iverilog
def test_prefill_span_is_bit_exact_at_the_reduced_geometry(tmp_path):
    binary = _build(tmp_path, **REDUCED, MAX_POSITION_SPAN=256)
    for rows in (REDUCED["QUERY_HEADS"], REDUCED["KEY_HEADS"]):
        for span in (2, 3, 16):
            report, _, _ = _case(
                tmp_path, binary, REDUCED, rows, span, 0x2000 + span * 8 + rows
            )
            print(report)


@needs_iverilog
def test_prefill_span_is_bit_exact_at_the_shipped_geometry(tmp_path):
    """The case that matters: a 16-token prefill of the shipped Qwen geometry."""

    binary = _build(tmp_path, **SHIPPED, MAX_POSITION_SPAN=65536)
    for rows in (SHIPPED["QUERY_HEADS"], SHIPPED["KEY_HEADS"]):
        report, fields, _ = _case(
            tmp_path, binary, SHIPPED, rows, 16, 0xA5A5 + rows
        )
        print(report)
        # One element per cycle in steady state, plus a prologue of one
        # coefficient row and an epilogue of the last validated block.
        assert fields["cycles"] < fields["count"] * 11 // 10, report


@needs_iverilog
def test_the_span_retires_one_element_per_cycle(tmp_path):
    """The initiation interval, measured as the span amortises the epilogue.

    A launch costs one coefficient row of prologue and one output block of
    epilogue -- the last position's block is written only after it validates --
    so cycles/element approaches 1 from above as the span grows.  No serial or
    four-cycles-per-element engine can come near this, whatever the span.

    The second half is the output-buffer trade, stated as a measurement rather
    than a comment: with two blocks the drain runs one pipeline depth behind the
    compute and costs three cycles per position, and a third block removes it.
    """

    rows = REDUCED["QUERY_HEADS"]
    observed = {}
    for buffers in (2, 3):
        binary = _build(tmp_path, **REDUCED, MAX_POSITION_SPAN=256,
                        BANK_WORDS=65536, OUT_BUFFERS=buffers)
        for span in (16, 128):
            report, fields, _ = _case(
                tmp_path, binary, REDUCED, rows, span, 0x31 + span
            )
            observed[buffers, span] = fields["cycles"] / fields["count"]
            print(f"OUT_BUFFERS={buffers} {report}  "
                  f"cycles/element={observed[buffers, span]:.4f}")
    # A longer span amortises the one-block epilogue, at either depth.
    assert observed[2, 128] < observed[2, 16]
    assert observed[3, 128] < observed[3, 16]
    # The default depth is within 4% of one element per cycle, and the third
    # block buys the per-position bubble back.
    assert observed[2, 128] < 1.04
    assert observed[3, 128] < 1.02
    assert observed[3, 128] < observed[2, 128]


@needs_iverilog
@pytest.mark.parametrize(
    "geometry",
    (dict(QUERY_HEADS=6, KEY_HEADS=3, HEAD_WIDTH=6),
     dict(QUERY_HEADS=1, KEY_HEADS=1, HEAD_WIDTH=2),
     dict(QUERY_HEADS=3, KEY_HEADS=2, HEAD_WIDTH=64)),
    ids=("6x3x6", "1x1x2", "3x2x64"),
)
def test_no_geometry_is_frozen(geometry, tmp_path):
    """Geometries the shipped constants would have refused, span 1 and span 16.

    1x1x2 is the narrowest head a half-rotation can have, and it is the case a
    hand-sized index or a doubled half width breaks rather than refuses.
    """

    binary = _build(tmp_path, **geometry, MAX_POSITION_SPAN=64, BANK_WORDS=16384)
    for rows in sorted({geometry["QUERY_HEADS"], geometry["KEY_HEADS"]}):
        for span in (1, 16):
            report, _, _ = _case(
                tmp_path, binary, geometry, rows, span, 0x99 + span + rows
            )
            print(report)


@needs_iverilog
def test_a_count_that_is_not_a_whole_number_of_positions_is_refused(tmp_path):
    """The negative control for the span recovery.

    Without it the test above would pass just as well if the count check had
    been deleted, which would let a short or ragged destination be written.
    """

    binary = _build(tmp_path, **REDUCED, MAX_POSITION_SPAN=64)
    _write(tmp_path, *_operands(8, 16, 4, 5))
    report, fields, _ = _run(binary, tmp_path, 8, 1, "+count=300")
    print(report)
    assert fields["err"] == 7, report
    assert fields["writes"] == 0, report


@needs_iverilog
def test_a_span_beyond_the_bound_is_refused(tmp_path):
    """MAX_POSITION_SPAN is a real bound, not a comment."""

    binary = _build(tmp_path, **REDUCED, MAX_POSITION_SPAN=4)
    _write(tmp_path, *_operands(8, 16, 8, 6))
    report, fields, _ = _run(binary, tmp_path, 8, 8)
    print(report)
    assert fields["err"] == 7, report
    assert fields["writes"] == 0, report


@needs_iverilog
def test_a_nonfinite_operand_fails_closed_without_tearing_a_position(tmp_path):
    """Atomicity, which a span makes a per-position rather than a per-launch claim.

    The qualified core validates every element of its launch before its first
    destination write.  Buffering a whole 16-position span to keep that literal
    statement would cost sixteen output blocks for nothing, because positions are
    independent -- so the lane drains a block only once its last element has
    retired without fault.  A poisoned word must therefore leave whole positions
    behind it and never a torn one.
    """

    binary = _build(tmp_path, **REDUCED, MAX_POSITION_SPAN=64)
    rows, cols, span = 8, 16, 4
    block = rows * cols

    codes, coefficients = _operands(rows, cols, span, 7)
    codes[2 * block + 40] = 0x7F80          # BF16 infinity in position 2
    _write(tmp_path, codes, coefficients)
    report, fields, _ = _run(binary, tmp_path, rows, span)
    print(report)
    assert fields["err"] == 1, report
    assert fields["writes"] % block == 0, report
    assert fields["writes"] <= 2 * block, report

    codes, coefficients = _operands(rows, cols, span, 7)
    coefficients[5] = 0x7F800000            # binary32 infinity in row 0
    _write(tmp_path, codes, coefficients)
    report, fields, _ = _run(binary, tmp_path, rows, span)
    print(report)
    assert fields["err"] == 1, report
    assert fields["writes"] == 0, report

    # The same poison at span 1, on the unchanged qualified core.
    codes, coefficients = _operands(rows, cols, 1, 7)
    codes[40] = 0x7F80
    _write(tmp_path, codes, coefficients)
    report, fields, _ = _run(binary, tmp_path, rows, 1)
    print(report)
    assert fields["err"] == 1, report
    assert fields["writes"] == 0, report


def _verilate(work: Path, **params: int) -> Path:
    binary = (work / "vrope").resolve()
    if binary.exists():
        return binary
    command = [
        str(PINNED_VERILATOR), "--binary", "--timing", "-Wno-fatal", "-j", "4",
        "--top-module", "tb_a3_rope_span",
        "--Mdir", str((work / "obj_rope").resolve()), "-o", str(binary),
    ]
    for name, value in params.items():
        command.append(f"-G{name}={value}")
    command += [str(REPO_ROOT / source) for source in SOURCES]
    built = subprocess.run(
        command, cwd=work, capture_output=True, text=True, timeout=1800
    )
    assert built.returncode == 0, built.stdout + built.stderr
    return binary


@needs_iverilog
@needs_pinned_verilator
def test_both_simulators_agree_word_for_word_on_a_span(tmp_path):
    """Dual-simulator evidence, which is what this repository calls closed.

    The same operand images through Icarus and through the pinned Verilator,
    compared against each other AND against the oracle, including the cycle
    count -- so a span that only one simulator retires correctly is a finding
    rather than a pass.
    """

    geometry = dict(REDUCED, MAX_POSITION_SPAN=256, BANK_WORDS=16384)
    icarus = _build(tmp_path, **geometry)
    verilated = _verilate(tmp_path, **geometry)
    cols = REDUCED["HEAD_WIDTH"]
    for rows, span in ((REDUCED["QUERY_HEADS"], 1), (REDUCED["QUERY_HEADS"], 16),
                       (REDUCED["KEY_HEADS"], 7)):
        codes, coefficients = _operands(rows, cols, span, 0xBEEF + span)
        _write(tmp_path, codes, coefficients)
        icarus_report, icarus_fields, icarus_words = _run(
            icarus, tmp_path, rows, span
        )
        verilated_report, verilated_fields, verilated_words = _run(
            verilated, tmp_path, rows, span, runner=()
        )
        print(f"iverilog  {icarus_report}")
        print(f"verilator {verilated_report}")
        expected = _reference(codes, coefficients, rows, cols, span)
        assert icarus_words == expected, icarus_report
        assert verilated_words == expected, verilated_report
        assert icarus_fields == verilated_fields, (
            f"{icarus_report}\n{verilated_report}"
        )
