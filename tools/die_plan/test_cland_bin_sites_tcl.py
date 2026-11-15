import json
import shutil
import subprocess

import pytest

import cland_bin_sites_tcl as C

DOC = {"schema": C.SCHEMA, "types": {"cbf_q01": {
    "bc_i02": {"u_bin": [43.2, 233.28], "u_st": [43.2, 483.84], "route_um": 728.8, "equal_hop_um": 242.9, "plan_stations": 0},
    "bc_i12": {"u_bin": [648.0, 224.64], "u_st": [648.0, 475.2]}}}}


def test_table_has_u_st_under_the_bus_and_u_bin_under_bus_colon_bin():
    t = C.table(DOC, "cbf_q01")
    assert " bc_i02 {43.200 483.840}" in t and " bc_i02:bin {43.200 233.280}" in t and t.startswith("set cland_bin_sites {")


def test_type_suffix_falls_back_and_unknown_type_is_empty():
    assert C.table(DOC, "cbf_q01__cl123abc")
    assert C.table(DOC, "cbn_q99") == ""


@pytest.mark.parametrize("bad", [{"schema": "x", "types": {}}, {"schema": C.SCHEMA, "types": {"t": {"b": {"u_st": [1]}}}},
                                 {"schema": C.SCHEMA, "types": {"t": {"b x": {"u_st": [1, 2]}}}},
                                 {"schema": C.SCHEMA, "types": {"t": {"b": {"u_st": [float("nan"), 2]}}}}])
def test_bad_input_fails_closed(bad):
    with pytest.raises(ValueError):
        C.table(bad, "t")


def test_sidecar_path_and_for_kit(tmp_path):
    plan = tmp_path / "zz_s4k.json"; plan.write_text("{}")
    assert C.sidecar_path(plan).name == "zz_s4k.cland_bin_sites.json"
    assert C.for_kit(plan, "cbf_q01") == ""
    C.sidecar_path(plan).write_text(json.dumps(DOC))
    assert "bc_i12:bin" in C.for_kit(plan, "cbf_q01") and C.for_kit(None, "cbf_q01") == ""


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_tcl_reads_it_back():
    body = C.table(DOC, "cbf_q01") + "puts [dict get $cland_bin_sites bc_i02:bin]\nputs [dict size $cland_bin_sites]\n"
    assert subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split("\n")[:2] == ["43.200 233.280", "4"]


def test_u_bin_only_bus_gives_only_the_bin_key():
    doc = {"schema": C.SCHEMA, "types": {"slw_fw_v2": {"fw_i00": {"u_bin": [10.0, 20.5]}}}}
    t = C.table(doc, "slw_fw_v2")
    assert " fw_i00:bin {10.000 20.500}" in t and "fw_i00 {" not in t
