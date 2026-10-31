"""Fresh G4 admission needs actual child-clock coverage, independently of raw pair slack."""
import copy
import hashlib
import subprocess
from pathlib import Path
import pytest
import die_sta as D


def native_record(mode="flat"):
    one = dict(exit=0, seams={"a->b/q": {"max": dict(worst=10, neg=0), "min": dict(worst=15, neg=0)}},   # FF hold >= +10 (OWNER 12.25)
               pair_skew=dict(seam_pairs=1, intra_pairs=0, worst_abs=12, seam_over=0, intra_over=0),
               clock_endpoint_coverage=dict(verdict="PASS", status="NO_UNEXPANDED_CHILD_ETM"))
    return dict(mode=mode, corners={"TT": copy.deepcopy(one), "FF": copy.deepcopy(one)})


@pytest.mark.parametrize("mode", ["flat", "ilm"])
def test_unexpanded_child_cannot_be_g4_pass(mode):
    res = native_record(mode)
    assert D.verdict(res)["status"] == "PASS"
    res["corners"]["FF"]["clock_endpoint_coverage"] = dict(verdict="NOT RUN", status="UNEXPANDED_CHILD_ETM")
    verdict = D.verdict(res)
    assert verdict["status"].startswith("NOT RUN")
    assert verdict["setup_TT"] == 10 and verdict["hold_FF"] == 15
    assert verdict["pairskew_FF"] == 12
    assert res["corners"]["FF"]["pair_skew"]["worst_abs"] == 12
    del res["corners"]["TT"]["clock_endpoint_coverage"]
    assert D.verdict(res)["status"].startswith("NOT RUN")


def test_catalog_uses_actual_linked_masters_and_rejects_mapping_errors(tmp_path):
    fixture = r"""
set fh [open catalog.txt w]
proc all_registers {args} {return {native/CK child/CLK}}
proc get_cells {args} {return [list [lindex $args end]]}
proc get_property {inst key} {
  if {$inst eq "native/CK"} {return DFF}
  return child_ROM
}
""" + D.clock_endpoint_catalog_tcl() + "\nclose $fh\n"
    result = subprocess.run(["tclsh"], input=fixture, text=True, cwd=tmp_path,
                            capture_output=True, check=True)
    assert not result.stderr
    catalog = D.parse_sta(tmp_path / "catalog.txt")["clock_endpoint_catalog"]
    assert catalog == dict(masters=["DFF", "child_ROM"], complete=True, errors=0)
    (tmp_path / "bad.txt").write_text("CLOCK_ENDPOINT_MASTER_HEX ZZ\nCLOCK_ENDPOINT_CATALOG complete 1 errors 2\n")
    bad = D.parse_sta(tmp_path / "bad.txt")
    coverage = D.evaluate_clock_endpoint_coverage([], bad, {})
    assert coverage["status"] == "UNAVAILABLE" and coverage["verdict"] == "NOT RUN"


def test_exact_consumed_library_and_actual_master_determine_coverage(tmp_path):
    lib = tmp_path / "child_tt.lib"
    lib.write_text("""library(test) { time_unit : "1ps";
      cell(ETM) { is_macro_cell : true;
        pin(CK) { timing() { timing_type : min_clock_tree_path;
          cell_rise(scalar) { values("165.2"); } } } }
      cell(SRAM) { is_macro_cell : true;
        pin(Q) { timing() { timing_type : rising_edge;
          cell_rise(scalar) { values("376.2"); } } } }
      cell(DFF) { }
    }""")
    digest = {str(lib): hashlib.sha256(lib.read_bytes()).hexdigest()}
    def check(masters):
        return D.evaluate_clock_endpoint_coverage([str(lib)], dict(clock_endpoint_catalog=dict(
            masters=masters, complete=True, errors=0)), digest)
    assert check(["ETM"])["verdict"] == "NOT RUN"
    assert check(["SRAM", "DFF"])["verdict"] == "PASS"
    assert check(["DFF"])["models"] == []   # uninstantiated library ETM is irrelevant
    lib.write_text(lib.read_text() + "\n// changed after the STA inputs were pinned\n")
    assert check(["ETM"])["status"] == "UNAVAILABLE"


def test_etm_crosscheck_stays_information_only():
    res = native_record("etm")
    res["corners"]["TT"]["clock_endpoint_coverage"] = dict(verdict="NOT RUN")
    assert D.verdict(res)["status"].startswith("INFO")
