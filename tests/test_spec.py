from __future__ import annotations

from pathlib import Path

from tools.check_spec import generate_traceability, validate
from tools.rtl_implementation_campaign import (
    equivalence_script,
    mapping_profile,
    sanitize_netlist,
    strict_json,
    validate_spec,
    yosys_script,
)
from tools.run_clean_rtl_implementation_replay import verify_existing_replay


ROOT = Path(__file__).resolve().parents[1]


def test_specification_gate_and_traceability_are_current() -> None:
    generated = validate()
    checked_in = (ROOT / "spec" / "TRACEABILITY.md").read_text(encoding="utf-8")
    assert generated == checked_in


def test_traceability_generation_is_byte_deterministic() -> None:
    import json

    requirements = json.loads(
        (ROOT / "spec" / "requirements.json").read_text(encoding="utf-8")
    )["requirements"]
    checks = json.loads(
        (ROOT / "spec" / "verification.json").read_text(encoding="utf-8")
    )["planned_checks"]
    assert generate_traceability(requirements, checks) == generate_traceability(
        requirements, checks
    )


def test_qwen_dense_control_is_in_frozen_manifest() -> None:
    import json

    manifest = json.loads((ROOT / "spec" / "manifest.json").read_text(encoding="utf-8"))
    qwen = next(item for item in manifest["models"] if item["name"] == "Qwen3-8B")
    assert qwen["role"] == "dense_control"
    assert qwen["stages_midpoint"] == 1
    assert qwen["study_context_tokens"] == [8192]


def test_fault_campaign_is_source_complete() -> None:
    import json

    campaign = json.loads(
        (ROOT / "spec" / "fault_campaign.json").read_text(encoding="utf-8")
    )
    assert campaign["planned_site_count"] == 87
    assert len(campaign["sites"]) == 87
    assert len({site["id"] for site in campaign["sites"]}) == 87
    assert len(campaign["required_simulators"]) == 2
    assert campaign["external_gates"]


def test_implementation_proxy_has_closed_physical_gate_contract() -> None:
    implementation = strict_json(ROOT / "spec" / "implementation_proxy.json")
    validate_spec(implementation)
    acceptance = implementation["acceptance"]
    physical = set(acceptance["physical_proxy_required_cases"])
    assert physical == {"numeric_e1_l4", "stage_reduced"}
    assert set(acceptance["postroute_equivalence_required_cases"]) == physical
    assert acceptance["physical_setup_violations_max"] == 0
    assert acceptance["physical_hold_violations_max"] == 0
    assert acceptance["physical_drc_errors_max"] == 0
    assert acceptance["physical_flow_errors_max"] == 0
    assert implementation["constraints"]["max_fanout"] == 32
    assert implementation["physical_flow_policy"]["orfs_kepler_lec"]["enabled"] is False
    postroute = implementation["physical_flow_policy"]["postroute_equivalence"]
    assert postroute["arbitrary_common_initial_state_required"] is True
    assert postroute["private_state_symbol_remaps_max"] == 8
    assert (
        implementation["warning_policy"]["openroad"]["unexpected_codes_are_fatal"]
        is True
    )


def test_large_mapping_exception_is_exact_bounded_and_nonphysical(
    tmp_path: Path,
) -> None:
    implementation = strict_json(ROOT / "spec" / "implementation_proxy.json")
    policy = implementation["large_case_mapping_policy"]
    assert policy["case_names"] == ["numeric_e16_l16"]
    assert policy["abc_script"] == "strash; &get -n; &nf; &put"
    assert policy["outer_process_timeout_seconds"] == 300
    large = next(
        case for case in implementation["cases"] if case["name"] == "numeric_e16_l16"
    )
    assert large["equivalence"] == "scaling_only"
    assert large["physical_proxy"] is None
    bounded = mapping_profile(large, implementation)
    bounded_script = yosys_script(large, tmp_path, bounded)
    assert bounded["profile_id"] == "bounded_structural_liberty_v1"
    assert bounded["qor_comparable_to_default_profile"] is False
    assert "abc -liberty " in bounded_script
    assert '-script "+strash; &get -n; &nf; &put"' in bounded_script
    assert "-D 10000" not in bounded_script
    for case in implementation["cases"]:
        if case["name"] == "numeric_e16_l16":
            continue
        default = mapping_profile(case, implementation)
        default_script = yosys_script(case, tmp_path, default)
        assert default["profile_id"] == "default_delay_oriented"
        assert default["outer_process_timeout_seconds"] is None
        assert "-D 10000" in default_script
        assert "&nf" not in default_script


def test_implementation_evidence_state_is_explicit() -> None:
    verification = strict_json(ROOT / "spec" / "verification.json")
    campaign = verification["implementation_campaign"]
    assert campaign["result_status"] in {"pending_governed_run", "closed"}
    result_paths = [ROOT / path for path in campaign["result_paths"]]
    if campaign["result_status"] == "pending_governed_run":
        assert not any(path.exists() for path in result_paths)
    else:
        assert all(path.is_file() for path in result_paths)
        result = strict_json(result_paths[0])
        assert result["status"] == "pass"
        assert result["baseline"]["dirty_paths"] == []
        assert all(result["canonical_eligibility"].values())
        replay_contract = campaign["clean_replay"]
        replay_paths = [ROOT / path for path in replay_contract["result_paths"]]
        assert replay_contract["required"] is True
        assert all(path.is_file() for path in replay_paths)
        replay = strict_json(replay_paths[0])
        assert replay["status"] == "pass"
        assert replay["run_fingerprint"] == result["run_fingerprint"]
        assert replay["summary"] == result["summary"]
        assert replay["verified_case_artifacts"] == 386
        assert all(replay["comparisons"].values())


def test_promoted_clean_replay_contract_is_nonmutating_and_verifiable() -> None:
    verified = verify_existing_replay(verify_case_files=False)
    assert verified["status"] == "pass"
    assert verified["run_fingerprint"] == "87e057764094b9ed"
    assert verified["verified_case_artifacts"] == 386
    assert verified["clean_snapshot"]["commit"] == (
        "34a0d2ec791a1344a5db96f0123e5d02d57d02ab"
    )


def test_program_plan_header_tracks_current_gate_state() -> None:
    plan = (ROOT / "rom-inference-program-plan.md").read_text(encoding="utf-8")
    header = plan.split("## Execution-status addendum", maxsplit=1)[0]
    normalized = " ".join(header.split())
    assert "implementation/verification in progress" not in normalized
    assert "implementation-proxy campaigns are" in normalized
    assert "COMP-01" in normalized
    assert "product architecture freeze" in normalized
    assert "product silicon remain on hold" in normalized


def test_generic_equivalence_normalizes_async_reset_cells_before_induction() -> None:
    implementation = strict_json(ROOT / "spec" / "implementation_proxy.json")
    case = next(item for item in implementation["cases"] if item["kind"] == "numeric")
    commands = equivalence_script(case).splitlines()
    assert commands.count("async2sync") == 1
    assert commands.index("async2sync") < next(
        index
        for index, command in enumerate(commands)
        if command.startswith("equiv_opt ")
    )


def test_structural_netlist_sanitizer_only_removes_signed_declarations(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.v"
    destination = tmp_path / "destination.v"
    source.write_text(
        "module m(input signed [3:0] a, output signed [3:0] y);\n"
        "wire signed [3:0] n;\n"
        "assign n = a;\n"
        "assign y = n;\n"
        "endmodule\n",
        encoding="utf-8",
    )
    assert sanitize_netlist(source, destination) == 3
    assert destination.read_text(encoding="utf-8") == (
        "module m(input [3:0] a, output [3:0] y);\n"
        "wire [3:0] n;\n"
        "assign n = a;\n"
        "assign y = n;\n"
        "endmodule\n"
    )
