#!/usr/bin/env python3
"""Verify LQ8 arithmetic through bounded SRAM tiles and complete bundle joining."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.rtl_abi3_lq8_campaign import RTL_SOURCES  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build", type=Path, default=ROOT / "build/runtime_lq8_operands"
    )
    parser.add_argument("--serial-refill", action="store_true")
    parser.add_argument("--future-auxiliary", action="store_true")
    parser.add_argument(
        "--auxiliary-depth", type=int, choices=[1, 2, 3, 4, 8], default=2
    )
    parser.add_argument("--rtl-weight-scheduler", action="store_true")
    parser.add_argument("--mutate-array-config", action="store_true")
    parser.add_argument("--integrated-service", action="store_true")
    args = parser.parse_args()
    if args.rtl_weight_scheduler and not args.future_auxiliary:
        parser.error(
            "RTL scheduler requires captured geometry admission (--future-auxiliary)"
        )
    if args.rtl_weight_scheduler and args.serial_refill:
        parser.error("RTL scheduler currently implements overlapped refill only")
    out = args.build.resolve()
    out.mkdir(parents=True, exist_ok=True)
    top = (ROOT / "rtl/test/a3_lq8_top.sv").read_text()
    top = re.sub(
        r"^\s*if \(d_(?:a|s|w|ws)_en[^\n]*d_(?:a|s|w|ws)_data\s*<=.*$",
        "",
        top,
        flags=re.M,
    )
    for name in ["a", "s", "w", "ws"]:
        top = re.sub(r"(reg)(\s+\[[^\n]+\]\s+d_" + name + r"_data;)", r"wire\2", top)
    service = (ROOT / "rtl/test/a3_lq8_runtime_service.svh").read_text()
    if args.rtl_weight_scheduler:
        service = service.replace(
            "generation=0,fill_base=0,acquire_base=0,stream_end=0",
            "generation=0",
        )
        service = service.replace(
            "    reg fill_bank=0,acquire_bank=0,filling=0;\n    reg [9:0] fill_index=0;\n",
            "",
        )
        service = re.sub(
            r"            stream_end<=cfg_w_base.*?;\n", "", service, flags=re.S
        )
        first = service.index("    wire [9:0] fill_words=")
        end = service.index("    ot_a3_weight_tile_prefetch prefetch(", first)
        service = (
            service[:first]
            + (ROOT / "rtl/test/a3_lq8_scheduled_weights.svh").read_text()
            + service[end:]
        )
        service = service.replace(
            ".reserve_bank(fill_bank)", ".reserve_bank(reserve_bank)"
        )
        service = service.replace(
            ".reserve_tag({generation,fill_base})", ".reserve_tag(reserve_tag)"
        )
        service = service.replace(
            ".fill_tag({generation,fill_base})", ".fill_tag(fill_tag)"
        )
        service = service.replace(
            ".fill_data(w_mem[fill_base+{22'b0,fill_index}])", ".fill_data(fill_data)"
        )
        service = service.replace(".tile_bank(acquire_bank)", ".tile_bank(tile_bank)")
        service = service.replace(
            ".tile_tag({generation,acquire_base})", ".tile_tag(tile_tag)"
        )
        service = service.replace("filling<=0;fill_index<=0;", "")
        service = service.replace(
            "            fill_base<=cfg_w_base;acquire_base<=cfg_w_base;\n", ""
        )
        service = service.replace("fill_bank<=0;acquire_bank<=0;", "")
        first = service.index(
            "            if(reserve_valid && reserve_ready)begin filling<=1;"
        )
        end = service.index("            if(operand_request && !aux_valid", first)
        service = (
            service[:first]
            + """            if(fill_valid && fill_ready)total_fills<=total_fills+1;
            if(tile_valid && tile_ready)begin total_tiles<=total_tiles+1;op_tiles<=op_tiles+1;end
"""
            + service[end:]
        )
    if args.future_auxiliary:
        first = service.index("    reg aux_valid=0")
        end = service.index("    ot_a3_lq8_operand_join joiner(", first)
        service = (
            service[:first]
            + (ROOT / "rtl/test/a3_lq8_future_auxiliary.svh").read_text()
            + service[end:]
        )
        first = service.index("            if(operand_request && !aux_valid")
        end = service.index("            // A response", first)
        service = service[:first] + service[end:]
        service = service.replace("aux_valid<=0;aux_pending<=0;", "")
        service = service.replace(
            ".auxiliary_generation(generation)", ".auxiliary_generation(aux_generation)"
        )
    if args.integrated_service:
        if args.serial_refill:
            parser.error("Integrated service uses overlapped refill")
        service = (ROOT / "rtl/test/a3_lq8_integrated_service.svh").read_text()
    top = top.replace(
        "    ot_a3_lq8 #(\n",
        f"    localparam SERIAL_REFILL=1'b{int(args.serial_refill)};\n"
        + f"    localparam integer AUXILIARY_DEPTH={args.auxiliary_depth};\n"
        + service
        + "\n    ot_a3_lq8 #(\n",
    )
    top = top.replace(
        ".ACC_SLOTS(ACC_SLOTS)\n    ) u_dut",
        ".ACC_SLOTS(ACC_SLOTS),.OPERAND_CREDITS(1)\n    ) u_dut",
    )
    top = top.replace(
        ".start(start_dut),",
        """.start(start_dut),.operand_credit(operand_credit),
        .operand_request(operand_request),.operand_issue(operand_issue),
        .operand_a_addr(preview_a),.operand_s_addr(preview_s),
        .operand_ws_addr(preview_ws),.operand_w_addr(preview_w),""",
    )
    if args.mutate_array_config:
        # Only disturb DUT inputs. Backing images and reference keep the
        # accepted command, so every expected result remains independently fixed.
        begin = top.index("    ) u_dut (")
        end = top.index("\n    );", begin)
        section = top[begin:end]
        section = re.sub(
            r"\.(cfg_\w+)\((cfg_\w+)\)",
            lambda m: f".{m[1]}(start_dut ? {m[2]} : ~{m[2]})",
            section,
        )
        top = top[:begin] + section + top[end:]
    (out / "top.sv").write_text(top)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/build_abi3_lq8_vectors.py"),
            "--out-dir",
            str(out),
            "--profile",
            "quick",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    sources = [
        *RTL_SOURCES,
        "rtl/abi3/ot_a3_operand_bank_owner.sv",
        "rtl/abi3/ot_a3_runtime_weight_banks.sv",
        "rtl/abi3/ot_a3_weight_tile_prefetch.sv",
        "rtl/abi3/ot_a3_weight_tile_scheduler.sv",
        "rtl/abi3/ot_a3_lq8_operand_join.sv",
        "rtl/abi3/ot_a3_lq8_operand_cursor.sv",
        "rtl/abi3/ot_a3_lq8_operand_admission.sv",
        "rtl/abi3/ot_a3_lq8_auxiliary_prefetch.sv",
        "rtl/abi3/ot_a3_lq8_runtime_operands.sv",
        "rtl/test/tb_a3_runtime_weight_banks.sv",
        "rtl/test/tb_a3_lq8.sv",
    ]
    tool = (
        Path(
            os.environ.get(
                "OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools"
            )
        )
        / "verilator-5.050/bin/verilator"
    )
    command = [
        str(tool),
        "--binary",
        "--timing",
        "-Wno-fatal",
        "--top-module",
        "tb_a3_lq8",
        "--Mdir",
        str(out / "obj"),
        "-o",
        "sim",
        *[str(ROOT / p) for p in sources],
        str(out / "top.sv"),
    ]
    tracked = [
        *sources,
        "rtl/test/a3_lq8_top.sv",
        "rtl/test/a3_lq8_runtime_service.svh",
        "rtl/test/a3_lq8_integrated_service.svh",
        "rtl/test/a3_lq8_scheduled_weights.svh",
        "rtl/test/a3_lq8_future_auxiliary.svh",
        "tools/check_lq8_runtime_operands.py",
    ]
    source_hashes = {
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked
    }
    with (out / "compile.log").open("w") as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    run = subprocess.run(
        [str(out / "obj/sim")], cwd=out, capture_output=True, text=True, timeout=300
    )
    (out / "simulation.log").write_text(run.stdout + run.stderr)
    if run.returncode or "FAIL" in run.stdout or "PASS: ABI3 lq8" not in run.stdout:
        raise SystemExit((run.stdout + run.stderr)[-6000:])
    markers = [
        s
        for s in run.stdout.splitlines()
        if s.startswith(("PASS:", "RUNTIME ", "AUXILIARY ", "checks="))
    ]
    if any(
        hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest
        for p, digest in source_hashes.items()
    ):
        raise SystemExit("Sources changed during validation; evidence not published")
    operations = [
        dict(zip(("issues", "tiles", "cycles"), map(int, match)))
        for match in re.findall(
            r"RUNTIME_OP issues=(\d+) tiles=(\d+) cycles=(\d+)", run.stdout
        )
    ]
    result = {
        "schema": "opentallas.lq8_runtime_operands.v1",
        "status": "pass",
        "scope": "LQ8 + two 512x128 SRAM banks, 32-word tiles, four-word FIFO, complete auxiliary response from behavioral backing memory with variable delay. Not G2 integration, bounded activation storage, row reuse or physical closure.",
        "serial_refill": args.serial_refill,
        "integrated_service": args.integrated_service,
        "mutate_array_config": args.mutate_array_config,
        "rtl_weight_scheduler": args.rtl_weight_scheduler,
        "future_auxiliary": args.future_auxiliary,
        "auxiliary_depth": args.auxiliary_depth if args.future_auxiliary else 0,
        "sources": source_hashes,
        "operations": operations,
        "total_operation_cycles": sum(op["cycles"] for op in operations),
        "compile_command": command,
        "markers": markers,
        "artifacts": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                out / "top.sv",
                out / "simulation.log",
                out / "manifest.json",
                *sorted(out.glob("lq8_*.hex")),
            ]
        },
    }
    (out / "evidence.json").write_text(json.dumps(result, indent=2) + "\n")
    print("\n".join(markers))


if __name__ == "__main__":
    main()
