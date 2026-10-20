"""Admission must execute the native collector, never trust caller receipts."""
import json
from pathlib import Path
import subprocess
from unittest.mock import patch
import pytest
import pg_receipt as pg


@pytest.fixture
def fixture(tmp_path):
    odb = tmp_path / "6_final.odb"
    odb.write_bytes(b"exact-active-odb")
    (tmp_path / "6_final.spef").write_text('*SPEF "ieee 1481-1999"\n*DESIGN "native_block"\n')
    collector = tmp_path / "audit_native_pg.tcl"
    collector.write_text("native-entry")
    (tmp_path / "native_pg_binding.tcl").write_text("native-census")
    executable = tmp_path / "openroad"
    executable.write_text("actual executable hash")
    executable.chmod(0o755)
    return odb, collector, executable, tmp_path / "receipts"


def audit():
    return dict(schema="native_pg_audit.v1", status="PASS", block="native_block", instance_count=1,
                pg_master_count=1, checked=2, roles={"POWER": 1, "GROUND": 1},
                failure_count=0, failures=[], mapping_error="", regions=[],
                domain_rules=[dict(inst_pattern=".*", pin_pattern="VP", net="rail", role="POWER", region=""),
                              dict(inst_pattern=".*", pin_pattern="VG", net="return", role="GROUND", region="")])


def run(fixture, payload, exitcode=0, mutate=None):
    odb, collector, executable, receipt_dir = fixture
    def execute(argv, **kw):
        assert argv == [str(executable), "-exit", str(collector)]
        target = Path(kw["env"]["OT_PG_AUDIT_REPORT"])
        assert not target.exists()
        target.write_text(json.dumps(payload))
        if mutate:
            mutate()
        return subprocess.CompletedProcess(argv, exitcode)
    with patch.object(pg.subprocess, "run", side_effect=execute) as calls:
        result = pg.require_native_pg(odb, collector=collector, openroad=str(executable), receipt_dir=receipt_dir)
        assert calls.call_count == 1
        return result


def test_exact_pass_and_every_call_fresh(fixture):
    first = run(fixture, audit())
    second = run(fixture, audit())
    assert first["transaction"] != second["transaction"]
    assert first["odb_sha256"] == second["odb_sha256"]
    assert len(first["source_dependencies"]) == 3
    assert first["binding_scope"] == pg.SCOPE
    assert first["domain_rules_sha256"]


def test_forged_saved_zero_failure_receipt_is_never_admission(fixture):
    odb, _, _, receipt_dir = fixture
    receipt_dir.mkdir()
    forged = dict(schema=pg.SCHEMA, status="PASS", odb_sha256=pg._sha(odb), checked=2,
                  roles={"POWER": 1, "GROUND": 1}, failure_count=0,
                  domain_rules_sha256="copied-rules-hash", source_dependencies={})
    old = receipt_dir / "receipt.json"
    old.write_text(json.dumps(forged))
    before = old.read_bytes()
    payload = audit()
    payload.update(status="FAIL", failure_count=1, failures=[{"reason": "OT_PG_FINAL_BINDING"}])
    with pytest.raises(pg.PGRefused, match="binding FAIL"):
        run(fixture, payload, exitcode=2)
    assert old.read_bytes() == before
    failures = list(receipt_dir.glob("audit-*/receipt.json"))
    assert len(failures) == 1 and json.loads(failures[0].read_text())["status"] == "REFUSED"


@pytest.mark.parametrize("mutation", [
    {"checked": 0}, {"checked": 3}, {"pg_master_count": 0},
    {"instance_count": 0}, {"roles": {"POWER": 2}},
    {"failure_count": 1}, {"domain_rules": []},
    {"mapping_error": "ambiguous actual domain"}, {"status": "FAIL"},
])
def test_native_result_not_summarized_away(fixture, mutation):
    payload = audit()
    payload.update(mutation)
    with pytest.raises(pg.PGRefused):
        run(fixture, payload)


def test_nonzero_native_exit_refuses_even_pass_json(fixture):
    with pytest.raises(pg.PGRefused, match="exited nonzero"):
        run(fixture, audit(), exitcode=2)


@pytest.mark.parametrize("target", [0, 1, 2])
def test_odb_or_executed_sources_mutated_during_audit_refuse(fixture, target):
    odb, collector, _, _ = fixture
    path = (odb, collector, collector.parent / "native_pg_binding.tcl")[target]
    with pytest.raises(pg.PGRefused, match="changed during"):
        run(fixture, audit(), mutate=lambda: path.write_bytes(b"changed"))


def test_missing_native_output_and_symlink_refuse(fixture):
    odb, collector, executable, receipt_dir = fixture
    with patch.object(pg.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
        with pytest.raises(pg.PGRefused, match="no fresh regular audit"):
            pg.require_native_pg(odb, collector=collector, openroad=str(executable), receipt_dir=receipt_dir)


def test_final_admission_rejects_placement_parasitic_model(fixture):
    odb, collector, executable, receipt_dir = fixture
    with pytest.raises(pg.PGRefused, match="routed_extracted"):
        pg.require_native_pg(odb, collector=collector, openroad=str(executable), receipt_dir=receipt_dir,
                             parasitic_model="placement")


def test_wrong_spef_design_refuses_native_pass(fixture):
    payload = audit()
    payload["block"] = "different_native_block"
    with pytest.raises(pg.PGRefused, match="SPEF DESIGN mismatches"):
        run(fixture, payload)


def test_spef_changed_during_native_audit_refuses(fixture):
    spef = fixture[0].parent / "6_final.spef"
    with pytest.raises(pg.PGRefused, match="SPEF changed"):
        run(fixture, audit(), mutate=lambda: spef.write_text("changed"))


def test_missing_spef_never_qualified(fixture):
    odb, collector, executable, receipt_dir = fixture
    (odb.parent / "6_final.spef").unlink()
    with pytest.raises(FileNotFoundError):
        pg.require_native_pg(odb, collector=collector, openroad=str(executable), receipt_dir=receipt_dir)
