#!/usr/bin/env python3
"""Qualify a host-loaded ABI contraction through the G2 runtime path."""

from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-backpressure", action="store_true")
parser.add_argument("--auxiliary-windows", action="store_true")
parser.add_argument("--no-weight-row-reuse", action="store_true")
parser.add_argument("--weight-response-gap", type=int, default=1)
parser.add_argument("--depth", type=int, default=80)
parser.add_argument("--cols", type=int, default=None)
parser.add_argument("--activation-miss-aligned", action="store_true")
args = parser.parse_args()
if args.depth < 2 or args.depth > 65535:
    parser.error("depth must be in 2..65535")
depth = args.depth
if args.weight_response_gap < 1:
    parser.error("weight response gap must be positive")
rows = 6 if args.output_backpressure else 1
cols = args.cols if args.cols is not None else (24 if args.auxiliary_windows else 8)
if cols < 8 or cols > 65528 or cols % 8:
    parser.error("cols must be a positive multiple of eight up to 65528")
record_name = (
    "g2_runtime_byte_transport"
    if args.auxiliary_windows
    else "g2_runtime_output"
    if args.output_backpressure
    else "g2_runtime_program"
)
if args.no_weight_row_reuse:
    record_name += "_no_weight_reuse"
if args.weight_response_gap != 1:
    record_name += f"_weight_gap{args.weight_response_gap}"
if depth != 80:
    record_name += f"_depth{depth}"
if args.cols is not None:
    record_name += f"_cols{cols}"
if args.activation_miss_aligned:
    record_name += "_rolling_activation"
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
    weight_codes=weight,
    activation_dtype=DType.BF16,
    weight_dtype=DType.BF16,
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
        for pass_base in range(0, cols // 8, 3)
        for k in range(depth)
        for column in range(pass_base, min(pass_base + 3, cols // 8))
    ],
    32,
)
hex_words("activation.hex", activation.reshape(-1), 16)
# Read the actual deployment object's bytes, not prepacked service words.
from runtime.sim.device import Device  # noqa: E402

reference_device = Device(case.deployment, capability, verify=False)
activation_view = reference_device.views.resolve(case.operand0_view, {}, {})
activation_object = activation_view.object_id
activation_payload = reference_device.memory[activation_object].read(
    0, activation.nbytes
)
assert activation_payload == activation.astype("<u2").tobytes()
hex_words("activation_bytes.hex", activation_payload, 2)
hex_words("expected.hex", golden["output"].reshape(-1), 8)
# Independent page-residency oracle for the admitted row/pass/K issue order.
# A later column pass can revisit a page evicted while reading the same row.
resident_page = None
expected_activation_fills = 0
for row in range(rows):
    for pass_base in range(0, cols // 8, 3):
        for k in range(depth):
            page = ((row * depth + k) // 256) * 256
            address = row * depth + k
            hit = resident_page is not None and resident_page <= address < min(resident_page + 256, rows * depth)
            if not hit:
                page = address if args.activation_miss_aligned else page
                expected_activation_fills += min(256, rows * depth - page)
                resident_page = page
(OUT / "program_config.svh").write_text(
    f"localparam integer PROGRAM_WORDS={count * 2}, DESCRIPTOR_WORDS={len(desc)};\n"
    f"localparam integer INSTRUCTION_COUNT={count};\n"
    f"localparam [31:0] ACTIVATION_OBJECT=32'd{activation_object};\n"
    f"localparam integer ROWS={rows}, COLS={cols}, DEPTH={depth}, STRESS_OUTPUT={int(args.output_backpressure)}, SRAM_AUX={int(args.auxiliary_windows)};\n"
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
hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked}
cmd = [
    str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"),
    "--binary",
    "--timing",
    "-j",
    "4",
    "-Wno-fatal",
    "-DOT_A3_FAKERAM_BEHAVIOURAL",
    f"-GWEIGHT_ROW_REUSE={int(not args.no_weight_row_reuse)}",
    f"-GWEIGHT_RESPONSE_GAP={args.weight_response_gap}",
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
result = {
    "status": "pass",
    "weight_row_reuse": not args.no_weight_row_reuse,
    "weight_response_gap": args.weight_response_gap,
    "activation_miss_aligned": args.activation_miss_aligned,
    "output_backpressure": args.output_backpressure,
    "auxiliary_sram_windows": args.auxiliary_windows,
    "rtl_auxiliary_scheduler": args.auxiliary_windows,
    "object_byte_transport": args.auxiliary_windows,
    "activation_object": activation_object,
    "activation_object_sha256": hashlib.sha256(activation_payload).hexdigest(),
    "scope": "Host-loaded admitted ABI program and descriptors through actual G2 sequencer/adapter/runtime/LQ8, compared with functional Device. Behavioral SRAM and external services; no physical closure.",
    "sources": hashes,
    "program_sha256": hashlib.sha256(image).hexdigest(),
    "descriptor_sha256": hashlib.sha256(case.deployment.table.encode()).hexdigest(),
    "golden_output": golden["output"].reshape(-1).tolist(),
    "fixture": {
        "rows": rows,
        "cols": cols,
        "depth": depth,
        "expected_activation_fills": expected_activation_fills,
        "dtype": "BF16",
        "weight_packing": "External fixture service repacks ABI N-major weights into eight-lane words",
        "output_addressing": "Logical flattened output index equals lane-local address times eight plus lane index",
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
