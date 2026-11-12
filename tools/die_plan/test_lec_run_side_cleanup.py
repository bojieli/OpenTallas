"""DISK-1111: lec.run_side removes <side>.preicg.json / <side>.icg.json on every exit (success, phase-A failure,
icg_to_enable failure, phase-B failure), so a failed LEC does not leave ~3 GB per job in the ot-run work dir.
    python3 -m pytest -q tools/die_plan/test_lec_run_side_cleanup.py
Pure unit test: yosys, docker and the ORFS image are replaced by stubs."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402


class _Stub:
    def __init__(self, out, fail_at=None):
        self.out, self.fail_at, self.calls = out, fail_at, []

    def run_yosys(self, script, ys, log):
        phase = "B" if str(ys).endswith("_b.ys") else "A"
        self.calls.append(phase)
        if phase == "A":                                   # phase A writes the big JSON
            (self.out / "gold.preicg.json").write_text("x" * 1000)
        if self.fail_at == phase:
            raise lec.Unproven(f"stub phase {phase} failure")
        return "ok-" + phase

    def icg_to_enable(self, pre, icg, side):
        self.calls.append("icg")
        Path(icg).write_text("y" * 1000)
        if self.fail_at == "icg":
            raise lec.Unproven("stub icg failure")
        return {"gates": 1}


def _patch(monkeypatch, st, split):
    monkeypatch.setattr(lec, "run_yosys", st.run_yosys)
    monkeypatch.setattr(lec, "icg_to_enable", st.icg_to_enable)
    monkeypatch.setattr(lec, "split_seq", lambda env: split)
    monkeypatch.setattr(lec, "seq_tail_b", lambda pre, lecff: "script-b")


def _left(out):
    return sorted(p.name for p in out.glob("*.json"))


def test_success_removes_both_jsons(tmp_path, monkeypatch):
    st = _Stub(tmp_path)
    _patch(monkeypatch, st, True)
    rec = {}
    assert lec.run_side({}, "s", tmp_path, "gold", [], rec) == "ok-B"
    assert st.calls == ["A", "icg", "B"] and rec["clock_gates"]["gold"] == {"gates": 1}
    assert _left(tmp_path) == []


@pytest.mark.parametrize("fail_at", ["A", "icg", "B"])
def test_failure_at_any_phase_removes_both_jsons(tmp_path, monkeypatch, fail_at):
    st = _Stub(tmp_path, fail_at)
    _patch(monkeypatch, st, True)
    with pytest.raises(lec.Unproven):
        lec.run_side({}, "s", tmp_path, "gold", [], {})
    assert _left(tmp_path) == []


def test_no_clock_gates_single_run_untouched(tmp_path, monkeypatch):
    st = _Stub(tmp_path)
    _patch(monkeypatch, st, False)
    (tmp_path / "gold.aliases.json").write_text("{}")      # kept: replay tools read it
    assert lec.run_side({}, "s", tmp_path, "gold", [], {}) == "ok-A"
    assert st.calls == ["A"]
    assert _left(tmp_path) == ["gold.aliases.json"]


def test_aliases_json_survives_split_failure(tmp_path, monkeypatch):
    st = _Stub(tmp_path, "B")
    _patch(monkeypatch, st, True)
    (tmp_path / "gold.aliases.json").write_text("{}")
    with pytest.raises(lec.Unproven):
        lec.run_side({}, "s", tmp_path, "gold", [], {})
    assert _left(tmp_path) == ["gold.aliases.json"]
