#!/usr/bin/env python3
"""Run the reproducible public-tool RTL static/CDC/RDC campaign.

The campaign is deliberately conservative: every synthesizable source is
inventoried, two independent language frontends elaborate the design, Yosys
performs structural checks, and source-level CDC/RDC invariants are checked
against a machine-readable crossing manifest.  A warning is a pass only when
it matches exactly one current, owned waiver.

This is public-tool methodology evidence, not target-qualified CDC/RDC, UPF,
lint, or foundry signoff.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl"
BUILD = RTL / "build" / "static"
RESULTS = ROOT / "results" / "rtl"
MANIFEST_PATH = ROOT / "spec" / "clock_reset_crossings.json"
WAIVER_PATH = ROOT / "spec" / "rtl_waivers.json"


def rtl_sources() -> tuple[str, ...]:
    paths = []
    for path in RTL.rglob("*.sv"):
        relative = path.relative_to(ROOT)
        if "formal" in relative.parts or "test" in relative.parts or "build" in relative.parts:
            continue
        paths.append(str(relative))
    return tuple(sorted(paths))


SOURCES = rtl_sources()
YOSYS_SOURCES = tuple(path for path in SOURCES if path != "rtl/lib/ot_crc_pkg.sv")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tool_version(command: list[str]) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        return {"available": False, "command": shlex.join(command)}
    run = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=15,
    )
    lines = [line.strip() for line in run.stdout.splitlines() if line.strip()]
    return {
        "available": True,
        "command": shlex.join(command),
        "executable": executable,
        "executable_sha256": sha256_file(Path(executable)),
        "version": lines[0] if lines else "no version text",
    }


def run_case(name: str, command: list[str], timeout: int = 180) -> dict[str, Any]:
    print(f"static: {name}", flush=True)
    try:
        run = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        output = run.stdout
        returncode: int | None = run.returncode
        status = "pass" if run.returncode == 0 else "fail"
    except subprocess.TimeoutExpired as exc:
        def timeout_text(value: str | bytes | None) -> str:
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value

        output = timeout_text(exc.stdout) + timeout_text(exc.stderr)
        returncode = None
        status = "timeout"
    log = BUILD / f"{name}.log"
    log.write_text(output, encoding="utf-8")
    return {
        "name": name,
        "status": status,
        "returncode": returncode,
        "timeout_seconds": timeout,
        "command": shlex.join(command),
        "log": str(log.relative_to(ROOT)),
        "output": output,
    }


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_modules_and_clock_resets(sources: Iterable[str]) -> tuple[list[dict[str, Any]], list[str]]:
    inventory: list[dict[str, Any]] = []
    errors: list[str] = []
    module_re = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)")
    port_re = re.compile(
        r"\b(input|output|inout)\s+(?:wire|reg|logic)\s+"
        r"(?:signed\s+)?(?:\[[^\]]+\]\s+)?([A-Za-z_][A-Za-z0-9_$]*)"
    )
    for source in sources:
        path = ROOT / source
        text = path.read_text(encoding="utf-8")
        first_nonblank = next((line.strip() for line in text.splitlines() if line.strip()), "")
        if first_nonblank != "`timescale 1ns/1ps":
            errors.append(f"{source}: missing canonical `timescale 1ns/1ps")
        modules = module_re.findall(text)
        is_package = bool(re.search(r"\bpackage\s+[A-Za-z_]", text))
        if not modules and not is_package:
            errors.append(f"{source}: no module or package declaration")
        ports = [
            {"direction": direction, "name": name}
            for direction, name in port_re.findall(text)
        ]
        clocks = sorted(
            item["name"]
            for item in ports
            if re.search(r"(?:^|_)(?:clk|clock)(?:$|_)", item["name"], re.IGNORECASE)
        )
        resets = sorted(
            item["name"]
            for item in ports
            if re.search(r"(?:^|_)(?:rst|reset)(?:_n)?(?:$|_)", item["name"], re.IGNORECASE)
        )
        inventory.append(
            {
                "path": source,
                "sha256": sha256_file(path),
                "kind": "package" if is_package and not modules else "module",
                "modules": modules,
                "clocks": clocks,
                "resets": resets,
            }
        )
    module_owners: dict[str, str] = {}
    for item in inventory:
        for module in item["modules"]:
            if module in module_owners:
                errors.append(
                    f"duplicate module {module}: {module_owners[module]} and {item['path']}"
                )
            module_owners[module] = item["path"]
    return inventory, errors


def parse_stage_top_ports() -> dict[str, str]:
    text = (RTL / "ot_stage_top.sv").read_text(encoding="utf-8")
    start = text.index("module ot_stage_top")
    end = text.index(");", start)
    header = text[start : end + 2]
    port_re = re.compile(
        r"\b(input|output|inout)\s+(?:wire|reg|logic)\s+"
        r"(?:signed\s+)?(?:\[[^\]]+\]\s+)?([A-Za-z_][A-Za-z0-9_$]*)"
    )
    return {name: direction for direction, name in port_re.findall(header)}


def check_manifest(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    actual_ports = parse_stage_top_ports()
    declared: dict[str, dict[str, str]] = {}
    for group in manifest.get("stage_top_port_groups", []):
        for signal in group.get("signals", []):
            if signal in declared:
                errors.append(f"manifest port {signal} appears in more than one group")
            declared[signal] = {
                "direction": group.get("direction", ""),
                "domain": group.get("domain", ""),
                "classification": group.get("classification", ""),
            }
    missing = sorted(set(actual_ports) - set(declared))
    extra = sorted(set(declared) - set(actual_ports))
    if missing:
        errors.append(f"stage-top ports missing from manifest: {', '.join(missing)}")
    if extra:
        errors.append(f"manifest names absent from stage top: {', '.join(extra)}")
    for name in sorted(set(actual_ports) & set(declared)):
        if actual_ports[name] != declared[name]["direction"]:
            errors.append(
                f"manifest direction mismatch for {name}: "
                f"RTL={actual_ports[name]} manifest={declared[name]['direction']}"
            )
        if not declared[name]["domain"] or not declared[name]["classification"]:
            errors.append(f"manifest port {name} lacks domain/classification")

    stage_text = (RTL / "ot_stage_top.sv").read_text(encoding="utf-8")
    seen_instances: set[str] = set()
    for crossing in manifest.get("crossings", []):
        required = {
            "id",
            "instance",
            "module",
            "source_domain",
            "destination_domain",
            "payload",
            "mechanism",
            "source_reset",
            "destination_reset",
            "reset_recovery",
            "spec_ref",
        }
        omitted = sorted(required - set(crossing))
        if omitted:
            errors.append(f"crossing {crossing.get('id', '?')} missing: {', '.join(omitted)}")
            continue
        instance = crossing["instance"]
        if instance in seen_instances:
            errors.append(f"crossing instance {instance} is duplicated")
        seen_instances.add(instance)
        pattern = re.compile(
            rf"\b{re.escape(crossing['module'])}\b\s*"
            rf"(?:#\s*\(.*?\)\s*)?{re.escape(instance)}\s*\(",
            re.DOTALL,
        )
        if not pattern.search(stage_text):
            errors.append(
                f"crossing {crossing['id']} does not map to "
                f"{crossing['module']} {instance} in ot_stage_top"
            )
        if not re.fullmatch(r"(?:CRP-2\.2|CRP-3\.1)", crossing["spec_ref"]):
            errors.append(f"crossing {crossing['id']} has invalid spec_ref")
    expected_instances = {
        "cmd_cdc",
        "rsp_cdc",
        "telemetry_cdc",
        "schedule_cdc",
        "status_snapshot_cdc",
        "ras_clear_cdc",
        "ras_safe_sync",
        "service_sync",
        "power_safe_sync",
        "idle_sync",
        "schedule_valid_sync",
        "core_reset_conditioner",
    }
    omitted_crossings = sorted(expected_instances - seen_instances)
    unexpected_crossings = sorted(seen_instances - expected_instances)
    if omitted_crossings:
        errors.append(f"required crossing instances missing: {', '.join(omitted_crossings)}")
    if unexpected_crossings:
        errors.append(f"unexpected crossing instances: {', '.join(unexpected_crossings)}")
    return {
        "top_port_count": len(actual_ports),
        "classified_port_count": len(declared),
        "crossing_count": len(manifest.get("crossings", [])),
        "reset_contract_count": len(manifest.get("resets", [])),
    }, errors


def require_patterns(
    checks: list[tuple[str, Path, str]],
) -> tuple[list[dict[str, str]], list[str]]:
    records: list[dict[str, str]] = []
    errors: list[str] = []
    cache: dict[Path, str] = {}
    for check_id, path, pattern in checks:
        text = cache.setdefault(path, path.read_text(encoding="utf-8"))
        if re.search(pattern, text, re.DOTALL):
            records.append({"id": check_id, "status": "pass", "path": str(path.relative_to(ROOT))})
        else:
            records.append({"id": check_id, "status": "fail", "path": str(path.relative_to(ROOT))})
            errors.append(f"structural pattern {check_id} not found in {path.relative_to(ROOT)}")
    return records, errors


def structural_checks() -> tuple[list[dict[str, str]], list[str]]:
    fifo = RTL / "lib" / "ot_async_fifo.sv"
    mailbox = RTL / "lib" / "ot_cdc_mailbox.sv"
    reset_sync = RTL / "lib" / "ot_reset_sync.sv"
    sync_bits = RTL / "lib" / "ot_sync_bits.sv"
    sync_level = RTL / "lib" / "ot_sync_level.sv"
    checks = [
        ("ATTR-FIFO-GRAY-W", fifo, r"async_reg\s*=\s*\"true\"[^;]*rd_gray_w1\s*,\s*rd_gray_w2"),
        ("ATTR-FIFO-GRAY-R", fifo, r"async_reg\s*=\s*\"true\"[^;]*wr_gray_r1\s*,\s*wr_gray_r2"),
        ("ATTR-FIFO-ONLINE-W", fifo, r"async_reg\s*=\s*\"true\"[^;]*rd_online_w1\s*,\s*rd_online_w2"),
        ("ATTR-FIFO-ONLINE-R", fifo, r"async_reg\s*=\s*\"true\"[^;]*wr_online_r1\s*,\s*wr_online_r2"),
        ("GRAY-WR-EQUATION", fifo, r"wr_gray_next\s*=\s*\(wr_bin_next\s*>>\s*1\)\s*\^\s*wr_bin_next"),
        ("GRAY-RD-EQUATION", fifo, r"rd_gray_next\s*=\s*\(rd_bin_next\s*>>\s*1\)\s*\^\s*rd_bin_next"),
        ("FIFO-COUPLED-RESET", fifo, r"fifo_async_rst_n\s*=\s*wr_rst_n\s*&&\s*rd_rst_n"),
        ("FIFO-WR-RENDEZVOUS", fifo, r"wr_ready\s*=\s*wr_domain_rst_n\s*&&\s*rd_online_w2\s*&&\s*!wr_full"),
        ("FIFO-RD-RENDEZVOUS", fifo, r"rd_valid\s*=\s*rd_domain_rst_n\s*&&\s*wr_online_r2\s*&&\s*!rd_empty"),
        ("ATTR-MAILBOX-ACK", mailbox, r"async_reg\s*=\s*\"true\"[^;]*ack_sync1\s*,\s*ack_sync2"),
        ("ATTR-MAILBOX-REQUEST", mailbox, r"async_reg\s*=\s*\"true\"[^;]*request_sync1\s*,\s*request_sync2"),
        ("ATTR-MAILBOX-DST-ONLINE", mailbox, r"async_reg\s*=\s*\"true\"[^;]*dst_online_sync1\s*,\s*dst_online_sync2"),
        ("ATTR-MAILBOX-SRC-ONLINE", mailbox, r"async_reg\s*=\s*\"true\"[^;]*src_online_sync1\s*,\s*src_online_sync2"),
        ("MAILBOX-SRC-ONLINE-GATE", mailbox, r"src_ready\s*=\s*source_online\s*&&\s*dst_online_sync2"),
        ("MAILBOX-DST-ONLINE-GATE", mailbox, r"dst_valid\s*=\s*destination_valid\s*&&\s*src_online_sync2\s*&&\s*request_sync2"),
        ("MAILBOX-REQUEST-CAPTURE", mailbox, r"payload_hold\s*<=\s*src_data;\s*request_level\s*<=\s*1'b1"),
        ("MAILBOX-RESPONSE-CAPTURE", mailbox, r"response_hold\s*<=\s*dst_response;.*acknowledge_level\s*<=\s*1'b1"),
        ("ATTR-SYNC-BITS-1", sync_bits, r"async_reg\s*=\s*\"true\"[^;]*sync_ff1"),
        ("ATTR-SYNC-BITS-2", sync_bits, r"async_reg\s*=\s*\"true\"[^;]*sync_ff2"),
        ("ATTR-SYNC-LEVEL-1", sync_level, r"async_reg\s*=\s*\"true\"[^;]*sync_ff1"),
        ("ATTR-SYNC-LEVEL-2", sync_level, r"async_reg\s*=\s*\"true\"[^;]*sync_ff2"),
        ("ATTR-RESET-PIPE", reset_sync, r"async_reg\s*=\s*\"true\"[^;]*reset_pipe"),
        ("RESET-ASYNC-ASSERT", reset_sync, r"always\s*@\(posedge\s+clk\s+or\s+negedge\s+async_rst_n\)"),
        ("RESET-SYNC-RELEASE", reset_sync, r"reset_pipe\s*<=\s*\{reset_pipe\[ASYNC_STAGES-2:0\],\s*1'b1\}"),
    ]
    records, errors = require_patterns(checks)

    mailbox_text = mailbox.read_text(encoding="utf-8")
    for signal, expected_count in (("payload_hold", 2), ("response_hold", 2)):
        count = len(re.findall(rf"\b{signal}\s*<=", mailbox_text))
        check_id = f"MAILBOX-{signal.upper()}-ASSIGNMENT-COUNT"
        status = "pass" if count == expected_count else "fail"
        records.append({"id": check_id, "status": status, "path": str(mailbox.relative_to(ROOT))})
        if status == "fail":
            errors.append(
                f"{signal} has {count} procedural assignments; expected reset plus one capture"
            )
    return records, errors


def rom_read_only_checks() -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for relative in ("rtl/via_mask_rom.sv", "rtl/ot_rom_wrapper.sv"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        start = text.index("module ")
        end = text.index(");", start)
        header = text[start : end + 2]
        write_ports = sorted(
            set(
                re.findall(
                    r"\binput\s+(?:wire|reg|logic)\s+(?:\[[^\]]+\]\s+)?"
                    r"([A-Za-z_][A-Za-z0-9_]*(?:write|wdata|we|wen|wr_)[A-Za-z0-9_]*)",
                    header,
                    flags=re.IGNORECASE,
                )
            )
        )
        memory_writes = re.findall(r"(?m)^\s*mem\s*\[[^\]]+\]\s*(?:<=|=)", text)
        status = "pass" if not write_ports and not memory_writes else "fail"
        records.append(
            {
                "path": relative,
                "status": status,
                "write_ports": write_ports,
                "procedural_memory_writes": len(memory_writes),
            }
        )
        if write_ports:
            errors.append(f"{relative}: immutable ROM has write-like ports {write_ports}")
        if memory_writes:
            errors.append(f"{relative}: immutable ROM storage is procedurally assigned")
    package_imports = []
    for source in SOURCES:
        if source == "rtl/lib/ot_crc_pkg.sv":
            continue
        text = (ROOT / source).read_text(encoding="utf-8")
        if re.search(r"\bimport\s+ot_crc_pkg::", text):
            package_imports.append(source)
    records.append(
        {
            "path": "rtl/lib/ot_crc_pkg.sv",
            "status": "pass" if not package_imports else "fail",
            "synthesizable_importers": package_imports,
        }
    )
    if package_imports:
        errors.append(
            "Yosys-excluded ot_crc_pkg is imported by synthesizable sources: "
            + ", ".join(package_imports)
        )
    return records, errors


def parse_frontend_findings(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    findings: list[dict[str, Any]] = []
    yosys_memory: list[str] = []
    for case in cases:
        output = case["output"]
        if case["name"].startswith("verilator"):
            for line in output.splitlines():
                match = re.match(r"%Warning-([A-Z0-9_]+):\s+([^:]+):(\d+):(.*)", line)
                if match:
                    category, path, line_no, message = match.groups()
                    normalized_path = path if path.startswith("rtl/") else f"rtl/{path}"
                    findings.append(
                        {
                            "tool": "verilator",
                            "category": category.lower(),
                            "path": normalized_path,
                            "line": int(line_no),
                            "message": normalize_space(message),
                            "match_text": f"{normalized_path}:{line_no}: {normalize_space(message)}",
                            "case": case["name"],
                        }
                    )
        elif case["name"].startswith("iverilog"):
            for line in output.splitlines():
                match = re.match(r"([^:]+):(\d+): warning: (.*)$", line.strip())
                if match:
                    path, line_no, message = match.groups()
                    normalized_path = path if path.startswith("rtl/") else f"rtl/{path}"
                    category = (
                        "array_sensitivity"
                        if "@* is sensitive to all" in message
                        else "warning"
                    )
                    full = f"{normalized_path}:{line_no}: warning: {message}"
                    findings.append(
                        {
                            "tool": "iverilog",
                            "category": category,
                            "path": normalized_path,
                            "line": int(line_no),
                            "message": message,
                            "match_text": full,
                            "case": case["name"],
                        }
                    )
        elif case["name"].startswith("yosys"):
            for line in output.splitlines():
                if line.startswith("Warning: Replacing memory "):
                    yosys_memory.append(line)
                elif line.startswith("Warning:"):
                    findings.append(
                        {
                            "tool": "yosys",
                            "category": "warning",
                            "path": None,
                            "line": None,
                            "message": line[len("Warning:") :].strip(),
                            "match_text": line,
                            "case": case["name"],
                        }
                    )
    findings.append(
        {
            "tool": "yosys",
            "category": "frontend_exclusion",
            "path": "rtl/lib/ot_crc_pkg.sv",
            "line": None,
            "message": (
                "excluded from Yosys 0.9 structural elaboration because that frontend "
                "cannot parse SystemVerilog package functions"
            ),
            "match_text": (
                "rtl/lib/ot_crc_pkg.sv: excluded from Yosys 0.9 structural elaboration "
                "because that frontend cannot parse SystemVerilog package functions"
            ),
            "case": "yosys_stage_check",
        }
    )
    return findings, sorted(set(yosys_memory))


def apply_waivers(
    findings: list[dict[str, Any]], waiver_doc: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    errors: list[str] = []
    today = dt.date.today()
    waivers = waiver_doc.get("waivers", [])
    required = {
        "id",
        "tool",
        "category",
        "match_regex",
        "scope",
        "owner",
        "risk",
        "rationale",
        "compensating_check",
        "requirements",
        "review_date",
        "expires",
        "reentry_condition",
    }
    ids: set[str] = set()
    valid: list[dict[str, Any]] = []
    for waiver in waivers:
        missing = sorted(required - set(waiver))
        waiver_id = waiver.get("id", "?")
        if missing:
            errors.append(f"waiver {waiver_id} missing: {', '.join(missing)}")
            continue
        if waiver_id in ids:
            errors.append(f"duplicate waiver ID {waiver_id}")
        ids.add(waiver_id)
        if not waiver["owner"].strip():
            errors.append(f"waiver {waiver_id} has no owner")
        try:
            expiry = dt.date.fromisoformat(waiver["expires"])
            review = dt.date.fromisoformat(waiver["review_date"])
        except ValueError:
            errors.append(f"waiver {waiver_id} has an invalid ISO date")
            continue
        if review > expiry:
            errors.append(f"waiver {waiver_id} review date is after expiration")
        if today > expiry:
            errors.append(f"waiver {waiver_id} expired on {expiry.isoformat()}")
        try:
            re.compile(waiver["match_regex"])
        except re.error as exc:
            errors.append(f"waiver {waiver_id} regex is invalid: {exc}")
            continue
        valid.append(waiver)

    used: set[str] = set()
    classified: list[dict[str, Any]] = []
    for finding in findings:
        matches = [
            waiver
            for waiver in valid
            if waiver["tool"] == finding["tool"]
            and waiver["category"] == finding["category"]
            and re.fullmatch(waiver["match_regex"], finding["match_text"])
        ]
        record = dict(finding)
        if len(matches) == 1:
            waiver = matches[0]
            record["disposition"] = "waived"
            record["waiver_id"] = waiver["id"]
            used.add(waiver["id"])
        elif not matches:
            record["disposition"] = "unowned"
            record["waiver_id"] = None
            errors.append(f"unowned {finding['tool']} finding: {finding['match_text']}")
        else:
            record["disposition"] = "ambiguous"
            record["waiver_id"] = None
            errors.append(
                f"finding matches multiple waivers {', '.join(w['id'] for w in matches)}: "
                f"{finding['match_text']}"
            )
        classified.append(record)
    unused = sorted(ids - used)
    if unused:
        errors.append(f"stale/unused waivers: {', '.join(unused)}")
    return classified, errors, sorted(used)


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Public-tool RTL static, CDC, and RDC campaign",
        "",
        f"**Overall status:** {summary['status'].upper()}",
        "",
        "This campaign closes the checked public RTL against the recorded open-tool "
        "policy. It does not replace target-qualified lint, CDC/RDC, UPF, macro, PDK, "
        "or foundry signoff.",
        "",
        "## Frontends and structural checks",
        "",
        "| Case | Result |",
        "|---|---|",
    ]
    for case in summary["tool_cases"]:
        lines.append(f"| `{case['name']}` | {case['status'].upper()} |")
    lines.extend(
        [
            "",
            "## Inventory and crossing closure",
            "",
            f"- Synthesizable RTL/package files inventoried: {summary['inventory']['source_count']}",
            f"- Declared modules inventoried: {summary['inventory']['module_count']}",
            f"- Stage-top ports classified: {summary['manifest']['classified_port_count']}/"
            f"{summary['manifest']['top_port_count']}",
            f"- Explicit CDC/RDC crossings mapped: {summary['manifest']['crossing_count']}",
            f"- Source structural invariants passed: {summary['structural']['passed']}/"
            f"{summary['structural']['total']}",
            f"- Immutable ROM wrappers with no write path: {summary['rom_read_only']['passed']}/"
            f"{summary['rom_read_only']['total']}",
            "",
            "The structural invariant set checks synchronizer attributes, binary-reflected "
            "Gray equations, coupled FIFO reset and online rendezvous, four-phase mailbox "
            "request/acknowledge/online structure, stable payload assignment topology, and "
            "asynchronous-assert/synchronous-release reset conditioning.",
            "",
            "## Findings and waivers",
            "",
            "| Tool | Category | Location | Disposition | Waiver |",
            "|---|---|---|---|---|",
        ]
    )
    for finding in summary["findings"]:
        location = finding["path"] or "tool output"
        if finding.get("line"):
            location += f":{finding['line']}"
        lines.append(
            f"| {finding['tool']} | {finding['category']} | `{location}` | "
            f"{finding['disposition']} | `{finding.get('waiver_id') or 'none'}` |"
        )
    if not summary["findings"]:
        lines.append("| — | — | — | no findings | — |")
    lines.extend(
        [
            "",
            f"Owned waivers consumed: {len(summary['used_waivers'])}. Unowned, ambiguous, "
            "expired, and stale waivers are campaign failures. Icarus unpacked-array "
            "sensitivity expansion notices are retained in evidence rather than hidden. "
            "Yosys memory-to-register lowering messages are recorded as transformations, "
            "then the lowered netlist must pass `check -assert`.",
            "",
            "## Evidence boundary",
            "",
            "- Verilator and Icarus are independent parser/elaboration frontends; Yosys is "
            "the independent structural netlist frontend.",
            "- The installed Yosys 0.9 cannot parse package functions. The unused CRC package "
            "is independently parsed by both language frontends, guarded against synthesis "
            "imports, and covered by an expiring waiver.",
            "- CDC/RDC source checks prove declared topology, not metastability MTBF, physical "
            "placement, reconvergence timing, or target library cell usage.",
            "- Open-tool results are pre-NDA methodology evidence only.",
            "",
            "## Source hashes",
            "",
        ]
    )
    for path, digest in summary["source_sha256"].items():
        lines.append(f"- `{path}`: `{digest}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    missing = [name for name in ("verilator", "iverilog", "yosys") if shutil.which(name) is None]
    if missing:
        print(f"missing required static tools: {', '.join(missing)}", file=sys.stderr)
        return 2

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    waiver_doc = json.loads(WAIVER_PATH.read_text(encoding="utf-8"))
    inventory, inventory_errors = parse_modules_and_clock_resets(SOURCES)
    manifest_record, manifest_errors = check_manifest(manifest)
    structural_records, structural_errors = structural_checks()
    rom_records, rom_errors = rom_read_only_checks()

    verilator_base = ["verilator", "--lint-only", "-Wall", "-Wno-fatal"]
    iverilog_base = ["iverilog", "-g2012", "-Wall", "-t", "null"]
    stage_parameters = (
        "hierarchy -check -top ot_stage_top "
        "-chparam SESSION_ENTRIES 4 -chparam CREDIT_SINKS 2 "
        "-chparam CREDIT_DEPTH 2 -chparam CMD_FIFO_DEPTH 4 "
        "-chparam RSP_FIFO_DEPTH 4 -chparam TELEM_FIFO_DEPTH 4 "
        "-chparam SCHEDULE_SLOTS 4"
    )
    yosys_read = "read_verilog -sv " + " ".join(YOSYS_SOURCES)
    cases = [
        run_case(
            "verilator_stage_strict",
            verilator_base + ["--top-module", "ot_stage_top", *SOURCES],
        ),
        run_case(
            "verilator_legacy_strict",
            verilator_base
            + [
                "--top-module",
                "opentallas_tile",
                "rtl/expert_mask_controller.sv",
                "rtl/via_mask_rom.sv",
                "rtl/rom_mac_tile.sv",
                "rtl/opentallas_tile.sv",
            ],
        ),
        run_case(
            "iverilog_stage_elaboration",
            iverilog_base + ["-s", "ot_stage_top", *SOURCES],
        ),
        run_case(
            "iverilog_legacy_elaboration",
            iverilog_base
            + [
                "-s",
                "opentallas_tile",
                "rtl/expert_mask_controller.sv",
                "rtl/via_mask_rom.sv",
                "rtl/rom_mac_tile.sv",
                "rtl/opentallas_tile.sv",
            ],
        ),
        run_case(
            "yosys_stage_check",
            [
                "yosys",
                "-q",
                "-p",
                f"{yosys_read}; {stage_parameters}; proc; opt; memory_dff; "
                "memory_collect; check -assert",
            ],
            timeout=300,
        ),
        run_case(
            "yosys_legacy_check",
            [
                "yosys",
                "-q",
                "-p",
                "read_verilog -sv rtl/expert_mask_controller.sv rtl/via_mask_rom.sv "
                "rtl/rom_mac_tile.sv rtl/opentallas_tile.sv; "
                "hierarchy -check -top opentallas_tile; proc; opt; memory_dff; "
                "memory_collect; check -assert",
            ],
        ),
    ]
    findings, memory_observations = parse_frontend_findings(cases)
    classified, waiver_errors, used_waivers = apply_waivers(findings, waiver_doc)

    errors = (
        inventory_errors
        + manifest_errors
        + structural_errors
        + rom_errors
        + waiver_errors
    )
    failed_cases = [case["name"] for case in cases if case["status"] != "pass"]
    if failed_cases:
        errors.append(f"tool cases failed: {', '.join(failed_cases)}")
    passed = not errors

    public_cases = [
        {key: value for key, value in case.items() if key != "output"}
        for case in cases
    ]
    source_manifest = sorted(
        set(SOURCES)
        | {
            "tools/rtl_static.py",
            "spec/clock_reset_crossings.json",
            "spec/rtl_waivers.json",
            "spec/CLOCK_RESET_POWER.md",
            "spec/INTERFACES.md",
            "spec/VERIFICATION_PLAN.md",
        }
    )
    summary: dict[str, Any] = {
        "schema_version": 1,
        "campaign": "rtl_static_cdc_rdc",
        "status": "pass" if passed else "fail",
        "evidence_class": "public_open_tool_structural_proxy",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "tools": {
            "verilator": tool_version(["verilator", "--version"]),
            "iverilog": tool_version(["iverilog", "-V"]),
            "yosys": tool_version(["yosys", "-V"]),
        },
        "inventory": {
            "source_count": len(inventory),
            "module_count": sum(len(item["modules"]) for item in inventory),
            "sources": inventory,
        },
        "manifest": manifest_record,
        "crossings": manifest["crossings"],
        "resets": manifest["resets"],
        "structural": {
            "total": len(structural_records),
            "passed": sum(item["status"] == "pass" for item in structural_records),
            "checks": structural_records,
        },
        "rom_read_only": {
            "total": len(rom_records),
            "passed": sum(item["status"] == "pass" for item in rom_records),
            "checks": rom_records,
        },
        "tool_cases": public_cases,
        "findings": classified,
        "used_waivers": used_waivers,
        "yosys_memory_lowering_observations": memory_observations,
        "errors": errors,
        "source_sha256": {
            path: sha256_file(ROOT / path) for path in source_manifest
        },
        "limitations": [
            "public structural CDC/RDC checks are not target-qualified signoff",
            "Yosys stage structural elaboration uses explicitly recorded reduced parameters",
            "Yosys 0.9 package-function parsing is covered by an expiring exact waiver",
            "physical synchronizer placement, MTBF, UPF, and PDK timing remain external",
        ],
    }
    (RESULTS / "static_campaign.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (RESULTS / "STATIC_REPORT.md").write_text(render_report(summary), encoding="utf-8")
    print(f"static campaign: {summary['status'].upper()}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
