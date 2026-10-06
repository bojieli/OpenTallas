"""The three-machine composer refuses to publish when a lever's adoption state disagrees with the composition."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import three_machine_compose as T  # noqa: E402

COMPOSITION = T.RECOVERY / "composition.json"


def _copy_levers(tmp_path):
    shutil.copytree(T.RECOVERY / "levers", tmp_path / "levers")
    return tmp_path


def _set_verdict(rec_dir, lever, verdict, exact=None):
    for f in (rec_dir / "levers").glob("*.json"):
        r = json.loads(f.read_text())
        if r.get("lever") == lever:
            r["verdict"] = verdict
            if exact is not None:
                r["exact"] = exact
            f.write_text(json.dumps(r, indent=1))
            return
    raise AssertionError(lever)


def _adopted():
    return sorted(k for k, v in T.read_levers(T.RECOVERY / "levers").items() if v["cls"] == "adopted")


def test_guard_passes_on_committed_records():
    assert T.main(["--guard-only"]) == 0


def test_flip_adopted_lever_to_pending_refuses(tmp_path, capsys):
    lever = _adopted()[0]
    rec = _copy_levers(tmp_path)
    _set_verdict(rec, lever, "PENDING_SSFF")
    levers = T.read_levers(rec / "levers")
    assert levers[lever]["cls"] == "conditional"
    applied = json.loads(COMPOSITION.read_text())["info"]["levers"]["applied"]
    with pytest.raises(T.Refused, match=f"includes lever '{lever}' with verdict PENDING_SSFF"):
        T.guard_applied(levers, applied, "published")
    # the CLI refuses before composing anything (exit 2), for both publish and check
    for extra in ([], ["--check"]):
        assert T.main(["--recovery", str(rec), "--composition", str(COMPOSITION), "--out", str(tmp_path / "o"),
                       "--no-scoreboard", *extra]) == 2
        assert "REFUSED" in capsys.readouterr().err
    assert not (tmp_path / "o").exists()


def test_adopt_lever_missing_refuses(tmp_path):
    pending = sorted(k for k, v in T.read_levers(T.RECOVERY / "levers").items() if v["cls"] == "conditional")
    rec = _copy_levers(tmp_path)
    _set_verdict(rec, pending[0], "ADOPT")
    applied = json.loads(COMPOSITION.read_text())["info"]["levers"]["applied"]
    with pytest.raises(T.Refused, match=f"missing ADOPT lever '{pending[0]}'"):
        T.guard_applied(T.read_levers(rec / "levers"), applied, "published")


def test_adopt_without_exactness_refuses(tmp_path):
    rec = _copy_levers(tmp_path)
    _set_verdict(rec, _adopted()[0], "ADOPT", exact=False)
    with pytest.raises(T.Refused, match="must be exact"):
        T.read_levers(rec / "levers")


def test_deleted_adopted_record_refuses(tmp_path):
    lever = _adopted()[0]
    rec = _copy_levers(tmp_path)
    for f in (rec / "levers").glob("*.json"):
        if json.loads(f.read_text()).get("lever") == lever:
            f.unlink()
    applied = json.loads(COMPOSITION.read_text())["info"]["levers"]["applied"]
    with pytest.raises(T.Refused, match="record is gone"):
        T.guard_applied(T.read_levers(rec / "levers"), applied, "published")
