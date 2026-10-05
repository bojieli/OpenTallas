#!/usr/bin/env python3
"""Run the governed capacitance-extracted SKY130A ROM-slice PVT campaign."""

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
CONTRACT_PATH = ROOT / "spice" / "sky130_rom_slice" / "extracted_pvt_contract.json"
BUILD = ROOT / "spice" / "build" / "sky130_extracted_pvt"
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
}


class ExtractedPvtError(RuntimeError):
    """A governed campaign input or acceptance gate failed."""


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
        raise ExtractedPvtError(f"cannot load {path}: {exc}") from exc
    if duplicates:
        raise ExtractedPvtError(f"duplicate JSON keys: {sorted(set(duplicates))}")
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
        raise ExtractedPvtError(f"repository path must be contained: {value}")
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ExtractedPvtError(f"repository path escapes root: {value}") from exc
    return path


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema_version") != 1:
        raise ExtractedPvtError("contract schema_version must be 1")
    if contract.get("experiment_id") != "sky130_via_rom_extracted_pvt_v1":
        raise ExtractedPvtError("unexpected experiment_id")
    dimensions = contract.get("dimensions", {})
    expected = {"process_corner", "vdd_v", "temperature_c", "output_load_ff"}
    if set(dimensions) != expected or dimensions["process_corner"] != ["ss", "tt", "ff"]:
        raise ExtractedPvtError("incomplete or unordered extracted-PVT dimensions")
    for name, values in dimensions.items():
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise ExtractedPvtError(f"dimension {name} must be a unique non-empty list")
        if name != "process_corner" and any(
            not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in values
        ):
            raise ExtractedPvtError(f"dimension {name} must contain finite numeric values")
        if name in {"vdd_v", "output_load_ff"} and any(value <= 0 for value in values):
            raise ExtractedPvtError(f"dimension {name} must contain positive values")
    campaigns = contract.get("campaigns")
    if not isinstance(campaigns, list) or len(campaigns) != 4:
        raise ExtractedPvtError("four extracted-PVT campaigns are required")
    names: set[str] = set()
    for campaign in campaigns:
        if set(campaign) != {"name", "dimensions", "fixed"}:
            raise ExtractedPvtError("invalid campaign entry")
        name = campaign["name"]
        if not isinstance(name, str) or not name or name in names:
            raise ExtractedPvtError("campaign names must be unique")
        names.add(name)
        swept = campaign["dimensions"]
        fixed = campaign["fixed"]
        if set(swept) | set(fixed) != expected or set(swept) & set(fixed):
            raise ExtractedPvtError(f"campaign {name} does not cover dimensions exactly once")
        for key, value in fixed.items():
            if value not in dimensions[key]:
                raise ExtractedPvtError(f"campaign {name} fixed value is outside dimension")
    boundary = contract.get("claim_boundary", {})
    if (
        boundary.get("evidence_class") != "capacitance_extracted_open_pdk_simulation"
        or boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("establishes")
        or not boundary.get("forbidden_inferences")
    ):
        raise ExtractedPvtError("claim boundary must prohibit target-node scaling")
    for path in contract.get("inputs", {}).values():
        if not repo_path(path).is_file():
            raise ExtractedPvtError(f"missing campaign input: {path}")
    acceptance = contract.get("acceptance", {})
    for key, value in acceptance.items():
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ExtractedPvtError(f"acceptance threshold {key} must be finite")
    if acceptance.get("unexpected_warnings_max") != 0:
        raise ExtractedPvtError("unexpected warnings must be fatal")


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
    cases = []
    for index, key in enumerate(sorted(by_key), start=1):
        cases.append(
            {
                **by_key[key],
                "campaigns": sorted(membership[key]),
                "case_id": f"case_{index:03d}",
            }
        )
    if len(cases) != 33:
        raise ExtractedPvtError(f"campaign must yield 33 unique cases, got {len(cases)}")
    return cases


def locate_pdk() -> Path:
    candidates: list[Path] = []
    override = os.environ.get("OPENTALLAS_PDK_ROOT")
    if override:
        root = Path(override)
        candidates.append(root if root.name == "sky130A" else root / "sky130A")
    candidates.extend(
        [
            ROOT / ".cache" / "pdk-root" / "sky130A",
            Path.home() / ".local" / "opentallas-pdk" / "sky130A",
        ]
    )
    for candidate in candidates:
        path = candidate.expanduser().resolve()
        if (path / "libs.tech" / "ngspice" / "sky130.lib.spice").is_file():
            return path
    raise ExtractedPvtError(f"cannot locate installed SKY130A ngspice models: {candidates}")


def ngspice_identity() -> dict[str, Any]:
    executable = shutil.which(os.environ.get("OPENTALLAS_NGSPICE", "ngspice"))
    if executable is None:
        raise ExtractedPvtError("ngspice executable not found")
    path = Path(executable).resolve()
    completed = subprocess.run(
        [str(path), "--version"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0 or "ngspice-36" not in completed.stdout:
        raise ExtractedPvtError(f"unexpected ngspice identity: {completed.stdout}")
    return {
        "executable": str(path),
        "executable_sha256": sha256_file(path),
        "version_output": completed.stdout.strip(),
    }


def verify_physical_input(contract: dict[str, Any]) -> dict[str, Any]:
    result_path = repo_path(contract["inputs"]["physical_result"])
    physical = strict_json(result_path)
    if physical.get("status") != "pass":
        raise ExtractedPvtError("upstream physical experiment did not pass")
    if physical.get("verification", {}).get("drc", {}).get("errors") != 0:
        raise ExtractedPvtError("upstream physical DRC is not clean")
    if physical.get("verification", {}).get("lvs", {}).get("final_result") != (
        "Circuits match uniquely."
    ):
        raise ExtractedPvtError("upstream physical LVS is not a unique match")
    pex_path = repo_path(contract["inputs"]["pex_netlist"])
    archived = {
        item["path"]: item for item in physical.get("artifacts", [])
    }.get(contract["inputs"]["pex_netlist"])
    if archived is None or archived.get("sha256") != sha256_file(pex_path):
        raise ExtractedPvtError("PEX netlist does not match upstream physical manifest")
    return {
        "path": contract["inputs"]["physical_result"],
        "sha256": sha256_file(result_path),
        "experiment_id": physical.get("experiment_id"),
        "pdk_tree_manifest_sha256": physical["pdk"]["tree"]["manifest_sha256"],
        "pex_path": contract["inputs"]["pex_netlist"],
        "pex_sha256": sha256_file(pex_path),
    }


def render_deck(
    template: str, case: dict[str, Any], model_deck: Path, pex: Path
) -> str:
    replacements = {
        "@TEMPERATURE_C@": str(case["temperature_c"]),
        "@MODEL_DECK@": str(model_deck),
        "@PEX_NETLIST@": str(pex),
        "@VDD_V@": str(case["vdd_v"]),
        "@OUTPUT_LOAD_FF@": str(case["output_load_ff"]),
    }
    rendered = template
    for placeholder, value in replacements.items():
        if rendered.count(placeholder) < 1:
            raise ExtractedPvtError(f"template must contain {placeholder}")
        rendered = rendered.replace(placeholder, value)
    if "@" in rendered:
        raise ExtractedPvtError("unrendered template placeholder remains")
    return rendered


def parse_measures(text: str) -> dict[str, float]:
    values = {match.group(1): float(match.group(2)) for match in MEASURE_RE.finditer(text)}
    missing = set(MEASURE_NAMES) - set(values)
    if missing:
        raise ExtractedPvtError(f"missing ngspice measures: {sorted(missing)}")
    if any(not math.isfinite(value) for value in values.values()):
        raise ExtractedPvtError("ngspice emitted non-finite measures")
    return values


def evaluate(
    case: dict[str, Any], values: dict[str, float], warnings: list[str], contract: dict[str, Any]
) -> list[str]:
    threshold = contract["acceptance"]
    vdd = case["vdd_v"]
    checks = (
        (values["v_present"] <= threshold["present_bitline_fraction_max"] * vdd, "selected programmed bitline did not discharge"),
        (values["v_absent"] >= threshold["absent_bitline_fraction_min"] * vdd, "via-absent bitline did not retain high"),
        (values["v_masked"] >= threshold["masked_bitline_fraction_min"] * vdd, "masked programmed bitline did not retain high"),
        (values["read_margin"] >= threshold["read_margin_fraction_min"] * vdd, "dynamic bitline separation is below threshold"),
        (values["sense_present_v"] >= threshold["sense_high_fraction_min"] * vdd, "present-bit sense output did not resolve high"),
        (values["sense_absent_v"] <= threshold["sense_low_fraction_max"] * vdd, "absent-bit sense output did not resolve low"),
        (values["sense_masked_v"] <= threshold["sense_low_fraction_max"] * vdd, "masked-bit sense output did not resolve low"),
        (0 < values["discharge_delay"] <= threshold["discharge_delay_ns_max"] * 1e-9, "discharge delay is outside bounded read window"),
        (threshold["read_energy_fj_min"] * 1e-15 < values["read_energy"] <= threshold["read_energy_fj_max"] * 1e-15, "read energy is outside sanity bound"),
        (0 <= values["inactive_leakage"] <= threshold["inactive_leakage_ua_max"] * 1e-6, "inactive leakage is outside sanity bound"),
        (len(warnings) <= threshold["unexpected_warnings_max"], "unexpected ngspice warning observed"),
    )
    return [message for passed, message in checks if not passed]


def run_case(
    case: dict[str, Any], contract: dict[str, Any], template: str, model_decks: dict[str, Path], pex: Path, executable: str
) -> dict[str, Any]:
    case_dir = BUILD / "cases" / case["case_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    deck = case_dir / "read.spice"
    model_deck = model_decks[case["process_corner"]]
    deck.write_text(render_deck(template, case, model_deck, pex), encoding="utf-8")
    log = case_dir / "ngspice.log"
    completed = subprocess.run(
        [executable, "-b", "-o", str(log), str(deck)],
        cwd=model_deck.parent,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    if completed.returncode != 0:
        raise ExtractedPvtError(
            f"{case['case_id']}: ngspice failed ({completed.returncode}); "
            f"stdout={completed.stdout!r}; stderr={completed.stderr!r}; log={log}"
        )
    values = parse_measures(log_text)
    all_warnings = sorted(set(WARNING_RE.findall(log_text + "\n" + completed.stderr)))
    expected = sorted(set(all_warnings) & EXPECTED_BENIGN_WARNINGS)
    warnings = sorted(set(all_warnings) - EXPECTED_BENIGN_WARNINGS)
    failures = evaluate(case, values, warnings, contract)
    return {
        **case,
        "deck_sha256": sha256_file(deck),
        "model_deck_sha256": sha256_file(model_deck),
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


def prepare_model_decks(pdk: Path) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    """Create small, auditable primitive-only decks from the installed PDK.

    Loading ``sky130.lib.spice`` pulls every device family into ngspice.  This
    circuit uses only the 1V8 NFET/PFET, so the governed run copies the exact
    invariant, non-FET, corner, and corner-PM3 files for those primitives.
    """

    tech = pdk / "libs.tech" / "ngspice"
    primitive = pdk / "libs.ref" / "sky130_fd_pr" / "spice"
    decks: dict[str, Path] = {}
    identities: dict[str, dict[str, Any]] = {}
    for corner in ("ss", "tt", "ff"):
        target = BUILD / "models" / corner
        target.mkdir(parents=True, exist_ok=True)
        sources = [
            tech / "parameters" / "invariant.spice",
            tech / "corners" / corner / "nonfet.spice",
            primitive / f"sky130_fd_pr__nfet_01v8__{corner}.corner.spice",
            primitive / f"sky130_fd_pr__nfet_01v8__{corner}.pm3.spice",
            primitive / f"sky130_fd_pr__pfet_01v8__{corner}.corner.spice",
            primitive / f"sky130_fd_pr__pfet_01v8__{corner}.pm3.spice",
        ]
        for source in sources:
            if not source.is_file():
                raise ExtractedPvtError(f"missing installed primitive model file: {source}")
            identity_key = str(source.relative_to(pdk))
            identities.setdefault(
                identity_key,
                {
                    "path": identity_key,
                    "sha256": sha256_file(source),
                    "size_bytes": source.stat().st_size,
                },
            )
            shutil.copyfile(source, target / source.name)
        deck = target / "models.spice"
        deck.write_text(
            "* Primitive-only installed SKY130A model deck\n"
            ".param mc_mm_switch=0\n"
            ".param mc_pr_switch=0\n"
            + "\n".join(
                f'.include "{(target / source.name)}"'
                for source in (sources[0], sources[1], sources[2], sources[4])
            )
            + "\n",
            encoding="utf-8",
        )
        (target / ".spiceinit").write_text("set ngbehavior=hsa\n", encoding="utf-8")
        decks[corner] = deck
    return decks, [identities[key] for key in sorted(identities)]


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
        "# Capacitance-extracted SKY130A via-ROM PVT campaign",
        "",
        f"**Result:** **{result['status'].upper()}** ({summary['cases_passed']}/{summary['cases_total']} cases passed)  ",
        "**Evidence class:** deterministic open-PDK PVT simulation of the archived capacitance-extracted slice; not silicon  ",
        f"**Upstream PEX:** `{result['upstream_physical']['pex_sha256']}`  ",
        f"**Simulator:** `{next(line for line in result['toolchain']['ngspice']['version_output'].splitlines() if 'ngspice-' in line).strip()}`",
        "",
        "## Results",
        "",
        "| Limiting metric | Observed case |",
        "|---|---|",
        f"| Minimum dynamic separation / VDD | {describe(summary['min_read_margin_fraction_vdd'], 'V/V')} |",
        f"| Maximum VDD/2 discharge delay | {describe(summary['max_discharge_delay_ns'], 'ns')} |",
        f"| Maximum 0–5 ns supply energy | {describe(summary['max_read_energy_fj'], 'fJ')} |",
        f"| Maximum 6–7 ns supply current | {describe(summary['max_inactive_leakage_ua'], 'uA')} |",
        "",
        "The circuit instantiates two copies of the exact archived two-column PEX",
        "slice. One copy has expert-enable high and validates programmed discharge",
        "plus absent-via retention; the second has expert-enable low and validates",
        "physical masking. The load sweep adds only the declared external output load.",
        "",
        "## Governed sweep",
        "",
        "- Full 3 × 3 × 3 SS/TT/FF, 1.62/1.80/1.98-V, -40/25/125-C PVT sweep at 20-fF output load.",
        "- 5/20/80-fF output-load sweeps at nominal PVT, slow-low-hot, and fast-high-cold.",
        "- Duplicate points run once, yielding 33 deterministic cases.",
        "- Every case checks bitline state, normalized margin, sense polarity, delay, energy, nonnegative bounded current, and unexpected warnings.",
        "",
        "## Claim boundary",
        "",
    ]
    lines.extend(f"- Establishes: {item}." for item in result["claim_boundary"]["establishes"])
    lines.append("")
    lines.extend(
        f"- Does not establish: {item}."
        for item in result["claim_boundary"]["forbidden_inferences"]
    )
    lines.extend(
        [
            "",
            "This result cannot be scaled from SKY130 into N7/N4 performance or a GPU",
            "speedup. Distributed wire resistance and statistical mismatch remain separate",
            "open gates, followed by target-foundry macro correlation and silicon.",
            "",
            "## Reproduction",
            "",
            "```bash",
            "python3 tools/run_sky130_extracted_pvt.py",
            "```",
            "",
            "Exact inputs, case measures, warnings, thresholds, and SHA-256 identities are",
            "stored in `results/spice/sky130_extracted_pvt.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    contract = strict_json(CONTRACT_PATH)
    validate_contract(contract)
    cases = generated_cases(contract)
    if args.validate_only:
        print(f"PASS: extracted-PVT contract; {len(cases)} deterministic cases")
        return 0

    upstream = verify_physical_input(contract)
    pdk = locate_pdk()
    template_path = repo_path(contract["inputs"]["template"])
    template = template_path.read_text(encoding="utf-8")
    pex = repo_path(contract["inputs"]["pex_netlist"])
    tool = ngspice_identity()
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    model_decks, model_files = prepare_model_decks(pdk)

    results = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index:02d}/{len(cases)}] {case_label(case)}", flush=True)
        results.append(run_case(case, contract, template, model_decks, pex, tool["executable"]))
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
        "acceptance": contract["acceptance"],
        "cases": results,
        "claim_boundary": contract["claim_boundary"],
        "contract": {
            "path": str(CONTRACT_PATH.relative_to(ROOT)),
            "sha256": sha256_file(CONTRACT_PATH),
        },
        "experiment_id": contract["experiment_id"],
        "input_model": {
            "campaigns": contract["campaigns"],
            "dimensions": contract["dimensions"],
        },
        "pdk": {
            "model_files": model_files,
            "model_scope": "installed invariant/nonfet plus 1V8 NFET/PFET SS/TT/FF primitive files only",
            "variant": "sky130A",
        },
        "runner": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "schema_version": 1,
        "status": "pass" if not failures else "fail",
        "summary": summary,
        "template": {
            "path": contract["inputs"]["template"],
            "sha256": sha256_file(template_path),
        },
        "toolchain": {"ngspice": tool},
        "upstream_physical": upstream,
    }
    json_path = repo_path(contract["reports"]["json"])
    markdown_path = repo_path(contract["reports"]["markdown"])
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(result), encoding="utf-8")
    print(f"{result['status'].upper()}: {summary['cases_passed']}/{summary['cases_total']} cases passed")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ExtractedPvtError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
