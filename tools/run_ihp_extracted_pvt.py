#!/usr/bin/env python3
"""Run deterministic PVT/load cases on the archived IHP SG13G2 PEX slice."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import product
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "spice" / "ihp_sg13g2" / "rom_slice" / "extracted_pvt_contract.json"
)
PDK_VERIFIER = ROOT / "tools" / "verify_ihp_pdk.py"
BUILD = ROOT / "spice" / "build" / "ihp_sg13g2_extracted_pvt"
MEASURE_NAMES = (
    "v_present",
    "v_absent",
    "v_masked",
    "sense_present_v",
    "sense_absent_v",
    "sense_masked_v",
    "read_margin",
    "discharge_delay",
    "read_energy",
    "inactive_leakage",
)
MEASURE_RE = re.compile(
    r"(?m)^\s*({})\s*=\s*([-+0-9.eE]+)".format("|".join(MEASURE_NAMES))
)
WARNING_RE = re.compile(r"(?mi)^\s*warning:\s*(.+)$")
EXPECTED_BENIGN_WARNINGS = {
    "vpre: no DC value, transient time 0 value used",
    "vwl: no DC value, transient time 0 value used",
    "m=xx on .subckt line will override multiplier m hierarchy!",
}


class IhpPvtError(RuntimeError):
    """A governed IHP extracted-circuit input or acceptance gate failed."""


def strict_json(path: Path) -> Any:
    duplicates: list[str] = []

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, child in items:
            if key in value:
                duplicates.append(key)
            value[key] = child
        return value

    try:
        parsed = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    except (OSError, json.JSONDecodeError) as exc:
        raise IhpPvtError(f"cannot load {path}: {exc}") from exc
    if duplicates:
        raise IhpPvtError(f"duplicate JSON keys: {sorted(set(duplicates))}")
    return parsed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise IhpPvtError(f"repository path must be contained: {value}")
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise IhpPvtError(f"repository path escapes root: {value}") from exc
    return path


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema_version") != 1:
        raise IhpPvtError("contract schema_version must be 1")
    if contract.get("experiment_id") != "ihp_sg13g2_via_rom_extracted_pvt_v1":
        raise IhpPvtError("unexpected IHP extracted-PVT experiment_id")
    if contract.get("pdk_lock") != "configs/pdk/ihp_sg13g2_physical_lock.json":
        raise IhpPvtError("campaign must use the governed IHP PDK lock")
    dimensions = contract.get("dimensions", {})
    expected = {"process_corner", "vdd_v", "temperature_c", "output_load_ff"}
    if set(dimensions) != expected or dimensions["process_corner"] != ["ss", "tt", "ff"]:
        raise IhpPvtError("incomplete or unordered IHP PVT dimensions")
    for name, values in dimensions.items():
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise IhpPvtError(f"dimension {name} must be a unique non-empty list")
        if name != "process_corner" and any(
            not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in values
        ):
            raise IhpPvtError(f"dimension {name} must be finite numeric values")
        if name in {"vdd_v", "output_load_ff"} and any(value <= 0 for value in values):
            raise IhpPvtError(f"dimension {name} must contain positive values")
        if name == "vdd_v" and any(value >= 1.5 for value in values):
            raise IhpPvtError("IHP LV sweep must stay below the published 1.5-V VDS maximum")
    campaigns = contract.get("campaigns")
    if not isinstance(campaigns, list) or len(campaigns) != 4:
        raise IhpPvtError("four IHP extracted-PVT campaigns are required")
    names: set[str] = set()
    for campaign in campaigns:
        if set(campaign) != {"name", "dimensions", "fixed"}:
            raise IhpPvtError("invalid IHP campaign entry")
        if campaign["name"] in names:
            raise IhpPvtError("campaign names must be unique")
        names.add(campaign["name"])
        swept = set(campaign["dimensions"])
        fixed = set(campaign["fixed"])
        if swept | fixed != expected or swept & fixed:
            raise IhpPvtError(f"campaign {campaign['name']} does not cover dimensions once")
        for key, value in campaign["fixed"].items():
            if value not in dimensions[key]:
                raise IhpPvtError(f"campaign {campaign['name']} fixed value is outside sweep")
    boundary = contract.get("claim_boundary", {})
    if (
        boundary.get("evidence_class")
        != "independent_capacitance_extracted_open_pdk_simulation"
        or boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("establishes")
        or not boundary.get("forbidden_inferences")
    ):
        raise IhpPvtError("claim boundary must prohibit target-node scaling")
    for marker in ("N7", "N4", "GPU speedup", "silicon"):
        if marker not in " ".join(boundary["forbidden_inferences"]):
            raise IhpPvtError(f"claim boundary does not cover {marker}")
    if set(contract.get("inputs", {})) != {
        "physical_result",
        "pex_netlist",
        "spice_init",
        "template",
    }:
        raise IhpPvtError("IHP PVT input set is incomplete")
    for value in contract["inputs"].values():
        if not repo_path(value).is_file():
            raise IhpPvtError(f"missing campaign input: {value}")
    for key, value in contract.get("acceptance", {}).items():
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise IhpPvtError(f"acceptance threshold {key} must be finite")
    if contract["acceptance"].get("unexpected_warnings_max") != 0:
        raise IhpPvtError("unexpected warnings must be fatal")


def generated_cases(contract: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions = contract["dimensions"]
    order = tuple(dimensions)
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    membership: defaultdict[tuple[Any, ...], list[str]] = defaultdict(list)
    for campaign in contract["campaigns"]:
        swept = campaign["dimensions"]
        for values in product(*(dimensions[name] for name in swept)):
            case = dict(campaign["fixed"])
            case.update(dict(zip(swept, values, strict=True)))
            key = tuple(case[name] for name in order)
            by_key[key] = case
            membership[key].append(campaign["name"])
    cases = [
        {
            **by_key[key],
            "campaigns": sorted(membership[key]),
            "case_id": f"case_{index:03d}",
        }
        for index, key in enumerate(sorted(by_key), start=1)
    ]
    if len(cases) != 33:
        raise IhpPvtError(f"campaign must yield 33 unique cases, got {len(cases)}")
    return cases


def locate_pdk(explicit: Path | None) -> Path:
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
    for candidate in candidates:
        root = candidate.expanduser().resolve()
        if root.name == "ihp-sg13g2":
            root = root.parent
        corner = root / "ihp-sg13g2" / "libs.tech" / "ngspice" / "models" / "cornerMOSlv.lib"
        if corner.is_file():
            return root
    raise IhpPvtError(f"cannot locate pinned IHP SG13G2 models: {candidates}")


def locate_tool(explicit: Path | None, env_name: str, default: Path, description: str) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    override = os.environ.get(env_name)
    if override:
        candidates.append(Path(override))
    candidates.append(default)
    for candidate in candidates:
        path = candidate.expanduser().resolve()
        if path.is_file() and os.access(path, os.X_OK):
            return path
    raise IhpPvtError(f"cannot locate {description}: {candidates}")


def verify_pdk(pdk: Path, lock: dict[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        ["python3", str(PDK_VERIFIER), str(pdk)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    if completed.returncode != 0:
        raise IhpPvtError(f"IHP PDK verification failed:\n{completed.stdout}")
    observed = json.loads(completed.stdout)
    expected = lock["pdk"]["installed_tree"]
    if observed.get("status") != "pass" or observed["tree"]["manifest_sha256"] != expected["manifest_sha256"]:
        raise IhpPvtError("IHP PDK semantic identity mismatch")
    return {
        "release": lock["pdk"]["release"],
        "commit": observed["root_commit"],
        "tree_manifest_sha256": observed["tree"]["manifest_sha256"],
    }


def verify_tool(path: Path, expected: dict[str, Any], marker: str) -> dict[str, Any]:
    digest = sha256_file(path)
    size = path.stat().st_size
    if digest != expected["executable_sha256"] or size != expected["executable_size_bytes"]:
        raise IhpPvtError(f"tool identity mismatch: {path}, sha256={digest}, size={size}")
    completed = subprocess.run(
        [str(path), "--version"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0 or marker not in completed.stdout:
        raise IhpPvtError(f"unexpected simulator identity: {completed.stdout}")
    return {
        "path": str(path),
        "sha256": digest,
        "size_bytes": size,
        "version_output": completed.stdout.strip(),
    }


def verify_osdi(root: Path, lock: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for name, expected in lock["osdi_models"]["models"].items():
        path = root / f"{name}.osdi"
        if not path.is_file():
            raise IhpPvtError(f"missing governed OSDI module: {path}")
        digest = sha256_file(path)
        size = path.stat().st_size
        if digest != expected["output_sha256"] or size != expected["output_size_bytes"]:
            raise IhpPvtError(f"OSDI identity mismatch: {path}")
        records.append(
            {"model": name, "path": str(path), "sha256": digest, "size_bytes": size}
        )
    return records


def verify_physical_input(contract: dict[str, Any]) -> dict[str, Any]:
    result_path = repo_path(contract["inputs"]["physical_result"])
    physical = strict_json(result_path)
    if physical.get("status") != "pass":
        raise IhpPvtError("upstream IHP physical experiment did not pass")
    if physical.get("verification", {}).get("drc", {}).get("errors") != 0:
        raise IhpPvtError("upstream IHP full DRC is not clean")
    if physical.get("verification", {}).get("lvs", {}).get("final_result") != "Circuits match uniquely.":
        raise IhpPvtError("upstream IHP LVS is not a unique match")
    pex = repo_path(contract["inputs"]["pex_netlist"])
    archived = {item["path"]: item for item in physical.get("artifacts", [])}.get(
        contract["inputs"]["pex_netlist"]
    )
    if archived is None or archived.get("sha256") != sha256_file(pex):
        raise IhpPvtError("IHP PEX netlist does not match physical artifact manifest")
    return {
        "path": contract["inputs"]["physical_result"],
        "sha256": sha256_file(result_path),
        "experiment_id": physical["experiment_id"],
        "pdk_tree_manifest_sha256": physical["pdk"]["tree"]["manifest_sha256"],
        "pex_path": contract["inputs"]["pex_netlist"],
        "pex_sha256": sha256_file(pex),
    }


def render_deck(template: str, case: dict[str, Any], corner: Path, pex: Path) -> str:
    replacements = {
        "@TEMPERATURE_C@": str(case["temperature_c"]),
        "@CORNER_LIBRARY@": str(corner),
        "@CORNER_SECTION@": f"mos_{case['process_corner']}",
        "@PEX_NETLIST@": str(pex),
        "@VDD_V@": str(case["vdd_v"]),
        "@OUTPUT_LOAD_FF@": str(case["output_load_ff"]),
    }
    rendered = template
    for placeholder, value in replacements.items():
        if rendered.count(placeholder) < 1:
            raise IhpPvtError(f"template must contain {placeholder}")
        rendered = rendered.replace(placeholder, value)
    if re.search(r"@[A-Z0-9_]+@", rendered):
        raise IhpPvtError("unrendered template placeholder remains")
    return rendered


def parse_measures(text: str) -> dict[str, float]:
    found: dict[str, list[float]] = defaultdict(list)
    for match in MEASURE_RE.finditer(text):
        found[match.group(1)].append(float(match.group(2)))
    invalid = {name: values for name, values in found.items() if len(values) != 1}
    missing = set(MEASURE_NAMES) - set(found)
    if missing or invalid:
        raise IhpPvtError(f"measure cardinality failure: missing={sorted(missing)}, invalid={invalid}")
    values = {name: found[name][0] for name in MEASURE_NAMES}
    if any(not math.isfinite(value) for value in values.values()):
        raise IhpPvtError("ngspice emitted non-finite measures")
    return values


def evaluate(case: dict[str, Any], values: dict[str, float], warnings: list[str], contract: dict[str, Any]) -> list[str]:
    threshold = contract["acceptance"]
    vdd = case["vdd_v"]
    checks = (
        (values["v_present"] <= threshold["present_bitline_fraction_max"] * vdd, "selected programmed bitline did not discharge"),
        (values["v_absent"] >= threshold["absent_bitline_fraction_min"] * vdd, "via-absent bitline did not retain high"),
        (values["v_masked"] >= threshold["masked_bitline_fraction_min"] * vdd, "masked programmed bitline did not retain high"),
        (values["read_margin"] >= threshold["read_margin_fraction_min"] * vdd, "dynamic bitline separation is below threshold"),
        (values["sense_present_v"] >= threshold["sense_high_fraction_min"] * vdd, "present sense output did not resolve high"),
        (values["sense_absent_v"] <= threshold["sense_low_fraction_max"] * vdd, "absent sense output did not resolve low"),
        (values["sense_masked_v"] <= threshold["sense_low_fraction_max"] * vdd, "masked sense output did not resolve low"),
        (0 < values["discharge_delay"] <= threshold["discharge_delay_ns_max"] * 1e-9, "discharge delay is outside window"),
        (threshold["read_energy_fj_min"] * 1e-15 < values["read_energy"] <= threshold["read_energy_fj_max"] * 1e-15, "read energy is outside sanity bound"),
        (0 <= values["inactive_leakage"] <= threshold["inactive_leakage_ua_max"] * 1e-6, "inactive leakage is outside sanity bound"),
        (len(warnings) <= threshold["unexpected_warnings_max"], "unexpected ngspice warning observed"),
    )
    return [message for passed, message in checks if not passed]


def run_case(
    case: dict[str, Any],
    contract: dict[str, Any],
    template: str,
    corner: Path,
    pex: Path,
    init: Path,
    executable: Path,
    pdk: Path,
    osdi: Path,
) -> dict[str, Any]:
    case_dir = BUILD / "cases" / case["case_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    deck = case_dir / "read.spice"
    deck.write_text(render_deck(template, case, corner, pex), encoding="utf-8")
    shutil.copy2(init, case_dir / ".spiceinit")
    environment = os.environ.copy()
    environment.update(
        {
            "LC_ALL": "C",
            "OPENTALLAS_IHP_PDK_ROOT": str(pdk),
            "OPENTALLAS_IHP_OSDI_ROOT": str(osdi),
            "TZ": "UTC",
        }
    )
    completed = subprocess.run(
        [str(executable), "-b", deck.name],
        cwd=case_dir,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    log = case_dir / "ngspice.log"
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise IhpPvtError(f"{case['case_id']}: ngspice failed ({completed.returncode})\n{completed.stdout}")
    values = parse_measures(completed.stdout)
    all_warnings = sorted(set(WARNING_RE.findall(completed.stdout)))
    expected = sorted(set(all_warnings) & EXPECTED_BENIGN_WARNINGS)
    warnings = sorted(set(all_warnings) - EXPECTED_BENIGN_WARNINGS)
    errors = [
        line.strip()
        for line in completed.stdout.splitlines()
        if re.match(r"^(Error|Fatal|ERROR|FATAL)(:|\s)", line.strip())
    ]
    if errors:
        raise IhpPvtError(f"{case['case_id']}: unexpected simulator errors: {errors}")
    failures = evaluate(case, values, warnings, contract)
    return {
        **case,
        "deck_sha256": sha256_file(deck),
        "expected_benign_warnings": expected,
        "failures": failures,
        "measures_si": values,
        "metrics": {
            "discharge_delay_ns": values["discharge_delay"] * 1e9,
            "inactive_leakage_ua": values["inactive_leakage"] * 1e6,
            "read_energy_fj": values["read_energy"] * 1e15,
            "read_margin_fraction_vdd": values["read_margin"] / case["vdd_v"],
        },
        "ngspice_log_sha256": sha256_file(log),
        "status": "pass" if not failures else "fail",
        "unexpected_warnings": warnings,
    }


def extremum(cases: list[dict[str, Any]], metric: str, maximum: bool) -> dict[str, Any]:
    selected = (max if maximum else min)(cases, key=lambda case: case["metrics"][metric])
    return {"case_id": selected["case_id"], "value": selected["metrics"][metric]}


def case_label(case: dict[str, Any]) -> str:
    return (
        f"{case['case_id']} ({case['process_corner']}, {case['vdd_v']:.2f} V, "
        f"{case['temperature_c']:.0f} C, {case['output_load_ff']:.0f} fF)"
    )


def markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    by_id = {case["case_id"]: case for case in result["cases"]}

    def describe(extreme: dict[str, Any], unit: str) -> str:
        return f"{extreme['value']:.6g} {unit} — {case_label(by_id[extreme['case_id']])}"

    lines = [
        "# Capacitance-extracted IHP SG13G2 controlled-via ROM PVT campaign",
        "",
        f"**Status:** **{result['status'].upper()}** ({summary['cases_passed']}/{summary['cases_total']} cases passed)  ",
        "**Evidence class:** deterministic simulation of archived IHP PEX with official PSP103 models; not silicon  ",
        f"**Upstream PEX:** `{result['upstream_physical']['pex_sha256']}`  ",
        "**Simulator:** ngspice 43 with pinned OSDI modules",
        "",
        "## Results",
        "",
        "| Limiting metric | Observed case |",
        "|---|---|",
        f"| Minimum dynamic separation / VDD | {describe(summary['min_read_margin_fraction_vdd'], 'V/V')} |",
        f"| Maximum VDD/2 discharge delay | {describe(summary['max_discharge_delay_ns'], 'ns')} |",
        f"| Maximum 0–5 ns supply energy | {describe(summary['max_read_energy_fj'], 'fJ')} |",
        f"| Maximum 6–7 ns RMS supply current | {describe(summary['max_inactive_leakage_ua'], 'µA')} |",
        "",
        "The testbench instantiates two copies of the exact archived PEX slice.",
        "The selected copy checks programmed discharge and absent-via retention;",
        "the second holds expert-enable low and checks masking. Output load is the",
        "only synthetic capacitance added to the extracted circuit.",
        "",
        "## Governed sweep",
        "",
        "- Full 3 × 3 × 3 SS/TT/FF, 1.08/1.20/1.32-V, -40/27/125-C sweep at 20 fF.",
        "- 5/20/80-fF load sweeps at nominal, slow-low-hot, and fast-high-cold conditions.",
        "- Duplicate points run once, yielding 33 deterministic cases.",
        "- Supply points remain below the public low-voltage model's 1.5-V VDS maximum.",
        "",
        "## Claim boundary",
        "",
    ]
    lines.extend(f"- Establishes: {item}." for item in result["claim_boundary"]["establishes"])
    lines.append("")
    lines.extend(f"- Does not establish: {item}." for item in result["claim_boundary"]["forbidden_inferences"])
    lines.extend(
        [
            "",
            "No IHP or SKY130 electrical value is feature-size-scaled into N7/N4",
            "performance or a GPU speedup.",
            "",
            "## Reproduction",
            "",
            "```bash",
            "python3 tools/run_ihp_extracted_pvt.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--ngspice", type=Path)
    parser.add_argument("--osdi-root", type=Path)
    args = parser.parse_args()

    contract = strict_json(CONTRACT_PATH)
    validate_contract(contract)
    cases = generated_cases(contract)
    if args.validate_only:
        print(f"PASS: IHP extracted-PVT contract; {len(cases)} deterministic cases")
        return 0

    lock = strict_json(repo_path(contract["pdk_lock"]))
    upstream = verify_physical_input(contract)
    pdk = locate_pdk(args.pdk_root)
    pdk_identity = verify_pdk(pdk, lock)
    ngspice = locate_tool(
        args.ngspice,
        "OPENTALLAS_IHP_NGSPICE",
        Path.home() / ".local" / "opentallas-tools" / "ngspice-43-osdi" / "bin" / "ngspice",
        "pinned ngspice 43 OSDI simulator",
    )
    ngspice_identity = verify_tool(ngspice, lock["tools"]["ngspice"], "ngspice-43")
    osdi = (
        args.osdi_root.expanduser().resolve()
        if args.osdi_root is not None
        else Path.home() / ".local" / "opentallas-tools" / "ihp-sg13g2-v0.3.0-osdi"
    )
    osdi_identity = verify_osdi(osdi, lock)
    model_root = pdk / "ihp-sg13g2" / "libs.tech" / "ngspice" / "models"
    corner = model_root / "cornerMOSlv.lib"
    model_files = [corner, model_root / "sg13g2_moslv_mod.lib", model_root / "sg13g2_moslv_parm.lib"]
    if not all(path.is_file() for path in model_files):
        raise IhpPvtError("official IHP low-voltage model dependency closure is incomplete")

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    template_path = repo_path(contract["inputs"]["template"])
    template = template_path.read_text(encoding="utf-8")
    pex = repo_path(contract["inputs"]["pex_netlist"])
    init = repo_path(contract["inputs"]["spice_init"])
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index:02d}/{len(cases)}] {case_label(case)}", flush=True)
        results.append(
            run_case(case, contract, template, corner, pex, init, ngspice, pdk, osdi)
        )
    failures = [case for case in results if case["status"] != "pass"]
    summary = {
        "cases_failed": len(failures),
        "cases_passed": len(results) - len(failures),
        "cases_total": len(results),
        "max_discharge_delay_ns": extremum(results, "discharge_delay_ns", True),
        "max_inactive_leakage_ua": extremum(results, "inactive_leakage_ua", True),
        "max_read_energy_fj": extremum(results, "read_energy_fj", True),
        "min_read_margin_fraction_vdd": extremum(results, "read_margin_fraction_vdd", False),
        "expected_benign_warning_counts": dict(
            sorted(Counter(w for case in results for w in case["expected_benign_warnings"]).items())
        ),
    }
    result = {
        "schema_version": 1,
        "experiment_id": contract["experiment_id"],
        "status": "pass" if not failures else "fail",
        "acceptance": contract["acceptance"],
        "cases": results,
        "summary": summary,
        "claim_boundary": contract["claim_boundary"],
        "contract": {"path": CONTRACT_PATH.relative_to(ROOT).as_posix(), "sha256": sha256_file(CONTRACT_PATH)},
        "input_model": {"campaigns": contract["campaigns"], "dimensions": contract["dimensions"]},
        "pdk": {
            **pdk_identity,
            "model_files": [
                {"path": path.relative_to(pdk).as_posix(), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
                for path in model_files
            ],
            "corner_sections": {corner_name: f"mos_{corner_name}" for corner_name in ("ss", "tt", "ff")},
        },
        "runner": {"path": Path(__file__).resolve().relative_to(ROOT).as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
        "template": {"path": contract["inputs"]["template"], "sha256": sha256_file(template_path)},
        "spice_init": {"path": contract["inputs"]["spice_init"], "sha256": sha256_file(init)},
        "toolchain": {"ngspice": ngspice_identity, "osdi_modules": osdi_identity},
        "upstream_physical": upstream,
    }
    json_path = repo_path(contract["reports"]["json"])
    markdown_path = repo_path(contract["reports"]["markdown"])
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(result), encoding="utf-8")
    print(f"{result['status'].upper()}: {summary['cases_passed']}/{summary['cases_total']} cases passed")
    if failures:
        for case in failures:
            print(f"  {case_label(case)}: {case['failures']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (IhpPvtError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
