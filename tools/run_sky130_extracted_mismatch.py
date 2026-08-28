#!/usr/bin/env python3
"""Run a governed fixed-seed SKY130A mismatch campaign on the archived PEX slice."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "spice" / "sky130_rom_slice" / "extracted_mismatch_contract.json"
)
BUILD = ROOT / "spice" / "build" / "sky130_extracted_mismatch"
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


class ExtractedMismatchError(RuntimeError):
    """A governed mismatch input, execution, or acceptance gate failed."""


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
        raise ExtractedMismatchError(f"cannot load {path}: {exc}") from exc
    if duplicates:
        raise ExtractedMismatchError(
            f"duplicate JSON keys in {path}: {sorted(set(duplicates))}"
        )
    return parsed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def repo_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ExtractedMismatchError(f"repository path must be contained: {value}")
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ExtractedMismatchError(f"repository path escapes root: {value}") from exc
    return path


def derive_seeds(sampling: dict[str, Any]) -> list[int]:
    if sampling["seed_algorithm"] != (
        "sha256_namespace_colon_index_first_u64_mod_2147483646_plus_1"
    ):
        raise ExtractedMismatchError("unsupported seed derivation algorithm")
    namespace = sampling["seed_namespace"]
    origin = sampling["index_origin"]
    seeds = []
    for offset in range(sampling["count"]):
        material = f"{namespace}:{origin + offset}".encode("utf-8")
        word = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
        seeds.append(word % 2_147_483_646 + 1)
    if len(seeds) != len(set(seeds)):
        raise ExtractedMismatchError("derived mismatch seeds are not unique")
    return seeds


def validate_contract(contract: dict[str, Any]) -> list[int]:
    if contract.get("schema_version") != 1:
        raise ExtractedMismatchError("contract schema_version must be 1")
    if contract.get("experiment_id") != "sky130_via_rom_extracted_mismatch_v1":
        raise ExtractedMismatchError("unexpected mismatch experiment_id")

    operating = contract.get("operating_point")
    if operating != {
        "output_load_ff": 20.0,
        "temperature_c": 25.0,
        "vdd_v": 1.8,
    }:
        raise ExtractedMismatchError(
            "v1 mismatch campaign must remain at nominal TT, 1.8 V, 25 C, 20 fF"
        )
    model_mode = contract.get("model_mode")
    if model_mode != {
        "corner": "tt",
        "mc_mm_switch": 1,
        "mc_pr_switch": 0,
        "scope": "mismatch_only_process_variation_disabled",
    }:
        raise ExtractedMismatchError("v1 must enable mismatch and disable process variation")

    sampling = contract.get("sampling", {})
    required_sampling = {
        "count",
        "default_workers",
        "index_origin",
        "quantiles",
        "replay_index",
        "seed_algorithm",
        "seed_namespace",
    }
    if set(sampling) != required_sampling:
        raise ExtractedMismatchError("incomplete or extra sampling policy fields")
    if sampling["count"] != 256 or sampling["index_origin"] != 0:
        raise ExtractedMismatchError("v1 requires exactly 256 fixed seeds from index zero")
    if sampling["default_workers"] != 4:
        raise ExtractedMismatchError("v1 default worker count must remain four")
    if not isinstance(sampling["seed_namespace"], str) or not sampling["seed_namespace"]:
        raise ExtractedMismatchError("seed namespace must be a non-empty string")
    if not isinstance(sampling["replay_index"], int) or not (
        0 <= sampling["replay_index"] < sampling["count"]
    ):
        raise ExtractedMismatchError("replay index is outside the sample set")
    quantiles = sampling["quantiles"]
    if quantiles != [0.0, 0.01, 0.05, 0.5, 0.95, 0.99, 1.0]:
        raise ExtractedMismatchError("v1 quantile set changed")
    seeds = derive_seeds(sampling)

    required_acceptance = {
        "absent_bitline_fraction_min",
        "discharge_delay_ns_max",
        "masked_bitline_fraction_min",
        "minimum_distinct_discharge_delay_values",
        "minimum_distinct_read_margin_values",
        "present_bitline_fraction_max",
        "read_energy_fj_max",
        "read_energy_fj_min",
        "read_margin_fraction_min",
        "replay_max_abs_measure_delta",
        "sample_failures_max",
        "sense_high_fraction_min",
        "sense_low_fraction_max",
        "supply_current_rms_ua_max",
        "unexpected_warnings_max",
    }
    acceptance = contract.get("acceptance", {})
    if set(acceptance) != required_acceptance:
        raise ExtractedMismatchError("incomplete or extra mismatch acceptance fields")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in acceptance.values()
    ):
        raise ExtractedMismatchError("all mismatch acceptance values must be finite numbers")
    if (
        acceptance["sample_failures_max"] != 0
        or acceptance["unexpected_warnings_max"] != 0
        or acceptance["replay_max_abs_measure_delta"] != 0.0
        or acceptance["minimum_distinct_discharge_delay_values"] < 2
        or acceptance["minimum_distinct_read_margin_values"] < 2
    ):
        raise ExtractedMismatchError("v1 reproducibility and warning gates were weakened")

    expected_inputs = {
        "deterministic_pvt_result",
        "pdk_lock",
        "pex_netlist",
        "physical_result",
        "template",
    }
    inputs = contract.get("inputs", {})
    if set(inputs) != expected_inputs:
        raise ExtractedMismatchError("incomplete or extra mismatch input paths")
    for value in inputs.values():
        if not repo_path(value).is_file():
            raise ExtractedMismatchError(f"missing mismatch campaign input: {value}")
    reports = contract.get("reports", {})
    if set(reports) != {"json", "markdown"}:
        raise ExtractedMismatchError("mismatch report paths are incomplete")
    for value in reports.values():
        repo_path(value)

    boundary = contract.get("claim_boundary", {})
    if (
        boundary.get("evidence_class")
        != "public_open_pdk_mismatch_model_simulation_of_capacitance_extracted_slice"
        or boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("establishes")
        or not boundary.get("forbidden_inferences")
    ):
        raise ExtractedMismatchError("claim boundary must prohibit target-node scaling")
    return seeds


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
    raise ExtractedMismatchError(
        f"cannot locate installed SKY130A ngspice models: {candidates}"
    )


def ngspice_identity() -> dict[str, Any]:
    executable = shutil.which(os.environ.get("OPENTALLAS_NGSPICE", "ngspice"))
    if executable is None:
        raise ExtractedMismatchError("ngspice executable not found")
    path = Path(executable).resolve()
    completed = subprocess.run(
        [str(path), "--version"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0 or "ngspice-36" not in completed.stdout:
        raise ExtractedMismatchError(f"unexpected ngspice identity: {completed.stdout}")
    return {
        "executable": str(path),
        "executable_sha256": sha256_file(path),
        "version_output": completed.stdout.strip(),
    }


def verify_upstream(contract: dict[str, Any]) -> dict[str, Any]:
    inputs = contract["inputs"]
    physical_path = repo_path(inputs["physical_result"])
    pvt_path = repo_path(inputs["deterministic_pvt_result"])
    pex_path = repo_path(inputs["pex_netlist"])
    lock_path = repo_path(inputs["pdk_lock"])
    physical = strict_json(physical_path)
    pvt = strict_json(pvt_path)
    lock = strict_json(lock_path)
    if physical.get("status") != "pass":
        raise ExtractedMismatchError("upstream physical experiment did not pass")
    if physical.get("verification", {}).get("drc") != {
        "errors": 0,
        "status": "pass",
    }:
        raise ExtractedMismatchError("upstream physical DRC is not clean")
    lvs = physical.get("verification", {}).get("lvs", {})
    if (
        lvs.get("final_result") != "Circuits match uniquely."
        or lvs.get("pin_lists_equivalent") is not True
    ):
        raise ExtractedMismatchError("upstream physical LVS is not a unique pin match")
    artifact = next(
        (
            item
            for item in physical.get("artifacts", [])
            if item.get("path") == inputs["pex_netlist"]
        ),
        None,
    )
    pex_sha256 = sha256_file(pex_path)
    if artifact is None or artifact.get("sha256") != pex_sha256:
        raise ExtractedMismatchError("PEX does not match the physical artifact manifest")
    if pvt.get("status") != "pass" or pvt.get("summary", {}).get("cases_failed") != 0:
        raise ExtractedMismatchError("upstream deterministic extracted-PVT run did not pass")
    pvt_upstream = pvt.get("upstream_physical", {})
    if (
        pvt_upstream.get("pex_sha256") != pex_sha256
        or pvt_upstream.get("sha256") != sha256_file(physical_path)
    ):
        raise ExtractedMismatchError("deterministic PVT result is not bound to current PEX")
    locked_manifest = lock.get("pdk", {}).get("installed_tree", {}).get(
        "manifest_sha256"
    )
    physical_manifest = physical.get("pdk", {}).get("tree", {}).get(
        "manifest_sha256"
    )
    if not locked_manifest or locked_manifest != physical_manifest:
        raise ExtractedMismatchError("physical result does not match the locked PDK tree")

    operating = contract["operating_point"]
    baseline_cases = [
        case
        for case in pvt.get("cases", [])
        if case.get("process_corner") == "tt"
        and case.get("vdd_v") == operating["vdd_v"]
        and case.get("temperature_c") == operating["temperature_c"]
        and case.get("output_load_ff") == operating["output_load_ff"]
    ]
    if len(baseline_cases) != 1:
        raise ExtractedMismatchError("cannot identify one nominal deterministic baseline case")
    baseline = baseline_cases[0]
    if baseline.get("status") != "pass" or set(baseline.get("measures_si", {})) != set(
        MEASURE_NAMES
    ):
        raise ExtractedMismatchError("nominal deterministic baseline is incomplete")
    return {
        "deterministic_pvt": {
            "baseline_case_id": baseline["case_id"],
            "baseline_measures_si": baseline["measures_si"],
            "path": inputs["deterministic_pvt_result"],
            "sha256": sha256_file(pvt_path),
        },
        "pdk_lock": {
            "path": inputs["pdk_lock"],
            "sha256": sha256_file(lock_path),
            "tree_manifest_sha256": locked_manifest,
        },
        "physical": {
            "experiment_id": physical.get("experiment_id"),
            "path": inputs["physical_result"],
            "pex_path": inputs["pex_netlist"],
            "pex_sha256": pex_sha256,
            "sha256": sha256_file(physical_path),
        },
    }


def prepare_model_deck(
    pdk: Path, model_mode: dict[str, Any]
) -> tuple[Path, list[dict[str, Any]], dict[str, Any]]:
    tech = pdk / "libs.tech" / "ngspice"
    primitive = pdk / "libs.ref" / "sky130_fd_pr" / "spice"
    corner = model_mode["corner"]
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
    identities: list[dict[str, Any]] = []
    mismatch_expression_counts: dict[str, int] = {}
    for source in sources:
        if not source.is_file():
            raise ExtractedMismatchError(f"missing installed model source: {source}")
        destination = target / source.name
        shutil.copyfile(source, destination)
        relative = str(source.relative_to(pdk))
        text = source.read_text(encoding="utf-8", errors="replace")
        count = text.upper().count("MC_MM_SWITCH*AGAUSS")
        identities.append(
            {
                "path": relative,
                "sha256": sha256_file(source),
                "size_bytes": source.stat().st_size,
            }
        )
        if source.name.endswith(".pm3.spice"):
            mismatch_expression_counts[relative] = count
            if count < 1:
                raise ExtractedMismatchError(
                    f"primitive model lacks mismatch AGAUSS expressions: {source}"
                )
    include_sources = (sources[0], sources[1], sources[2], sources[4])
    deck = target / "models.spice"
    deck.write_text(
        "* Primitive-only installed SKY130A TT mismatch model deck\n"
        f".param mc_mm_switch={model_mode['mc_mm_switch']}\n"
        f".param mc_pr_switch={model_mode['mc_pr_switch']}\n"
        + "\n".join(
            f'.include "{target / source.name}"' for source in include_sources
        )
        + "\n",
        encoding="utf-8",
    )
    activation = {
        "mc_mm_switch": model_mode["mc_mm_switch"],
        "mc_pr_switch": model_mode["mc_pr_switch"],
        "mismatch_expression_counts": dict(sorted(mismatch_expression_counts.items())),
        "mismatch_expression_total": sum(mismatch_expression_counts.values()),
    }
    return deck, sorted(identities, key=lambda item: item["path"]), activation


def render_deck(
    template: str,
    operating: dict[str, Any],
    model_deck: Path,
    pex: Path,
) -> str:
    replacements = {
        "@TEMPERATURE_C@": str(operating["temperature_c"]),
        "@MODEL_DECK@": str(model_deck),
        "@PEX_NETLIST@": str(pex),
        "@VDD_V@": str(operating["vdd_v"]),
        "@OUTPUT_LOAD_FF@": str(operating["output_load_ff"]),
    }
    rendered = template
    for placeholder, value in replacements.items():
        if rendered.count(placeholder) < 1:
            raise ExtractedMismatchError(f"template must contain {placeholder}")
        rendered = rendered.replace(placeholder, value)
    if "@" in rendered:
        raise ExtractedMismatchError("unrendered template placeholder remains")
    return rendered


def parsed_measures(text: str) -> tuple[dict[str, float], list[str]]:
    values = {match.group(1): float(match.group(2)) for match in MEASURE_RE.finditer(text)}
    invalid = [name for name, value in values.items() if not math.isfinite(value)]
    missing = sorted(set(MEASURE_NAMES) - set(values))
    return values, sorted(set(missing + invalid))


def evaluate_sample(
    values: dict[str, float],
    missing: list[str],
    unexpected_warnings: list[str],
    operating: dict[str, Any],
    acceptance: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if missing:
        failures.append("missing_or_nonfinite_measures:" + ",".join(missing))
        return failures
    vdd = operating["vdd_v"]
    checks = (
        (
            values["v_present"] <= acceptance["present_bitline_fraction_max"] * vdd,
            "selected_programmed_bitline_did_not_discharge",
        ),
        (
            values["v_absent"] >= acceptance["absent_bitline_fraction_min"] * vdd,
            "via_absent_bitline_did_not_retain_high",
        ),
        (
            values["v_masked"] >= acceptance["masked_bitline_fraction_min"] * vdd,
            "masked_programmed_bitline_did_not_retain_high",
        ),
        (
            values["read_margin"] >= acceptance["read_margin_fraction_min"] * vdd,
            "dynamic_bitline_separation_below_threshold",
        ),
        (
            values["sense_present_v"] >= acceptance["sense_high_fraction_min"] * vdd,
            "present_bit_sense_output_did_not_resolve_high",
        ),
        (
            values["sense_absent_v"] <= acceptance["sense_low_fraction_max"] * vdd,
            "absent_bit_sense_output_did_not_resolve_low",
        ),
        (
            values["sense_masked_v"] <= acceptance["sense_low_fraction_max"] * vdd,
            "masked_bit_sense_output_did_not_resolve_low",
        ),
        (
            0 < values["discharge_delay"]
            <= acceptance["discharge_delay_ns_max"] * 1e-9,
            "discharge_delay_outside_bounded_read_window",
        ),
        (
            acceptance["read_energy_fj_min"] * 1e-15
            < values["read_energy"]
            <= acceptance["read_energy_fj_max"] * 1e-15,
            "read_energy_outside_sanity_bound",
        ),
        (
            0 <= values["inactive_leakage"]
            <= acceptance["supply_current_rms_ua_max"] * 1e-6,
            "post_read_supply_current_rms_outside_sanity_bound",
        ),
        (
            len(unexpected_warnings) <= acceptance["unexpected_warnings_max"],
            "unexpected_ngspice_warning_observed",
        ),
    )
    failures.extend(message for passed, message in checks if not passed)
    return failures


def metrics_from_measures(
    values: dict[str, float], operating: dict[str, Any]
) -> dict[str, float]:
    vdd = operating["vdd_v"]
    return {
        "absent_bitline_fraction_vdd": values["v_absent"] / vdd,
        "discharge_delay_ns": values["discharge_delay"] * 1e9,
        "masked_bitline_fraction_vdd": values["v_masked"] / vdd,
        "post_read_supply_current_rms_ua": values["inactive_leakage"] * 1e6,
        "present_bitline_fraction_vdd": values["v_present"] / vdd,
        "read_energy_fj": values["read_energy"] * 1e15,
        "read_margin_fraction_vdd": values["read_margin"] / vdd,
        "sense_absent_fraction_vdd": values["sense_absent_v"] / vdd,
        "sense_masked_fraction_vdd": values["sense_masked_v"] / vdd,
        "sense_present_fraction_vdd": values["sense_present_v"] / vdd,
    }


def run_sample(
    *,
    case_id: str,
    sample_index: int,
    seed: int,
    rendered_deck: str,
    operating: dict[str, Any],
    acceptance: dict[str, Any],
    executable: str,
) -> dict[str, Any]:
    case_dir = BUILD / "cases" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    deck_path = case_dir / "read.spice"
    init_path = case_dir / ".spiceinit"
    log_path = case_dir / "ngspice.log"
    seed_marker = ".option scale=1u"
    if rendered_deck.count(seed_marker) != 1:
        raise ExtractedMismatchError(
            "testbench must contain exactly one scale option for seed injection"
        )
    seeded_deck = rendered_deck.replace(
        seed_marker,
        f".option seed={seed}\n{seed_marker}",
        1,
    )
    deck_path.write_text(seeded_deck, encoding="utf-8")
    init_path.write_text(
        "set ngbehavior=hsa\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [executable, "-b", "-o", str(log_path), str(deck_path)],
        cwd=case_dir,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    log_text = (
        log_path.read_text(encoding="utf-8", errors="replace")
        if log_path.exists()
        else ""
    )
    all_warnings = sorted(
        set(WARNING_RE.findall(log_text + "\n" + completed.stdout + "\n" + completed.stderr))
    )
    expected_warnings = sorted(set(all_warnings) & EXPECTED_BENIGN_WARNINGS)
    unexpected_warnings = sorted(set(all_warnings) - EXPECTED_BENIGN_WARNINGS)
    values, missing = parsed_measures(log_text)
    failures: list[str] = []
    if completed.returncode != 0:
        failures.append(f"ngspice_return_code:{completed.returncode}")
    failures.extend(
        evaluate_sample(values, missing, unexpected_warnings, operating, acceptance)
    )
    metrics = metrics_from_measures(values, operating) if not missing else None
    return {
        "case_id": case_id,
        "deck_sha256": sha256_file(deck_path),
        "expected_benign_warnings": expected_warnings,
        "failures": failures,
        "measures_si": values,
        "metrics": metrics,
        "missing_or_nonfinite_measures": missing,
        "ngspice": {
            "log_sha256": sha256_file(log_path) if log_path.exists() else None,
            "return_code": completed.returncode,
            "stderr_sha256": sha256_text(completed.stderr),
            "stdout_sha256": sha256_text(completed.stdout),
        },
        "sample_index": sample_index,
        "seed": seed,
        "seed_control": {
            "evaluation_order": "netlist_option_after_wallace_initialization_before_model_expansion",
            "netlist_option": f".option seed={seed}",
        },
        "spiceinit_sha256": sha256_file(init_path),
        "status": "pass" if not failures else "fail",
        "unexpected_warnings": unexpected_warnings,
    }


def linear_quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ExtractedMismatchError("cannot calculate a quantile without values")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def quantile_label(probability: float) -> str:
    return f"p{round(probability * 100):02d}" if probability < 1.0 else "p100"


def distribution(
    samples: list[dict[str, Any]],
    metric: str,
    unit: str,
    quantiles: list[float],
) -> dict[str, Any]:
    values = [
        sample["metrics"][metric]
        for sample in samples
        if sample.get("metrics") is not None
    ]
    return {
        "maximum": max(values),
        "mean": statistics.fmean(values),
        "minimum": min(values),
        "population_stddev": statistics.pstdev(values),
        "quantiles": {
            quantile_label(probability): linear_quantile(values, probability)
            for probability in quantiles
        },
        "sample_count": len(values),
        "unit": unit,
    }


def replay_check(
    original: dict[str, Any], replay: dict[str, Any], threshold: float
) -> dict[str, Any]:
    comparable = (
        set(original["measures_si"]) == set(MEASURE_NAMES)
        and set(replay["measures_si"]) == set(MEASURE_NAMES)
    )
    deltas = (
        {
            name: abs(original["measures_si"][name] - replay["measures_si"][name])
            for name in MEASURE_NAMES
        }
        if comparable
        else {}
    )
    maximum = max(deltas.values()) if deltas else math.inf
    passed = (
        original["seed"] == replay["seed"]
        and original["status"] == "pass"
        and replay["status"] == "pass"
        and maximum <= threshold
    )
    return {
        "all_measure_deltas_si": deltas,
        "maximum_abs_measure_delta_si": maximum if math.isfinite(maximum) else None,
        "original_case_id": original["case_id"],
        "replay_case_id": replay["case_id"],
        "seed": original["seed"],
        "status": "pass" if passed else "fail",
        "threshold_si": threshold,
    }


def markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    metric_labels = {
        "present_bitline_fraction_vdd": "Selected programmed bitline / VDD",
        "absent_bitline_fraction_vdd": "Via-absent bitline / VDD",
        "masked_bitline_fraction_vdd": "Masked programmed bitline / VDD",
        "read_margin_fraction_vdd": "Dynamic separation / VDD",
        "discharge_delay_ns": "VDD/2 discharge delay (ns)",
        "read_energy_fj": "0-5 ns supply energy (fJ)",
        "post_read_supply_current_rms_ua": "6-7 ns supply-current RMS (uA)",
    }
    lines = [
        "# Fixed-seed SKY130A extracted-slice mismatch campaign",
        "",
        f"**Result:** **{result['status'].upper()}** "
        f"({summary['samples_passed']}/{summary['samples_total']} modeled samples passed)  ",
        "**Evidence class:** public open-PDK mismatch-model simulation of the archived capacitance-extracted local slice; not silicon  ",
        f"**Operating point:** TT, {result['input_model']['operating_point']['vdd_v']:.2f} V, "
        f"{result['input_model']['operating_point']['temperature_c']:.0f} C, "
        f"{result['input_model']['operating_point']['output_load_ff']:.0f} fF  ",
        f"**Upstream PEX:** `{result['upstream']['physical']['pex_sha256']}`",
        "",
        "## Observed distributions",
        "",
        "The table reports linear-interpolated empirical quantiles across the fixed",
        "seed set. It is a circuit-model sensitivity result, not a fitted probability",
        "distribution or a production-yield estimate.",
        "",
        "| Metric | Minimum | p01 | p50 | p99 | Maximum |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, label in metric_labels.items():
        item = summary["distributions"][key]
        lines.append(
            f"| {label} | {item['minimum']:.6g} | "
            f"{item['quantiles']['p01']:.6g} | {item['quantiles']['p50']:.6g} | "
            f"{item['quantiles']['p99']:.6g} | {item['maximum']:.6g} |"
        )
    variation = summary["variation_detection"]
    replay = summary["same_seed_replay"]
    activation = result["pdk"]["mismatch_activation"]
    lines.extend(
        [
            "",
            "## Reproducibility and activation checks",
            "",
            f"- The contract deterministically derives {summary['samples_total']} unique positive ngspice seeds; the ordered list digest is `{result['input_model']['sampling']['ordered_seed_list_sha256']}`.",
            f"- A fresh ngspice process reloads the mismatch-enabled primitive models for every seed (`mc_mm_switch=1`, `mc_pr_switch=0`); each generated netlist carries `.option seed=<value>` before model expansion.",
            f"- The copied NFET/PFET model files contain {activation['mismatch_expression_total']} `MC_MM_SWITCH*AGAUSS` expressions in total.",
            f"- Same-seed replay: **{replay['status'].upper()}**, maximum absolute parsed-measure delta {replay['maximum_abs_measure_delta_si']:.6g} SI units.",
            f"- Cross-seed variation: {variation['distinct_discharge_delay_values']} distinct discharge-delay values and {variation['distinct_read_margin_values']} distinct read-margin values.",
            "",
            "All passing samples satisfy the same local functional thresholds used by",
            "the deterministic extracted-PVT campaign. Zero failures in this finite",
            "public-model set must not be described as 100% yield: the run omits random",
            "defects, spatial/systematic variation, sense-amplifier offset, compact-array",
            "parasitics, distributed resistance, IR/noise, aging, repair, and silicon",
            "correlation.",
            "",
            "## Claim boundary",
            "",
        ]
    )
    lines.extend(f"- Establishes: {item}." for item in result["claim_boundary"]["establishes"])
    lines.append("")
    lines.extend(
        f"- Does not establish: {item}."
        for item in result["claim_boundary"]["forbidden_inferences"]
    )
    lines.extend(
        [
            "",
            "No value in this report may be scaled from SKY130 into N7/N4 or used",
            "to calculate a GPU speedup.",
            "",
            "## Reproduction",
            "",
            "```bash",
            "python3 tools/run_sky130_extracted_mismatch.py",
            "```",
            "",
            "The contract, exact seed per sample, parsed measures, warnings, model-file",
            "hashes, replay deltas, and tool identity are stored in",
            "`results/spice/sky130_extracted_mismatch.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--workers", type=int)
    args = parser.parse_args()
    contract = strict_json(CONTRACT_PATH)
    seeds = validate_contract(contract)
    if args.validate_only:
        print(
            "PASS: extracted-mismatch contract; "
            f"{len(seeds)} fixed seeds plus one same-seed replay"
        )
        return 0

    workers = args.workers or contract["sampling"]["default_workers"]
    if not 1 <= workers <= 16:
        raise ExtractedMismatchError("workers must be between 1 and 16")
    upstream = verify_upstream(contract)
    pdk = locate_pdk()
    tool = ngspice_identity()
    template_path = repo_path(contract["inputs"]["template"])
    pex = repo_path(contract["inputs"]["pex_netlist"])
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    model_deck, model_files, activation = prepare_model_deck(
        pdk, contract["model_mode"]
    )
    rendered = render_deck(
        template_path.read_text(encoding="utf-8"),
        contract["operating_point"],
        model_deck,
        pex,
    )

    def execute(index_and_seed: tuple[int, int]) -> dict[str, Any]:
        index, seed = index_and_seed
        return run_sample(
            case_id=f"sample_{index + 1:04d}",
            sample_index=index,
            seed=seed,
            rendered_deck=rendered,
            operating=contract["operating_point"],
            acceptance=contract["acceptance"],
            executable=tool["executable"],
        )

    results: list[dict[str, Any]] = []
    indexed_seeds = list(enumerate(seeds))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {executor.submit(execute, item): item[0] for item in indexed_seeds}
        for completed_count, future in enumerate(as_completed(pending), start=1):
            sample = future.result()
            results.append(sample)
            if completed_count == 1 or completed_count % 16 == 0 or completed_count == len(seeds):
                print(
                    f"[{completed_count:03d}/{len(seeds)}] completed "
                    f"{sample['case_id']} ({sample['status']})",
                    flush=True,
                )
    results.sort(key=lambda sample: sample["sample_index"])

    replay_index = contract["sampling"]["replay_index"]
    replay = run_sample(
        case_id=f"replay_sample_{replay_index + 1:04d}",
        sample_index=replay_index,
        seed=seeds[replay_index],
        rendered_deck=rendered,
        operating=contract["operating_point"],
        acceptance=contract["acceptance"],
        executable=tool["executable"],
    )
    replay_summary = replay_check(
        results[replay_index],
        replay,
        contract["acceptance"]["replay_max_abs_measure_delta"],
    )

    valid_samples = [sample for sample in results if sample["metrics"] is not None]
    if not valid_samples:
        raise ExtractedMismatchError("no sample emitted a complete measure vector")
    metric_units = {
        "absent_bitline_fraction_vdd": "V/V",
        "discharge_delay_ns": "ns",
        "masked_bitline_fraction_vdd": "V/V",
        "post_read_supply_current_rms_ua": "uA",
        "present_bitline_fraction_vdd": "V/V",
        "read_energy_fj": "fJ",
        "read_margin_fraction_vdd": "V/V",
        "sense_absent_fraction_vdd": "V/V",
        "sense_masked_fraction_vdd": "V/V",
        "sense_present_fraction_vdd": "V/V",
    }
    distributions = {
        metric: distribution(
            valid_samples,
            metric,
            unit,
            contract["sampling"]["quantiles"],
        )
        for metric, unit in metric_units.items()
    }
    distinct_delays = len(
        {sample["metrics"]["discharge_delay_ns"].hex() for sample in valid_samples}
    )
    distinct_margins = len(
        {
            sample["metrics"]["read_margin_fraction_vdd"].hex()
            for sample in valid_samples
        }
    )
    variation = {
        "distinct_discharge_delay_values": distinct_delays,
        "distinct_read_margin_values": distinct_margins,
        "minimum_distinct_discharge_delay_values": contract["acceptance"][
            "minimum_distinct_discharge_delay_values"
        ],
        "minimum_distinct_read_margin_values": contract["acceptance"][
            "minimum_distinct_read_margin_values"
        ],
        "status": "pass"
        if distinct_delays
        >= contract["acceptance"]["minimum_distinct_discharge_delay_values"]
        and distinct_margins
        >= contract["acceptance"]["minimum_distinct_read_margin_values"]
        else "fail",
    }
    failed = [sample for sample in results if sample["status"] != "pass"]
    status = "pass"
    if (
        len(failed) > contract["acceptance"]["sample_failures_max"]
        or len(valid_samples) != len(results)
        or replay_summary["status"] != "pass"
        or variation["status"] != "pass"
    ):
        status = "fail"
    seed_list_text = "".join(
        f"{index}:{seed}\n" for index, seed in enumerate(seeds)
    )
    summary = {
        "distributions": distributions,
        "failure_reason_counts": dict(
            sorted(Counter(reason for sample in results for reason in sample["failures"]).items())
        ),
        "same_seed_replay": replay_summary,
        "samples_failed": len(failed),
        "samples_passed": len(results) - len(failed),
        "samples_total": len(results),
        "unexpected_warning_counts": dict(
            sorted(
                Counter(
                    warning
                    for sample in results
                    for warning in sample["unexpected_warnings"]
                ).items()
            )
        ),
        "valid_measure_vectors": len(valid_samples),
        "variation_detection": variation,
    }
    result = {
        "acceptance": contract["acceptance"],
        "claim_boundary": contract["claim_boundary"],
        "contract": {
            "path": str(CONTRACT_PATH.relative_to(ROOT)),
            "sha256": sha256_file(CONTRACT_PATH),
        },
        "experiment_id": contract["experiment_id"],
        "input_model": {
            "model_mode": contract["model_mode"],
            "operating_point": contract["operating_point"],
            "sampling": {
                **contract["sampling"],
                "ordered_seed_list_sha256": sha256_text(seed_list_text),
            },
        },
        "pdk": {
            "mismatch_activation": activation,
            "model_deck_sha256": sha256_file(model_deck),
            "model_files": model_files,
            "model_scope": "installed invariant/nonfet and TT 1V8 NFET/PFET primitive files only",
            "variant": "sky130A",
        },
        "replay": replay,
        "runner": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
            "workers": workers,
        },
        "samples": results,
        "schema_version": 1,
        "status": status,
        "summary": summary,
        "template": {
            "path": contract["inputs"]["template"],
            "sha256": sha256_file(template_path),
        },
        "toolchain": {"ngspice": tool},
        "upstream": upstream,
    }
    json_path = repo_path(contract["reports"]["json"])
    markdown_path = repo_path(contract["reports"]["markdown"])
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(markdown(result), encoding="utf-8")
    print(
        f"{status.upper()}: {summary['samples_passed']}/{summary['samples_total']} "
        "fixed-seed mismatch samples passed; "
        f"same-seed replay {replay_summary['status']}",
        flush=True,
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ExtractedMismatchError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
