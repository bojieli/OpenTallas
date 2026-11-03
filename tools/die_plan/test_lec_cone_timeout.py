"""LEC-CONE-TIMEOUT (FLOW-22 11-02): a hung per-cone ABC batch is bisected to the hung cone, which stays undecided."""
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
import lec


def fake_runner(hung, calls, flush=False):
    """ABC that answers each cone 'equivalent' (odd ids: NOT EQUIVALENT) and never returns on a hung cone."""
    def run(abc, sf, limit):
        ids = [int(i) for i in re.findall(r"&cone -O (\d+)", Path(sf).read_text())]
        calls.append((ids, limit))
        out = []
        for i in ids:
            if i in hung:
                return ("\n".join(out) if flush else ""), True     # killed: buffered text lost unless flushed
            out.append("Networks are NOT EQUIVALENT" if i % 2 else "Networks are equivalent")
        return "\n".join(out), False
    return run


def expect(ids, hung):
    return ["undecided" if i in hung else "differs" if i % 2 else "proved" for i in ids]


def test_hung_cone_bisected_to_undecided(tmp_path):
    ids, hung, calls, log = list(range(10, 26)), {13}, [], []
    res = lec.cone_batch("abc", tmp_path / "s.aig", tmp_path, "t", ids, "-m", 100, log, limit=5,
                         runner=fake_runner(hung, calls))
    assert res == expect(ids, hung)
    assert any(c == ([13], 5 + lec.CONE_BUDGET_S) for c in calls)          # the hung cone ran alone, then gave up
    assert any("LEC CONE TIMEOUT t output 13" in x for x in log)
    assert len(calls) <= 2 * 5 + 1                                          # log2 bisection, not one run per cone


def test_partial_output_kept_and_two_hung_cones(tmp_path):
    ids, hung, calls = list(range(0, 9)), {2, 7}, []
    res = lec.cone_batch("abc", tmp_path / "s.aig", tmp_path, "t", ids, "-n -m", 10, [], limit=1,
                         runner=fake_runner(hung, calls, flush=True))
    assert res == expect(ids, hung)
    assert calls[1][0] == ids[2:6]                                         # 0, 1 answered before the hang: kept


def test_no_limit_is_old_behaviour(tmp_path):
    calls = []
    res = lec.cone_batch("abc", tmp_path / "s.aig", tmp_path, "t", [0, 1], "-m", 10, [], limit=0,
                         runner=fake_runner(set(), calls))
    assert res == ["proved", "differs"] and calls == [([0, 1], None)]


def test_env_limit_and_real_subprocess_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_LEC_CONE_S", "7")
    assert lec.cone_limit_s() == 7.0
    monkeypatch.setenv("OT_LEC_CONE_S", "junk")
    assert lec.cone_limit_s() == lec.CONE_S_DEFAULT
    sf = tmp_path / "x.abc"; sf.write_text("")
    def run(cmd, **kw):
        assert kw["timeout"] == 3
        raise subprocess.TimeoutExpired(cmd, 3, output=b"Networks are equivalent\n", stderr=None)
    monkeypatch.setattr(lec.subprocess, "run", run)
    assert lec.run_abc_script("abc", sf, 3) == ("Networks are equivalent\n", True)


def test_prove_marks_hung_cone_undecided_never_proved(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "xor_sat", lambda *a: {})
    m = lec.Aig()
    x = m.add_input("x")
    m.outs, m.onames = [x, x, x], ["a", "hung", "c"]
    monkeypatch.setattr(lec, "abc_bin", lambda: "fake-abc")
    monkeypatch.setattr(lec, "aig_outputs", lambda p: [2, 2, 2])
    monkeypatch.setattr(lec, "lit_val", lambda *a: 0)
    monkeypatch.setenv("OT_LEC_CONE_S", "1")

    def run(args, **kw):
        script = Path(args[-1]).read_text() if args[1] == "-f" else args[-1]
        if "&fraig" in script:
            (tmp_path / "h_swept.aig").touch()
            return SimpleNamespace(stdout="Undef calls 3", stderr="")
        ids = [int(i) for i in re.findall(r"&cone -O (\d+)", script)]
        if 1 in ids:
            assert kw.get("timeout")
            raise subprocess.TimeoutExpired(args, kw["timeout"], output=None)
        return SimpleNamespace(stdout="\n".join("Networks are equivalent" for _ in ids), stderr="")
    monkeypatch.setattr(lec.subprocess, "run", run)
    assert lec.prove(m, tmp_path, 100, [], tag="h") == {"a": "proved", "hung": "undecided", "c": "proved"}
