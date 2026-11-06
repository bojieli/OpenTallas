import json

import pytest

import signoff


def declaration(tmp_path, names):
    (tmp_path / "straps.json").write_text(json.dumps({"straps": names}))
    return str(tmp_path)


def test_declared_and_explicitly_false_pathed_only(tmp_path):
    kit = declaration(tmp_path, ["strap_row0", "strap_ten"])
    sdc = "set_false_path -from [get_ports {strap_row0 dynamic}]\n"
    assert signoff.declared_static_straps(kit, sdc) == ["strap_row0"]
    assert signoff.declared_static_straps(kit, "set_false_path -from [get_ports {strap_*}]") == []
    assert signoff.declared_static_straps(kit, "") == []
    assert signoff.declared_static_straps(None, sdc) == []


def test_invalid_declaration_fails(tmp_path):
    kit = declaration(tmp_path, ["ordinary_data"])
    with pytest.raises(ValueError):
        signoff.declared_static_straps(kit, "set_false_path -from [get_ports {ordinary_data}]")


def test_observer_has_no_timing_exceptions_or_case_analysis():
    assert signoff.static_strap_tcl([]) == ""
    tcl = signoff.static_strap_tcl(["strap_row0"])
    assert "set_false_path" not in tcl
    assert "set_case_analysis" not in tcl
    assert "-trace_arcs all" in tcl
    assert "-startpoints_only" in tcl


def test_only_proven_listed_endpoints_are_removed():
    text = "Warning: There are 3 unconstrained endpoints.\n  qstrap/D\n  qdynamic/D\n  ft_o\n"
    result = signoff.check_setup_counts(text, ["ft_o"], ["qstrap/D", "not_listed/D", "ft_o"])
    assert result["unconstrained"] == 1
    assert result["static_strap_endpoints"] == 1
    assert result["ft_die_timed"] == 1


def test_missing_evidence_retains_failure_and_other_gates():
    text = "Warning: There are 2 unconstrained endpoints.\n  qs/D\n  qd/D\nWarning: There is 1 register/latch pin with no clock.\nWarning: There are 2 combinational loops.\n"
    result = signoff.check_setup_counts(text)
    assert result["unconstrained"] == 2
    assert result["unclocked"] == 1
    assert result["loops"] == 2


def test_raw_count_and_exact_proven_names_remain_in_record():
    log = "SO_STATIC_STRAP_ENDPOINT qstrap/D\nSO_PATH_BEGIN CHECK_SETUP\nWarning: There are 2 unconstrained endpoints.\n  qstrap/D\n  qdynamic/D\nSO_PATH_END\n"
    parsed = signoff.parse_session(log)
    result = signoff.corner_result(parsed)
    assert result["check_setup"]["unconstrained"] == 1
    assert result["static_strap_endpoints"] == ["qstrap/D"]
    assert "There are 2 unconstrained" in parsed["blocks"]["CHECK_SETUP"]
