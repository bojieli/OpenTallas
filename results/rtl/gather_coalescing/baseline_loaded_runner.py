#!/usr/bin/env python3
"""Qualify a host-loaded ABI contraction through the G2 runtime path."""

from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--write-outstanding", type=int, choices=[1, 2, 4, 8], default=4)
parser.add_argument("--strided-weights", action="store_true")
parser.add_argument("--strided-output", action="store_true")
parser.add_argument("--object-writes", action="store_true")
parser.add_argument("--output-backpressure", action="store_true")
parser.add_argument("--auxiliary-windows", action="store_true")
parser.add_argument("--no-weight-word-handoff", action="store_true")
parser.add_argument("--no-weight-line-retention", action="store_true")
parser.add_argument("--weight-object-reads", action="store_true")
parser.add_argument("--input-layout", action="store_true")
parser.add_argument("--no-weight-row-reuse", action="store_true")
parser.add_argument("--pass-first", action="store_true")
parser.add_argument("--auto-schedule", action="store_true", help="Choose row/pass order and pass width from residency before elaboration")
parser.add_argument("--pass-columns",type=int,choices=[1,2,3],default=3)
parser.add_argument("--weight-read-credits", type=int, choices=[1,2,4,8], default=1)
parser.add_argument("--weight-object-outstanding", type=int, choices=[1,2,4,8], default=1)
parser.add_argument("--weight-response-gap", type=int, default=1)
parser.add_argument("--weight-object-latency", type=int, default=3, help="Response delay cycles in the single-outstanding object-read fixture")
parser.add_argument("--depth", type=int, default=80)
parser.add_argument("--cols", type=int, default=None)
parser.add_argument("--activation-miss-aligned", action="store_true")
parser.add_argument("--auxiliary-depth", type=int, choices=[1, 2, 3, 4, 8], default=3)
parser.add_argument("--registered-auxiliary-requests", action="store_true")
args = parser.parse_args()
if args.depth < 2 or args.depth > 65535:
    parser.error("depth must be in 2..65535")
depth = args.depth
if args.weight_object_latency < 0 or args.weight_object_latency > 64:
    parser.error("weight object latency must be in 0..64")
if args.weight_response_gap < 1:
    parser.error("weight response gap must be positive")
rows = 6 if args.output_backpressure else 1
cols = args.cols if args.cols is not None else (24 if args.auxiliary_windows else 8)
if cols < 8 or cols > 65528:
    parser.error("cols must be in 8..65528")
logical_cols = cols
cols = (logical_cols + 7) & ~7
schedule_policy = None
if args.auto_schedule:
    if args.pass_first or args.pass_columns != 3 or args.no_weight_row_reuse:
        parser.error("--auto-schedule requires default schedule flags and enabled weight reuse")
    from tools.g2_schedule_policy import choose_schedule
    schedule_policy = choose_schedule(rows, logical_cols, depth)
    args.pass_first = schedule_policy['pass_first']
    args.pass_columns = schedule_policy['pass_columns']
    # Compare schedules over the same actual object I/O path.
    args.weight_object_reads = True
    args.object_writes = True
    print("schedule policy: " + json.dumps(schedule_policy), flush=True)
if args.pass_columns!=3 and not args.pass_first:
    parser.error("nondefault pass width requires --pass-first")
if args.pass_first:
    args.weight_object_reads=True
    args.object_writes=True
if args.strided_weights:
    args.weight_object_reads = True
if args.weight_object_reads:
    args.input_layout = True
record_name = (
    "g2_runtime_byte_transport"
    if args.auxiliary_windows
    else "g2_runtime_output"
    if args.output_backpressure
    else "g2_runtime_program"
)
if args.no_weight_row_reuse:
    record_name += "_no_weight_reuse"
if args.weight_read_credits != 1 or args.weight_object_outstanding != 1:
    record_name += f"_readcredits{args.weight_read_credits}_objectqueue{args.weight_object_outstanding}"
if args.weight_object_latency != 3:
    record_name += f"_object_latency{args.weight_object_latency}"
if args.weight_response_gap != 1:
    record_name += f"_weight_gap{args.weight_response_gap}"
if depth != 80:
    record_name += f"_depth{depth}"
if args.cols is not None:
    record_name += f"_cols{logical_cols}"
if args.activation_miss_aligned:
    record_name += "_rolling_activation"
record_name += f"_auxdepth{args.auxiliary_depth}"
record_name += "_registered" if args.registered_auxiliary_requests else "_direct"
if args.object_writes:
    record_name += f"_object_writes_depth{args.write_outstanding}"
if args.strided_output:
    record_name += "_strided_output"
if args.input_layout:
    record_name += "_input_layout"
if args.weight_object_reads:
    record_name += "_weight_object_reads"
if args.no_weight_line_retention:
    record_name += "_no_weight_line_retention"
if args.strided_weights:
    record_name += "_strided_weights"
if args.no_weight_word_handoff:
    record_name += "_no_word_handoff"
if args.pass_first:
    record_name += "_pass_first"
if args.pass_columns!=3:
    record_name += f"_passcols{args.pass_columns}"
if args.auto_schedule:
    record_name += "_auto_schedule"
record_name += "_before_coalescing_probe"
OUT = ROOT / "build" / record_name
OUT.mkdir(parents=True, exist_ok=True)
from tools.build_abi3_engine_vectors import (  # noqa: E402
    engine_capability,
    matmul_case,
    run_golden,
    load_engines,
    verify_deployment,
    DType,
)

capability = engine_capability()
# Non-square and lane-distinct: the wrong B shape or transposition cannot pass.
activation = np.resize(
    np.array([0x3F80, 0x3F00, 0xBF80, 0x3E80, 0x4000], dtype=np.uint16), (rows, depth)
)
activation[1::2] ^= np.uint16(0x8000)
weight = np.repeat(
    np.array(
        [0x3F80, 0x4000, 0x4040, 0x4080, 0xBF80, 0xC000, 0xC040, 0xC080],
        dtype=np.uint16,
    )[:, None],
    depth,
    axis=1,
)
weight = np.tile(weight, (cols // 8, 1))
# Distinguish local columns as well as lanes and K to expose replay aliasing.
for column in range(cols // 8):
    weight[column * 8 : (column + 1) * 8] = np.roll(
        weight[column * 8 : (column + 1) * 8], column, axis=0
    )
weight[:, 2::7] ^= np.uint16(0x8000)
weight[:, 5::11] = 0
case = matmul_case(
    "g2_runtime_program",
    "Non-square program dispatch",
    capability,
    OUT / "deployment",
    activation_codes=activation,
    weight_codes=weight[:logical_cols],
    activation_dtype=DType.BF16,
    weight_dtype=DType.BF16,
    output_strides=(2*logical_cols+5, 2) if args.strided_output else None,
    output_element_offset=7 if args.strided_output else 0,
    weight_strides=(2*depth+5, 2) if args.strided_weights else None,
    weight_element_offset=11 if args.strided_weights else 0,
)
admission = verify_deployment(case.deployment, capability)
assert admission.admitted, admission.errors
load_engines()
golden = run_golden(case, capability)
assert golden["status"] == 0 and golden["trap_class"] == 0, golden["message"]
image = case.deployment.program
count = int.from_bytes(image[16:20], "little")
work = int.from_bytes(image[184:192], "little")
assert count <= 128 and len(case.deployment.table) <= 341
assert not case.symbols, "This fixture must not need symbol loading"


def hex_words(name, values, digits):
    (OUT / name).write_text("".join(f"{int(v):0{digits}x}\n" for v in values))


hex_words(
    "program.hex",
    [
        int.from_bytes(image[i : i + 16], "little")
        for i in range(256, 256 + count * 32, 16)
    ],
    32,
)
desc = []
for record in case.deployment.table._records:
    prefix = record[:192].ljust(192, b"\0")
    desc.extend(int.from_bytes(prefix[i : i + 16], "little") for i in range(0, 192, 16))
hex_words("descriptor.hex", desc, 32)
hex_words(
    "weight.hex",
    [
        sum(int(weight[column * 8 + lane, k]) << (16 * lane) for lane in range(8))
        for _ in range(rows)
        for pass_base in range(0, cols // 8, args.pass_columns)
        for k in range(depth)
        for column in range(pass_base, min(pass_base + args.pass_columns, cols // 8))
    ],
    32,
)
hex_words("activation.hex", activation.reshape(-1), 16)
# Read the actual deployment object's bytes, not prepacked service words.
from runtime.sim.device import Device  # noqa: E402

reference_device = Device(case.deployment, capability, verify=False)
activation_view = reference_device.views.resolve(case.operand0_view, {}, {})
activation_object = activation_view.object_id
weight_view = reference_device.views.resolve(case.operand1_view, {}, {})
weight_object = weight_view.object_id
output_view = reference_device.views.resolve(case.output_view, {}, {})
output_object = output_view.object_id
output_base = 7 if args.strided_output else 0
output_row_stride, output_col_stride = output_view.strides
output_bytes = 2*(output_base+(rows-1)*output_row_stride+(logical_cols-1)*output_col_stride+1)
activation_payload = reference_device.memory[activation_object].read(
    0, activation.nbytes
)
assert activation_payload == activation.astype("<u2").tobytes()
hex_words("activation_bytes.hex", activation_payload, 2)
weight_base = 11 if args.strided_weights else 0
weight_column_stride, weight_k_stride = weight_view.strides
weight_object_bytes = 2*(weight_base+(logical_cols-1)*weight_column_stride+(depth-1)*weight_k_stride+1)
weight_payload = reference_device.memory[weight_object].read(0, weight_object_bytes)
for column in range(logical_cols):
    for k in range(depth):
        offset = 2*(weight_base+column*weight_column_stride+k*weight_k_stride)
        assert int.from_bytes(weight_payload[offset:offset+2], "little") == int(weight[column, k])
hex_words("weight_bytes.hex", weight_payload, 2)
expected_padded = np.zeros((rows, cols), dtype=np.uint32)
expected_padded[:, :logical_cols] = golden["output"]
hex_words("expected.hex", expected_padded.reshape(-1), 8)
# Independent page-residency oracle for the admitted row/pass/K issue order.
# A later column pass can revisit a page evicted while reading the same row.
resident_page = None
expected_activation_fills = 0
issue_order=[(row,p) for row in range(rows) for p in range(0,cols//8,args.pass_columns)]
if args.pass_first:
    issue_order.sort(key=lambda rp:(rp[1],rp[0]))
for row,pass_base in issue_order:
    for k in range(depth):
        page = ((row * depth + k) // 256) * 256
        address = row * depth + k
        hit = resident_page is not None and resident_page <= address < min(resident_page + 256, rows * depth)
        if not hit:
            page = address if args.activation_miss_aligned else page
            expected_activation_fills += min(256, rows * depth - page)
            resident_page = page
expected_weight_fills=rows*(cols//8)*depth
if not args.no_weight_row_reuse and rows>1:
    if args.pass_first:
        expected_weight_fills=sum(min(args.pass_columns,cols//8-p)*depth *
            (1 if min(args.pass_columns,cols//8-p)*depth<=1024 else rows)
            for p in range(0,cols//8,args.pass_columns))
    elif (cols//8)*depth<=1024:
        expected_weight_fills=(cols//8)*depth
(OUT / "program_config.svh").write_text(
    f"localparam integer PROGRAM_WORDS={count * 2}, DESCRIPTOR_WORDS={len(desc)};\n"
    f"localparam integer INSTRUCTION_COUNT={count};\n"
    f"localparam [31:0] ACTIVATION_OBJECT=32'd{activation_object}, OUTPUT_OBJECT=32'd{output_object};\n"
    f"localparam integer WEIGHT_BASE={weight_base}, WEIGHT_COLUMN_STRIDE={weight_column_stride}, WEIGHT_K_STRIDE={weight_k_stride}, WEIGHT_OBJECT_BYTES={weight_object_bytes};\n"
    f"localparam [31:0] WEIGHT_OBJECT=32'd{weight_object};\n"
    f"localparam integer ROWS={rows}, COLS={cols}, LOGICAL_COLS={logical_cols}, DEPTH={depth}, STRESS_OUTPUT={int(args.output_backpressure)}, SRAM_AUX={int(args.auxiliary_windows)};\n"
    f"localparam integer OUTPUT_BASE={output_base}, OUTPUT_ROW_STRIDE={output_row_stride}, OUTPUT_COL_STRIDE={output_col_stride}, OUTPUT_BYTES={output_bytes};\n"
    f"localparam integer EXPECTED_WEIGHT_FILLS={expected_weight_fills};\n"
    f"localparam integer EXPECTED_ACTIVATION_FILLS={expected_activation_fills};\n"
    f"localparam [63:0] MAX_WORK=64'd{work};\n"
)
packages = [
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_lane_pkg.sv",
    "rtl/abi3/ot_a3_pkg.sv",
]
sources = packages + [
    "rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv",
    "rtl/abi3/ot_a3_g2_cluster.sv",
    "rtl/test/tb_a3_g2_runtime_program.sv",
]
# Include hashes of library-resolved dependencies; logs identify elaborated design.
tracked = sorted(
    set(
        sources
        + [
            "tools/check_g2_runtime_program.py",
            "tools/g2_schedule_policy.py",
            "tools/build_abi3_engine_vectors.py",
            "runtime/sim/engines/tensor.py",
            "rtl/test/tb_a3_g2_issue_contract.sv",
            "tests/test_g2_issue_contract.py",
            "tests/test_reserved_output_queue.py",
            "tests/test_runtime_auxiliary_windows.py",
            "tests/test_auxiliary_window_scheduler.py",
            "tests/test_operand_byte_mapper.py",
            "tests/test_weight_row_reuse.py",
        ]
        + [
            str(p.relative_to(ROOT))
            for d in ["rtl/abi3", "rtl/proto"]
            for p in (ROOT / d).glob("*.sv")
        ]
    )
)
tracked.remove("rtl/abi3/ot_a3_bf16_weight_gather.sv")
tracked += ["results/rtl/before_gather_coalescing/gather.sv", "results/rtl/gather_coalescing/baseline_loaded_runner.py"]
hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked}
cmd = [
    str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"),
    "--binary",
    "--timing",
    "-j",
    "4",
    "-Wno-fatal",
    "-DOT_A3_FAKERAM_BEHAVIOURAL",
    f"-GWRITE_OUTSTANDING={args.write_outstanding}",
    f"-GWEIGHT_WORD_HANDOFF={int(not args.no_weight_word_handoff)}",
    f"-GWEIGHT_LINE_REUSE={int(not args.no_weight_line_retention)}",
    f"-GWEIGHT_OBJECT_READS={int(args.weight_object_reads)}",
    f"-GINPUT_LAYOUT={int(args.input_layout)}",
    f"-GOBJECT_WRITES={int(args.object_writes)}",
    f"-GPASS_COLUMNS={args.pass_columns}",
    f"-GPASS_FIRST={int(args.pass_first)}",
    f"-GWEIGHT_ROW_REUSE={int(not args.no_weight_row_reuse)}",
    f"-GAUXILIARY_DEPTH={args.auxiliary_depth}",
    f"-GREGISTER_AUXILIARY_REQUESTS={int(args.registered_auxiliary_requests)}",
    f"-GWEIGHT_RESPONSE_GAP={args.weight_response_gap}",
    f"-GWEIGHT_OBJECT_LATENCY={args.weight_object_latency}",
    f"-GWEIGHT_READ_CREDITS={args.weight_read_credits}",
    f"-GWEIGHT_OBJECT_OUTSTANDING={args.weight_object_outstanding}",
    f"-GACTIVATION_MISS_ALIGNED={int(args.activation_miss_aligned)}",
    "--top-module",
    "tb_a3_g2_runtime_program",
    "-I" + str(OUT),
    "--Mdir",
    str(OUT / "obj"),
    "-o",
    "sim",
    "-y",
    str(ROOT / "rtl/abi3"),
    "-y",
    str(ROOT / "rtl"),
    "-y",
    str(ROOT / "rtl/proto"),
    str(ROOT / "results/rtl/before_gather_coalescing/gather.sv"),
    *[str(ROOT / p) for p in sources],
]
with (OUT / "compile.log").open("w") as log:
    subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT)
r = subprocess.run(
    [str(OUT / "obj/sim")], capture_output=True, text=True, timeout=120, cwd=OUT
)
(OUT / "simulation.log").write_text(r.stdout + r.stderr)
assert r.returncode == 0, r.stdout + r.stderr
assert "PASS G2 runtime program" in r.stdout
for p, h in hashes.items():
    assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p
phase_latencies=[{"phase":int(phase),"cycles":int(cycles)} for phase,cycles in
    re.findall(r"phase latency phase=(\d+) elapsed_cycles=(\d+)",r.stdout)]
assert phase_latencies and all(x["cycles"]>0 for x in phase_latencies)
result = {
    "status": "pass",
    "schedule_policy": schedule_policy,
    "phase_latencies": phase_latencies,
    "phase_latency_scope": "Kick-to-program-done under modeled memory, output stalls and explicit drain acknowledgements; not whole-model inference latency.",
    "object_writes": args.object_writes,
    "descriptor_input_layout": args.input_layout,
    "weight_object_reads": args.weight_object_reads,
    "strided_weights": args.strided_weights,
    "weight_word_handoff": not args.no_weight_word_handoff,
    "weight_line_retention": not args.no_weight_line_retention,
    "weight_object_sha256": hashlib.sha256(weight_payload).hexdigest(),
    "strided_output": args.strided_output,
    "write_outstanding": args.write_outstanding,
    "pass_first": args.pass_first,
    "pass_columns": args.pass_columns,
    "weight_row_reuse": not args.no_weight_row_reuse,
    "auxiliary_depth": args.auxiliary_depth,
    "registered_auxiliary_requests": args.registered_auxiliary_requests,
    "weight_response_gap": args.weight_response_gap,
    "weight_read_credits": args.weight_read_credits,
    "weight_object_service": {"response_delay_cycles": args.weight_object_latency,
                              "outstanding_limit": args.weight_object_outstanding,
                              "request_ready_pattern": "cycles modulo 5 != 0"},
    "activation_miss_aligned": args.activation_miss_aligned,
    "output_backpressure": args.output_backpressure,
    "auxiliary_sram_windows": args.auxiliary_windows,
    "rtl_auxiliary_scheduler": args.auxiliary_windows,
    "object_byte_transport": args.auxiliary_windows,
    "activation_object": activation_object,
    "descriptor_output_object": output_object,
    "activation_object_sha256": hashlib.sha256(activation_payload).hexdigest(),
    "scope": "Host-loaded admitted ABI program and descriptors through actual G2 sequencer/adapter/runtime/LQ8, compared with functional Device. Behavioral SRAM and external services; no physical closure.",
    "sources": hashes,
    "program_sha256": hashlib.sha256(image).hexdigest(),
    "descriptor_sha256": hashlib.sha256(case.deployment.table.encode()).hexdigest(),
    "golden_output": golden["output"].reshape(-1).tolist(),
    "fixture": {
        "rows": rows,
        "cols": logical_cols,
        "padded_cols": cols,
        "depth": depth,
        "expected_weight_fills": expected_weight_fills,
        "expected_activation_fills": expected_activation_fills,
        "dtype": "BF16",
        "weight_packing": "Synthesizable cluster cursor and cached gather read ABI object bytes" if args.weight_object_reads else "External fixture service repacks ABI N-major weights into eight-lane words",
        "weight_element_base": weight_base,
        "weight_strides": [weight_column_stride, weight_k_stride],
        "weight_object_bytes": weight_object_bytes,
        "output_element_base": output_base,
        "output_strides": [output_row_stride, output_col_stride],
        "output_object_bytes": output_bytes,
        "output_addressing": "Subtract output_element_base from lane-local address; derive row and column using padded width and lane. Byte offset=2*(base+row*row_stride+column*col_stride).",
    },
    "command": cmd,
    "stdout": r.stdout,
    "artifacts": {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(OUT.glob("*.hex"))
        + [OUT / "program_config.svh", OUT / "simulation.log"]
    },
}
(ROOT / "results/rtl" / f"a3_{record_name}.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(r.stdout)
