"""REF-SITE-SPEED-1125: ref_site.run pools its per-type work with lines identical to the serial run; plan_advisory runs the
self-pooling checks (PARENT_CHECKS) in the parent, keeping CHECKS order."""
import os

import plan_advisory as PA
import ref_site as RS


def _fake(monkeypatch):
    raw = {"partition_types": {f"T{i}": {} for i in range(7)}}
    monkeypatch.setattr(RS.TS, "_plan", lambda r, p: object())
    monkeypatch.setattr(RS.TS, "_plandir", lambda p: None)
    monkeypatch.setattr(RS.TS, "type_tables", lambda r, tn: [1])

    def type_refs(P, r, tn):
        i = int(tn[1:])
        if i == 3:
            raise ValueError("no grid")
        refs = {f"collector_children[{j}]": ("reset", f"rst_n_t{j}", (0.0, 0.0), [(500.0 * (j + 1) * (i % 2), 0.0)]) for j in range(i)}
        refs["x[u]"] = ("unemitted", "rst_rl_9", None, []) if i == 5 else ("tap", "clk_t1", (1.0, 1.0), [])
        return refs, i
    monkeypatch.setattr(RS, "type_refs", type_refs)
    monkeypatch.setattr(RS, "family", lambda k: "collector_children" if k.startswith("collector") else "x")
    monkeypatch.setattr(RS, "LOCAL_FAMILIES", {"collector_children"})
    return raw


def test_pooled_run_lines_equal_serial(monkeypatch):
    raw = _fake(monkeypatch)
    a, b = [], []
    ra = RS.run(raw, "p.json", log=a.append, jobs=1)
    rb = RS.run(raw, "p.json", log=b.append, jobs=3)
    assert a == b and len(a) >= 4
    assert ra["reach"] == rb["reach"] and ra["unemitted"] == rb["unemitted"] and ra["tot"] == rb["tot"]
    assert any(x.startswith("NOT-EVALUABLE\tT3") for x in a)


def test_ref_site_jobs_env_and_daemon(monkeypatch):
    monkeypatch.setenv("OT_REF_SITE_J", "1")
    assert RS._jobs(10) == 1
    monkeypatch.setenv("OT_REF_SITE_J", "4")
    assert RS._jobs(10) == 4 and RS._jobs(2) == 2


def test_parent_checks_run_in_parent_in_checks_order(monkeypatch):
    pids = {}

    def fake_one(name, mod, raw, plan_path, tree, kw, cap, alarm=True):
        pids[name] = (os.getpid(), alarm)
        return name, [f"WARN ADV-{name} x"], 0.0
    monkeypatch.setattr(PA, "_run_one", fake_one)
    names = [n for n, _ in PA.CHECKS[:4]] + ["REF-SITE"]
    out = PA.run({}, "p.json", checks=names, jobs=3)
    order = [n for n, _ in PA.CHECKS if n in names]
    assert out == [f"WARN ADV-{n} x" for n in order]
    assert pids["REF-SITE"] == (os.getpid(), False)          # parent, no alarm (pool children record in their own dict)
