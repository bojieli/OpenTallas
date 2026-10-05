#!/usr/bin/env python3
"""Run the governed IHP SG13G2 controlled-via ROM physical replication.

The shared parsers are imported from the already governed SKY130 runner so the
two experiments apply the same topology, geometry, LVS, and capacitance gates.
PDK discovery, identity, archival paths, and claim text remain IHP-specific.
No open-PDK result is scaled to N7 or N4.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

import run_sky130_physical as common


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "spice" / "ihp_sg13g2" / "rom_slice" / "physical_contract.json"
)
PDK_VERIFIER = ROOT / "tools" / "verify_ihp_pdk.py"


class IhpPhysicalError(RuntimeError):
    """An IHP physical input, identity, or acceptance gate failed."""


def repository_path(value: str) -> Path:
    try:
        return common.repository_path(value)
    except common.PhysicalExperimentError as exc:
        raise IhpPhysicalError(str(exc)) from exc


def validate_contract(contract: dict[str, Any], lock: dict[str, Any]) -> None:
    if contract.get("schema_version") != 1:
        raise IhpPhysicalError("physical contract schema_version must be 1")
    if contract.get("experiment_id") != "ihp_sg13g2_via_rom_physical_v1":
        raise IhpPhysicalError("unexpected IHP physical experiment_id")
    if lock.get("schema_version") != 1:
        raise IhpPhysicalError("IHP PDK lock schema_version must be 1")
    if lock.get("pdk", {}).get("variant") != "ihp-sg13g2":
        raise IhpPhysicalError("physical replication requires IHP SG13G2")
    if repository_path(contract["pdk_lock"]) != repository_path(
        "configs/pdk/ihp_sg13g2_physical_lock.json"
    ):
        raise IhpPhysicalError("physical contract must use the governed IHP lock")

    inputs = contract.get("inputs", {})
    if set(inputs) != {"generator", "schematic"}:
        raise IhpPhysicalError("physical contract must name generator and schematic")
    for value in inputs.values():
        if not repository_path(value).is_file():
            raise IhpPhysicalError(f"missing governed physical input: {value}")

    ports = contract.get("top_ports")
    if not isinstance(ports, list) or len(ports) != 10 or len(set(ports)) != 10:
        raise IhpPhysicalError("physical contract must declare ten unique ports")
    acceptance = contract.get("acceptance", {})
    if acceptance.get("drc_errors_max") != 0:
        raise IhpPhysicalError("zero full-style DRC errors is mandatory")
    if acceptance.get("lvs_final_result") != "Circuits match uniquely.":
        raise IhpPhysicalError("a unique port-complete LVS match is mandatory")
    if acceptance.get("programming_via1", {}).get("expected_delta") != 1:
        raise IhpPhysicalError("exactly one programming-via delta is mandatory")

    boundary = contract.get("claim_boundary", {})
    if (
        boundary.get("evidence_class")
        != "open_pdk_independent_drc_lvs_and_extraction"
        or boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("establishes")
        or not boundary.get("forbidden_inferences")
    ):
        raise IhpPhysicalError("IHP physical claim boundary is incomplete")
    forbidden = " ".join(boundary["forbidden_inferences"])
    for marker in ("N7", "N4", "GPU speedup", "silicon"):
        if marker not in forbidden:
            raise IhpPhysicalError(f"claim boundary does not cover {marker}")

    reports = contract.get("reports", {})
    if set(reports) != {"artifacts", "json", "markdown"}:
        raise IhpPhysicalError("physical report destinations are incomplete")
    for value in reports.values():
        repository_path(value)


def first_existing(candidates: list[Path], description: str) -> Path:
    checked: list[str] = []
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        checked.append(str(resolved))
        if resolved.exists():
            return resolved
    raise IhpPhysicalError(f"cannot find {description}; checked {checked}")


def locate_pdk(explicit: Path | None) -> tuple[Path, Path]:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    override = os.environ.get("OPENTALLAS_IHP_PDK_ROOT")
    if override:
        candidates.append(Path(override))
    candidates.extend(
        [
            ROOT / ".cache" / "ihp-open-pdk-v0.3.0",
            Path.home() / ".local" / "opentallas-pdk" / "ihp-open-pdk-v0.3.0",
        ]
    )
    selected = first_existing(candidates, "pinned IHP Open PDK v0.3.0")
    root = selected.parent if selected.name == "ihp-sg13g2" else selected
    variant = root / "ihp-sg13g2"
    required = [
        variant / "libs.tech" / "magic" / "ihp-sg13g2.magicrc",
        variant / "libs.tech" / "netgen" / "ihp-sg13g2_setup.tcl",
        variant / "libs.tech" / "magic" / "ihp-sg13g2-extract.tech",
    ]
    if not all(path.is_file() for path in required):
        raise IhpPhysicalError(f"incomplete IHP physical collateral under {root}")
    return root, variant


def verify_pdk(pdk: Path, variant: Path, lock: dict[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        ["python3", str(PDK_VERIFIER), str(pdk)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    if completed.returncode != 0:
        raise IhpPhysicalError(f"IHP PDK tree verification failed:\n{completed.stdout}")
    try:
        observed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise IhpPhysicalError(f"invalid IHP verifier output: {completed.stdout}") from exc
    if observed.get("status") != "pass":
        raise IhpPhysicalError(f"IHP PDK verifier did not pass: {observed}")
    expected = lock["pdk"]["installed_tree"]
    tree = observed["tree"]
    for key in (
        "regular_files",
        "symlinks",
        "gitlinks",
        "payload_entries",
        "semantic_records",
        "payload_bytes",
        "manifest_sha256",
    ):
        if tree.get(key) != expected.get(key):
            raise IhpPhysicalError(f"IHP verified tree mismatch for {key}")
    return {
        "family": lock["pdk"]["family"],
        "variant": lock["pdk"]["variant"],
        "release": lock["pdk"]["release"],
        "commit": observed["root_commit"],
        "root": str(pdk),
        "submodules": observed["submodules"],
        "tree": tree,
        "magic_deck_sha256": common.sha256_file(
            variant / "libs.tech" / "magic" / "ihp-sg13g2.tech"
        ),
        "magic_drc_sha256": common.sha256_file(
            variant / "libs.tech" / "magic" / "ihp-sg13g2-drc.tech"
        ),
        "magic_extract_sha256": common.sha256_file(
            variant / "libs.tech" / "magic" / "ihp-sg13g2-extract.tech"
        ),
        "netgen_setup_sha256": common.sha256_file(
            variant / "libs.tech" / "netgen" / "ihp-sg13g2_setup.tcl"
        ),
    }


def archive_files(build: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    destination = repository_path(contract["reports"]["artifacts"])
    expected_destination = repository_path(
        "results/spice/ihp_sg13g2_physical/artifacts"
    )
    if destination != expected_destination:
        raise IhpPhysicalError(f"refusing unexpected artifact destination {destination}")
    required = [build / name for name in sorted(set(contract["artifacts"]))]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise IhpPhysicalError(f"missing IHP physical artifacts: {missing}")
    generated = sorted({*build.glob("*.mag"), *build.glob("*.ext")})
    sources = sorted({*required, *generated}, key=lambda path: path.name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="artifacts.staging.", dir=destination.parent))
    try:
        for source in sources:
            shutil.copy2(source, staging / source.name)
        if destination.exists():
            shutil.rmtree(destination)
        staging.replace(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": common.sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(destination.iterdir())
        if path.is_file()
    ]


def markdown_report(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    caps = metrics["parasitics"]
    boundary = result["claim_boundary"]
    lines = [
        "# IHP SG13G2 controlled-via ROM physical replication",
        "",
        f"**Status:** **{result['status'].upper()}**  ",
        "**Evidence class:** independent public-PDK DRC, LVS, and capacitance extraction; not silicon  ",
        f"**PDK:** `{result['pdk']['variant']}` / `{result['pdk']['release']}` / `{result['pdk']['commit']}`  ",
        f"**Magic:** `{result['toolchain']['magic']['version']}` / `{result['toolchain']['magic']['commit']}`  ",
        f"**Netgen:** `{result['toolchain']['netgen']['version']}`",
        "",
        "## Closed gates",
        "",
        f"- Magic `drc(full)`: **{result['verification']['drc']['errors']} errors**.",
        f"- Netgen LVS: **{result['verification']['lvs']['final_result']}**",
        f"- Extracted topology: **{metrics['topology']['device_count']} MOS devices, {metrics['topology']['net_count']} nets, {len(metrics['topology']['ports'])} ports**.",
        f"- Programming geometry: present column has {metrics['layout']['programming_via1']['present_column_count']} top-level via1 shapes; absent column has {metrics['layout']['programming_via1']['absent_column_count']}; delta **1**.",
        f"- PEX: **{caps['capacitance_element_count']} capacitance elements** ({caps['nonzero_capacitance_element_count']} nonzero), totaling {caps['total_extracted_capacitance_ff']:.6g} fF.",
        "",
        "The layout uses IHP's native `sg13_lv_nmos` and `sg13_lv_pmos`",
        "generators. Device-terminal vias are disabled, legal remote landing sites",
        "are routed explicitly, and the lower row-drain via exists only in the",
        "programmed column. The unprogrammed row retains `ROM_DRAIN_ABSENT` as a",
        "distinct extracted node rather than silently joining `BL_ABSENT`.",
        "",
        "## Local geometry and parasitics",
        "",
        f"The fixed demonstration footprint is {metrics['layout']['bbox_um'][2]:.3f} × {metrics['layout']['bbox_um'][3]:.3f} µm = {metrics['layout']['footprint_area_um2']:.3f} µm².",
        "It is deliberately roomy and is **not a ROM-cell density macro**.",
        "",
        "| Net | Incident extracted capacitance |",
        "|---|---:|",
    ]
    for node, value in caps["incident_capacitance_ff"].items():
        lines.append(f"| `{node}` | {value:.6g} fF |")
    lines.extend(
        [
            "",
            "Detailed distributed resistance and extracted electrical PVT/load",
            "behavior are separate gates; this run closes base capacitance extraction.",
            "",
            "## Scientific interpretation",
            "",
            "This is an independent foundry-PDK replication of the controlled-via",
            "method, not a feature-size scaling exercise. Agreement with SKY130 would",
            "reduce the chance that topology legality is a SKY130-deck artifact; it",
            "still would not characterize an N7/N4 product.",
            "",
        ]
    )
    lines.extend(f"- Establishes: {item}." for item in boundary["establishes"])
    lines.append("")
    lines.extend(f"- Does not establish: {item}." for item in boundary["forbidden_inferences"])
    lines.extend(
        [
            "",
            "## Reproduction",
            "",
            "```bash",
            "python3 tools/run_ihp_physical.py",
            "```",
            "",
            "The machine-readable result records the exact PDK tree, tool binaries,",
            "inputs, decks, and archived output hashes.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(contract: dict[str, Any], result: dict[str, Any]) -> None:
    json_path = repository_path(contract["reports"]["json"])
    markdown_path = repository_path(contract["reports"]["markdown"])
    json_path.parent.mkdir(parents=True, exist_ok=True)
    result["reports"] = dict(contract["reports"])
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(result), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tool-root", type=Path)
    parser.add_argument("--magic", type=Path)
    parser.add_argument("--netgen", type=Path)
    parser.add_argument("--keep-build", action="store_true")
    args = parser.parse_args()

    build: Path | None = None
    try:
        contract = common.strict_json(CONTRACT_PATH)
        lock = common.strict_json(repository_path(contract["pdk_lock"]))
        validate_contract(contract, lock)
        if args.validate_only:
            print("PASS: IHP physical contract and no-scaling boundary")
            return 0

        pdk, variant = locate_pdk(args.pdk_root)
        magic, netgen = common.locate_tools(
            lock, args.tool_root, args.magic, args.netgen
        )
        pdk_identity = verify_pdk(pdk, variant, lock)
        identities = common.tool_identities(magic, netgen, lock)

        build_parent = ROOT / "spice" / "build"
        build_parent.mkdir(parents=True, exist_ok=True)
        build = Path(tempfile.mkdtemp(prefix="ihp_sg13g2_rom_physical.", dir=build_parent))
        input_records: dict[str, Any] = {}
        for name, relative in contract["inputs"].items():
            source = repository_path(relative)
            shutil.copy2(source, build / source.name)
            input_records[name] = {
                "path": relative,
                "sha256": common.sha256_file(source),
                "size_bytes": source.stat().st_size,
            }

        environment = os.environ.copy()
        environment.update(
            {
                "LC_ALL": "C",
                "PDK_ROOT": str(pdk),
                "TZ": "UTC",
            }
        )
        magic_log = build / "magic.log"
        magic_output = common.run_checked(
            [
                str(magic),
                "-dnull",
                "-noconsole",
                "-rcfile",
                str(variant / "libs.tech" / "magic" / "ihp-sg13g2.magicrc"),
                Path(contract["inputs"]["generator"]).name,
            ],
            cwd=build,
            log=magic_log,
            env=environment,
        )
        drc = common.parse_magic(magic_output, contract["acceptance"]["drc_errors_max"])

        top = contract["top_cell"]
        netgen_stdout = build / "netgen.stdout"
        common.run_checked(
            [
                str(netgen),
                "-batch",
                "lvs",
                f"{top}.extracted.spice {top}",
                f"{Path(contract['inputs']['schematic']).name} {top}",
                str(variant / "libs.tech" / "netgen" / "ihp-sg13g2_setup.tcl"),
                "lvs.log",
            ],
            cwd=build,
            log=netgen_stdout,
        )
        lvs_log = build / "lvs.log"
        if not lvs_log.is_file():
            raise IhpPhysicalError("Netgen did not create the IHP LVS log")
        lvs = common.parse_lvs(
            lvs_log.read_text(encoding="utf-8", errors="replace"),
            contract["acceptance"]["lvs_final_result"],
        )
        topology = common.parse_extracted_topology(
            build / f"{top}.extracted.spice", contract
        )
        layout = common.parse_mag(build / f"{top}.mag", contract)
        parasitics = common.parse_pex(build / f"{top}.pex.spice")
        artifacts = archive_files(build, contract)

        result = {
            "schema_version": 1,
            "experiment_id": contract["experiment_id"],
            "status": "pass",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "contract": {
                "path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
                "sha256": common.sha256_file(CONTRACT_PATH),
            },
            "inputs": input_records,
            "pdk": pdk_identity,
            "toolchain": identities,
            "verification": {"drc": drc, "lvs": lvs},
            "metrics": {
                "layout": layout,
                "topology": topology,
                "parasitics": parasitics,
            },
            "artifacts": artifacts,
            "claim_boundary": contract["claim_boundary"],
        }
        write_reports(contract, result)
        print(
            "PASS: IHP SG13G2 physical ROM replication; "
            f"DRC={drc['errors']}, LVS={lvs['final_result']}, "
            f"via1={layout['programming_via1']['present_column_count']}/"
            f"{layout['programming_via1']['absent_column_count']}"
        )
        return 0
    except (IhpPhysicalError, common.PhysicalExperimentError, OSError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}")
        return 1
    finally:
        if build is not None and build.exists():
            if args.keep_build:
                print(f"Kept build directory: {build}")
            else:
                shutil.rmtree(build)


if __name__ == "__main__":
    raise SystemExit(main())
