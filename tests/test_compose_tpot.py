"""The TPOT composer must refuse, and must refuse for the right reason.

Gate G3's measurement contract says ``tpot_s`` is composed from RTL-measured
cycles summed over the issue trace G1e certified.  A composer that emits a
number when the ladder has not closed, when an issued operator has no measured
cycle count, or when the dependent boundary is unmeasured would publish an
assumption as a measurement -- the defect this board was rebuilt to remove.

So these tests pin the refusals FIRST and in both directions: each one is
checked to fire when its condition is false AND to fall silent when it is
true, because a refusal that can never lift is as useless as one that never
fires.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("compose_tpot", ROOT / "tools/compose_tpot.py")
tpot = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(tpot)


def _write(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))


PASSING_CERT = {
    "status": "pass",
    "certificate": {
        "every_issued_instance_covered": True,
        "uncovered_instance_count": 0,
        "token_ids_match_oracle": True,
        "derived_mechanically": True,
    },
}

MEASURED_BOUNDARY = {
    "calibration": {
        "boundary": {"measured": True, "rtl_measured_boundary_cycles": 44},
        "clock": {"frequency_hz": 1e9},
    }
}

CENSUS_ROW = {"family": 16, "sub": 2, "descriptor_id": 32, "instances": 3}


def _record(**over) -> dict:
    body = {
        "storage_class": "rom",
        "workload_id": "TA-QW-EOS-1",
        "trace": {"equals_golden": True, "divergence_index": None},
        "issue_census": {"rows": [dict(CENSUS_ROW)], "classes": 1, "instances": 3},
    }
    body.update(over)
    return body


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(tpot, "REPO", tmp_path)
    monkeypatch.setattr(tpot, "CERTIFICATE", tmp_path / "cert.json")
    monkeypatch.setattr(tpot, "TRACE", tmp_path / "trace.json")
    monkeypatch.setattr(tpot, "CALIBRATION", tmp_path / "calib.json")
    monkeypatch.setattr(tpot, "BUDGET", tmp_path / "budget.json")
    return tmp_path


# --- the certificate ------------------------------------------------------

def test_a_failing_certificate_refuses(repo):
    _write(tpot.CERTIFICATE, {"status": "fail",
                              "certificate": {"every_issued_instance_covered": False,
                                              "uncovered_instance_count": 1095,
                                              "token_ids_match_oracle": False}})
    got = tpot.certificate_refusal()
    assert got is not None
    assert got["category"] == "certificate_failing"
    assert "1,095" in got["why"]


def test_an_absent_certificate_refuses_rather_than_passing_vacuously(repo):
    got = tpot.certificate_refusal()
    assert got is not None and got["category"] == "certificate_absent"


def test_a_certificate_that_covers_every_instance_does_not_refuse(repo):
    _write(tpot.CERTIFICATE, PASSING_CERT)
    assert tpot.certificate_refusal() is None


def test_a_certificate_passing_but_leaving_instances_uncovered_still_refuses(repo):
    """status alone is not enough: the arithmetic has to hold too."""
    body = json.loads(json.dumps(PASSING_CERT))
    body["certificate"]["uncovered_instance_count"] = 7
    body["certificate"]["every_issued_instance_covered"] = False
    _write(tpot.CERTIFICATE, body)
    got = tpot.certificate_refusal()
    assert got is not None and got["category"] == "certificate_failing"


# --- the dependent boundary ----------------------------------------------

def test_an_unmeasured_boundary_refuses(repo):
    _write(tpot.CALIBRATION, {"calibration": {"boundary": {
        "measured": False, "rtl_measured_boundary_cycles": None,
        "why_unmeasured": "this record is a STRUCTURAL probe, not a boundary measurement"}}})
    got = tpot.boundary_refusal()
    assert got is not None
    assert got["category"] == "boundary_unmeasured"
    assert "STRUCTURAL probe" in got["why"]


def test_a_measured_boundary_does_not_refuse(repo):
    _write(tpot.CALIBRATION, MEASURED_BOUNDARY)
    assert tpot.boundary_refusal() is None


def test_a_boundary_claiming_measured_with_no_cycles_still_refuses(repo):
    """The flag is not the measurement; the cycle count is."""
    _write(tpot.CALIBRATION, {"calibration": {"boundary": {
        "measured": True, "rtl_measured_boundary_cycles": None}}})
    assert tpot.boundary_refusal() is not None


# --- the trace and its coverage -------------------------------------------

def test_a_diverging_trace_refuses(repo):
    got = tpot.trace_refusal(_record(trace={"equals_golden": False, "divergence_index": 41}))
    assert got is not None and got["category"] == "trace_uncertified"


def test_an_equal_trace_does_not_refuse(repo):
    assert tpot.trace_refusal(_record()) is None


def test_a_class_with_no_measured_cycles_refuses_and_counts_the_instances(repo):
    got = tpot.coverage_refusal(_record(), measured={})
    assert got is not None
    assert got["category"] == "operator_cycles_unmeasured"
    assert "3 issued instance(s)" in got["why"]


def test_coverage_does_not_refuse_once_every_class_is_measured(repo):
    measured = {(16, 2, 32): 100}
    assert tpot.coverage_refusal(_record(), measured) is None


def test_a_partially_measured_trace_still_refuses(repo):
    """One measured class out of two is not a measurement of the workload."""
    rec = _record(issue_census={"rows": [dict(CENSUS_ROW),
                                         {"family": 48, "sub": 1, "descriptor_id": 99,
                                          "instances": 5}]})
    got = tpot.coverage_refusal(rec, measured={(16, 2, 32): 100})
    assert got is not None
    assert "1 of 2" in got["why"]
    assert "5 issued instance(s)" in got["why"]


def test_an_absent_census_refuses(repo):
    got = tpot.coverage_refusal(_record(issue_census={}), measured={})
    assert got is not None and got["category"] == "trace_census_absent"


# --- the happy path, which must be reachable ------------------------------

def test_the_composition_is_the_sum_over_the_certified_trace(repo):
    """A rung that cannot pass hides the work as surely as one that cannot fail."""
    got = tpot.compose(_record(), boundary_cycles=44, clock_hz=1e9,
                       measured={(16, 2, 32): 100})
    assert got["operator_cycles"] == 300           # 100 cycles x 3 instances
    assert got["boundary_count"] == 3
    assert got["boundary_cycles_total"] == 132     # 44 x 3
    assert got["total_cycles"] == 432
    assert got["tpot_s"] == pytest.approx(432e-9)


def test_the_composition_scales_with_the_clock(repo):
    a = tpot.compose(_record(), 44, 1e9, {(16, 2, 32): 100})
    b = tpot.compose(_record(), 44, 2e9, {(16, 2, 32): 100})
    assert a["total_cycles"] == b["total_cycles"]
    assert b["tpot_s"] == pytest.approx(a["tpot_s"] / 2)


# --- the live repository --------------------------------------------------

def test_the_live_repository_refuses_today_and_names_why():
    """Not a synthetic case: the real artifacts, read as they stand.

    This is the test that would start failing the day the ladder closes, and
    it is meant to: at that point the refusal list is the work that remains.
    """
    result = tpot.compose_all()
    assert result["composed_count"] == 0, "a row composed -- update this test and the gate"
    categories = {r["category"] for row in result["rows"] for r in row["refusals"]}
    assert "certificate_failing" in categories
    assert "boundary_unmeasured" in categories
    assert result["refused_count"] == len(result["rows"])


def test_no_tpot_record_is_written_for_a_refused_row(tmp_path):
    """The gate globs results/tpot/*.json, so a refused row must leave nothing."""
    out = tmp_path / "tpot"
    tpot.main(["--out", str(out)])
    assert not list(out.glob("*.json")), "a refused row wrote a record the gate would read"
