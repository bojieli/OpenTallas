"""bind_emit_par: forked per-type emit == the serial loop (state, files, output order), unsafe forms fall back (FABLE-PIPELINE-R1)."""
import copy
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_emit_par as EP  # noqa: E402


class Err(Exception):
    pass


class Rec:
    def __init__(self, d):
        self.d = d


class PlanRec:
    """schema.Plan as clock_landings._physical_clock_plan memoises it: plain attributes + a per-type cache it fills lazily"""

    def __init__(self, raw):
        self.raw = raw
        self.W = 100.0
        self._reset_tree_cache = {}

    def taps(self, tn):
        return self._reset_tree_cache.setdefault(("sites", tn), [len(tn), self.W])


class Glue:
    """an object that does not pickle (holds a lambda) with nested state the type passes mutate in place (Binder.pc.efs_rec)"""

    def __init__(self):
        self.files = []
        self.rec = {"types": {}}
        self.fn = lambda x: x
        self.B = None                                  # back reference to the Binder (Binder.pc.B)
        self.memo = None
        self._plan = None


class Fake:
    """the shapes Binder.emit's per-type body uses: dict-of-type receipts, shared error list (aliased), nested io maps, an object
    with a growing list, a large read-only netlist"""

    def __init__(self, n=7, big=False):
        self.by_type = {f"t{i}": [f"p{i}a", f"p{i}b"] for i in range(n)}
        self.members = {f"p{i}a": list(range(i)) for i in range(n)}
        self.errors = []
        self.alias = self.errors                       # Graph(F, rules, errors) keeps the same list
        self.pnames = {}
        self.io_used = {}
        self.seen = set()
        self.glue = Glue()
        self.glue.B = self
        self.F = {"cells": {i: {"x": i} for i in range(200000 if big else 10)}}
        self.fail = None
        self._memo = None
        self.stats = {"cells_emitted": 5, "name": "x"}
        self.level = None

    def _emit_one(self, tn, ps, out, files):
        print(f"emit {tn}")
        if self.fail == tn:
            raise Err(f"gap in {tn}")
        f = Path(out) / f"{tn}.sv"
        f.write_text(f"module {tn}; // {len(self.members.get(ps[0], []))}\nendmodule\n")
        self.pnames[tn] = {"clk": ps[0]}
        for p in ps:
            self.io_used.setdefault(p, {})[tn] = [1, 2]
        self.seen.add(tn)
        self.stats["cells_emitted"] += len(ps) + int(tn[1:])
        self.stats["wires_emitted"] = self.stats.get("wires_emitted", 0) + 3       # a count the first type creates
        if self._memo is None:                         # a lazily computed die-wide value (Binder.bump_pins): the same in every worker
            self._memo = {"ports": {"S": ["link", "far"]}}
        if getattr(self, "_memo2", None) is None:
            self._memo2 = ["a", "b"]
        self.glue.files.append(str(f) + ".glue")
        self.glue.rec["types"][tn] = len(ps)
        if self.glue.memo is None:                     # lazily built record object without __eq__, the same in every worker
            self.glue.memo = Rec({"taps": [1, 2, 3]})
        if self.glue._plan is None:                    # a lazily built schema.Plan each worker fills with its own type's cache entries
            self.glue._plan = PlanRec({"die": "x"})
        self.glue._plan.taps(tn)
        self.__dict__.setdefault("_receipts", {})[tn] = dict(n=len(ps))
        if tn.endswith(("1", "4")):
            self.errors.append(f"WARN {tn}")
        self.F["cells"][0]["x"] == 0                    # read-only use of the big netlist
        if self.level is not None:
            self.level += 1
        files.append(f)


def serial(B, out):
    files = []
    for tn, ps in sorted(B.by_type.items()):
        B._emit_one(tn, ps, out, files)
    return files


def state(B):
    d = {k: v for k, v in B.__dict__.items() if k not in ("F", "glue", "alias")}
    d["glue_rec"] = B.glue.rec
    d["glue_memo"] = B.glue.memo.d if B.glue.memo else None
    d["glue_plan"] = (B.glue._plan.raw, B.glue._plan.W, B.glue._plan._reset_tree_cache) if B.glue._plan else None
    d["glue_files"] = [Path(x).name for x in B.glue.files]
    d["alias_is_errors"] = B.alias is B.errors
    return copy.deepcopy(d)


@pytest.mark.parametrize("j,big", [(2, False), (4, False), (3, True)])
def test_parallel_equals_serial(tmp_path, capfd, j, big, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    a, b = Fake(big=big), Fake(big=big)
    monkeypatch.setattr(EP, "DEEP_MAX", 1 << 20)
    (tmp_path / "s" / "rtl").mkdir(parents=True)
    (tmp_path / "p" / "rtl").mkdir(parents=True)
    fs = serial(a, tmp_path / "s" / "rtl")
    out_s = capfd.readouterr().out
    fp = []
    rec = EP.run(b, tmp_path / "p" / "rtl", fp, j)
    out_p = capfd.readouterr().out
    assert state(a) == state(b)
    assert [f.name for f in fs] == [f.name for f in fp]
    assert [ln for ln in out_p.splitlines() if ln.startswith("emit ")] == out_s.splitlines()
    for f in fs:
        assert (tmp_path / "p" / "rtl" / f.name).read_text() == f.read_text()
    assert rec["types"] == 7 and (tmp_path / "p" / "bind_emit_par.json").is_file()
    assert b.errors == ["WARN t1", "WARN t4"] and b.alias == b.errors      # aliased list extended once, in type order
    if big:
        assert "F" in rec["shallow_attrs"]


def test_first_failing_type_raises_with_state_up_to_it(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    a, b = Fake(), Fake()
    a.fail = b.fail = "t3"
    with pytest.raises(Err):
        serial(a, tmp_path)
    files = []
    with pytest.raises(Err, match="gap in t3"):
        EP.run(b, tmp_path, files, 3)
    assert state(a) == state(b) and [f.name for f in files] == ["t0.sv", "t1.sv", "t2.sv"]


@pytest.mark.parametrize("gate_rc", [0, 2])
def test_parallel_emit_leaves_plan_gate_status_for_its_owner(tmp_path, gate_rc):
    gate_pid = os.fork()
    if gate_pid == 0:
        os._exit(gate_rc)
    try:
        # Make the gate waitable before any worker is started, without reaping it.
        os.waitid(os.P_PID, gate_pid, os.WEXITED | os.WNOWAIT)
        EP.run(Fake(n=2), tmp_path, [], 2)
        pid, status = os.waitpid(gate_pid, 0)
        assert pid == gate_pid
        assert os.waitstatus_to_exitcode(status) == gate_rc
    finally:
        try:
            os.waitpid(gate_pid, 0)
        except ChildProcessError:
            pass


def test_cross_type_counter_is_unsafe_and_leaves_state(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    b = Fake()
    b.level = 0
    before = state(b)
    files = []
    with pytest.raises(EP.ParUnsafe, match="level"):
        EP.run(b, tmp_path, files, 3)
    assert state(b) == before and files == []


def test_merge_set_rules():
    assert EP.merge_set({"a": [1]}, {"b": [2]}, ()) == {"a": [1], "b": [2]}
    assert EP.merge_set({"a": [1]}, {"a": [1]}, ()) == {"a": [1]}
    assert EP.merge_set(True, True, ()) is True and EP.merge_set("x", "x", ()) == "x"
    assert EP.merge_set(2, 3, (("k", "stats"), ("k", "x"))) == 5
    for a, b in ((1, 1), ([1], [2]), ("x", "y"), ({"a": [1]}, {"a": [1, 1]}), (1, True)):
        with pytest.raises(EP.ParUnsafe):
            EP.merge_set(a, b, (("k", "v"),))


def test_merge_set_record_objects():
    a, b = PlanRec({"die": 1}), PlanRec({"die": 1})
    a.taps("t0"), b.taps("t1"), b.taps("t0")
    m = EP.merge_set(a, b, (("k", "_plan"),))
    assert type(m) is PlanRec and m.W == 100.0 and set(m._reset_tree_cache) == {("sites", "t0"), ("sites", "t1")}
    c = PlanRec({"die": 1})
    c._reset_tree_cache[("sites", "t0")] = [9]
    with pytest.raises(EP.ParUnsafe):
        EP.merge_set(a, c, (("k", "_plan"),))
    d = PlanRec({"die": 2})
    with pytest.raises(EP.ParUnsafe):
        EP.merge_set(a, d, (("k", "_plan"),))


def test_change_under_a_path_another_type_set_is_unsafe():
    st = {"d": {"x": [0]}}
    ops = [("t0", [("set", (("k", "d"), ("k", "x")), [9])]), ("t1", [("extend", (("k", "d"), ("k", "x")), [1])])]
    with pytest.raises(EP.ParUnsafe, match="under"):
        EP.apply(st, ops)
    assert st == {"d": {"x": [0]}}


def test_removed_key_is_unsafe(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    b = Fake()
    b.pnames["old"] = 1
    orig = b._emit_one

    def bad(tn, ps, out, files):
        b.pnames.pop("old", None)
        orig(tn, ps, out, files)
    b._emit_one = bad
    with pytest.raises(EP.ParUnsafe, match="removed"):
        EP.run(b, tmp_path, [], 2)


def test_jobs_env(monkeypatch):
    monkeypatch.delenv("OT_BIND_EMIT_J", raising=False)
    monkeypatch.setattr(EP, "mem_jobs", lambda: 3)
    assert EP.jobs() == min(3, max(1, min(8, (EP.os.cpu_count() or 4) // 4)))     # default auto, capped by memory
    monkeypatch.setenv("OT_BIND_EMIT_J", "1")
    assert EP.jobs() == 1
    monkeypatch.setenv("OT_BIND_EMIT_J", "6")
    assert EP.jobs() == 6
    monkeypatch.setenv("OT_BIND_EMIT_J", "auto")
    assert 1 <= EP.jobs() <= 8
    monkeypatch.setenv("OT_BIND_EMIT_J", "x")
    assert EP.jobs() == 1


def test_mem_jobs():
    G = 1 << 30
    assert EP.mem_jobs(rss=8 * G, limit=110 * G) == 15                 # KV: 8 GB parent, ot-run --mem 110
    assert EP.mem_jobs(rss=8 * G, limit=24 * G) == 2
    assert EP.mem_jobs(rss=8 * G, limit=9 * G) == 1
    assert EP.mem_jobs(rss=0, limit=None) == 8
    assert EP._mem_limit_bytes() is None or EP._mem_limit_bytes() > 0
