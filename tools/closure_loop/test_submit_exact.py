"""submit_exact: spec follows the commit; kit/consumed paths come from the route command (ROOT 2026-10-15)."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import submit_exact as S  # noqa: E402

SPEC = {"name": "s81net_x-n4-7f5182219", "block": "x", "ref_tile": True,
        "source": {"commit": "7f5182219", "extra_paths": ["rtl/a"]}, "sources": ["rtl/b.sv"],
        "stages": {"route": {"cmd": "bash tools/ref_tile/ref_route.sh physical/ref_tile/x/kit.env"}}}


def test_move_spec_renames_suffix():
    s = S.move_spec(SPEC, "abcdef0123456789")
    assert s["name"] == "s81net_x-n4-abcdef012" and s["source"]["commit"] == "abcdef012"
    assert SPEC["source"]["commit"] == "7f5182219"


def test_consumed_paths():
    assert S.kit_of(SPEC) == "physical/ref_tile/x"
    assert S.consumed_paths(SPEC) == ["physical/ref_tile/x", "rtl/b.sv", "rtl/a"]


def test_dirty_detects_uncommitted_and_moved(tmp_path):
    def g(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)
    g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    (tmp_path / "k").mkdir(); (tmp_path / "k" / "f").write_text("1")
    g("add", "k"); g("commit", "-qm", "a")
    c1 = S.git(tmp_path, "rev-parse", "HEAD")
    assert S.dirty(tmp_path, c1, ["k"]) == ([], [])
    (tmp_path / "k" / "f").write_text("2")
    assert S.dirty(tmp_path, c1, ["k"])[0] == ["k/f"]
    g("commit", "-qam", "b")
    assert S.dirty(tmp_path, c1, ["k"]) == ([], ["k/f"])


def test_origin_problems_unpushed_source_and_grant(tmp_path):
    def g(d, *a):
        return subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, text=True).stdout.strip()
    bare, wt = tmp_path / "o.git", tmp_path / "w"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(["git", "init", "-q", str(wt)], check=True)
    g(wt, "config", "user.email", "t@t"); g(wt, "config", "user.name", "t"); g(wt, "remote", "add", "origin", str(bare))
    (wt / "k").mkdir(); (wt / "k" / "spec.json").write_text("{}")
    g(wt, "add", "k"); g(wt, "commit", "-qm", "a"); g(wt, "push", "-q", "origin", "HEAD:refs/heads/br")
    c1 = g(wt, "rev-parse", "HEAD")
    spec = {"source": {"branch": "br"}}
    assert S.origin_problems(wt, c1, spec, "k") == []
    (wt / "k" / "grant.json").write_text('{"m6_pin_grant": {"source_commit": "%s"}}' % c1)
    g(wt, "add", "k"); g(wt, "commit", "-qm", "b")
    c2 = g(wt, "rev-parse", "HEAD")
    bad = S.origin_problems(wt, c2, spec, "k", push=False)
    assert len(bad) == 1 and "not on origin/br" in bad[0]
    assert S.origin_problems(wt, c2, spec, "k", dry=True) == []       # fast-forward possible: dry run would push
    assert S.origin_problems(wt, c2, spec, "k") == []                 # GATE-FRICTION: fast-forward pushed
    assert g(wt, "rev-parse", "origin/br") == c2
    g(wt, "checkout", "-q", "--detach", c1); g(wt, "commit", "-q", "--allow-empty", "-m", "diverged")
    bad = S.origin_problems(wt, g(wt, "rev-parse", "HEAD"), spec, "k")
    assert len(bad) == 1 and "no fast-forward" in bad[0]              # never forced
    g(wt, "checkout", "-q", c2)
    g(wt, "commit", "-q", "--allow-empty", "-m", "local only")
    c3 = g(wt, "rev-parse", "HEAD")
    (wt / "k" / "grant.json").write_text('{"m6_pin_grant": {"source_commit": "%s"}}' % c3)
    g(wt, "add", "k"); g(wt, "commit", "-qm", "c"); g(wt, "push", "-q", "origin", "HEAD:refs/heads/br")
    c4 = g(wt, "rev-parse", "HEAD")
    assert S.origin_problems(wt, c4, spec, "k") == []           # c3 is pushed as an ancestor of br
    (wt / "k" / "grant.json").write_text('{"m6_pin_grant": {"source_commit": "%s"}}' % ("ab" * 20))
    g(wt, "add", "k"); g(wt, "commit", "-qm", "d"); g(wt, "push", "-q", "origin", "HEAD:refs/heads/br")
    bad = S.origin_problems(wt, g(wt, "rev-parse", "HEAD"), spec, "k")
    assert len(bad) == 1 and "does not exist" in bad[0]


import json as _json_vr
import unittest
SE = S
json = _json_vr


class VisualReview(unittest.TestCase):
    """PRE-ROUTE VISUAL REVIEW (owner 2026-10-17)"""
    def setUp(self):
        import tempfile
        self.t = Path(tempfile.mkdtemp())
        self.crit = self.t / "critical.txt"; self.crit.write_text("ot_hot  # coordinator\n")
        self.jobs = self.t / "jobs"; self.jobs.mkdir()
        SE.CRITICAL_TILES = self.crit
        self.lock = self.t / "COORDINATOR.lock"; self.lock.write_text('{"owner": "claude"}')
        SE.COORD_LOCK = self.lock

    def test_required_by_list_or_failed_routes(self):
        self.assertIn("critical", SE.review_required({"block": "ot_hot"}, "physical/ref_tile/k", self.jobs))
        self.assertIsNone(SE.review_required({"block": "ot_cold"}, "physical/ref_tile/k", self.jobs))
        self.assertIn("matches 'ot_hot'", SE.review_required({"block": "ot_hot_v2"}, "physical/ref_tile/k", self.jobs))
        self.assertIn("coordinator", "coordinator (msg 2026-10-17 07:05)")
        self.assertIsNone(SE.reviewer_allowed("coordinator (msg 2026-10-17 07:05)"))
        for i, st in enumerate(("EARLY_FAIL_HOLD", "NEEDS_RTL", "CLOSED")):
            (self.jobs / f"j{i}.json").write_text(json.dumps({"name": f"j{i}", "status": st, "spec": {"block": "ot_cold"}}))
        self.assertIn("2 earlier", SE.review_required({"block": "ot_cold"}, "physical/ref_tile/k", self.jobs))

    def test_receipt_binding(self):
        gate = {"commit": "abc1234def", "generated": "t"}
        good = {"reviewer": "coordinator (Claude)", "time": "now", "gate_commit": "abc1234", "verdict": "APPROVED",
                "checklist": {k: "ok" for k in SE.REVIEW_CHECKLIST}}
        files = {"k/gate_result.json": json.dumps(gate), "k/gate_layout/REVIEW.json": json.dumps(good)}
        self.assertIsNone(SE.review_check(self.t, "c" * 40, "k", show=files.get))
        for bad in (dict(good, gate_commit="fff9999"), dict(good, verdict="CHANGES"),
                    dict(good, checklist={"lattice": 1})):
            files["k/gate_layout/REVIEW.json"] = json.dumps(bad)
            self.assertIn("REVIEW_REQUIRED", SE.review_check(self.t, "c" * 40, "k", show=files.get))
        del files["k/gate_layout/REVIEW.json"]
        self.assertIn("REVIEW_REQUIRED: no", SE.review_check(self.t, "c" * 40, "k", show=files.get))

    def test_geometry_hash_independent_of_kit_name(self):
        """ROOT 10-19 (HKV-D2D18): a byte-identical layout under a new kit name hashes the same; a receipt carrying the
        pre-10-19 path-keyed hash is still accepted; a changed pin file still changes the hash"""
        fp = {"die": [0, 0, 100, 50], "core": [1, 1, 99, 49], "pins": {"W": ["a"]}, "clock_port": "ck", "blocks": []}
        def kit(name, io="set_io_pin_constraint -region left:* -pin_names a\n"):
            return {f"{name}/floorplan.json": json.dumps(fp), f"{name}/io.tcl": io,
                    f"{name}/clock_entry.sdc": "create_clock ck\n",
                    f"{name}/spec.json": json.dumps({"outline": {"w": 100, "h": 50}, "io_tcl": f"{name}/io.tcl"}),
                    f"{name}/gate_result.json": json.dumps({"commit": "new1234"})}
        a, b = kit("physical/ref_tile/d2d_r7u"), kit("physical/ref_tile/d2d_r7v")
        ga, gb = SE.geometry_record(a.get, "physical/ref_tile/d2d_r7u"), SE.geometry_record(b.get, "physical/ref_tile/d2d_r7v")
        self.assertEqual(ga["sha256"], gb["sha256"])
        la = SE.geometry_record(a.get, "physical/ref_tile/d2d_r7u", legacy=True)
        lb = SE.geometry_record(b.get, "physical/ref_tile/d2d_r7v", legacy=True)
        self.assertNotEqual(la["sha256"], lb["sha256"])          # the old form keyed by path (the pointless re-review)
        c = kit("physical/ref_tile/d2d_r7v", io="set_io_pin_constraint -region right:* -pin_names a\n")
        self.assertNotEqual(SE.geometry_record(c.get, "physical/ref_tile/d2d_r7v")["sha256"], ga["sha256"])
        rev = {"reviewer": "coordinator (Claude)", "time": "now", "gate_commit": "abc0001", "verdict": "APPROVED",
               "checklist": {k: "ok" for k in SE.REVIEW_CHECKLIST}}
        for sha in (gb["sha256"], lb["sha256"]):                 # new form, and the transition (legacy) form
            b["physical/ref_tile/d2d_r7v/gate_layout/REVIEW.json"] = json.dumps(dict(rev, geometry_sha256=sha))
            self.assertIsNone(SE.review_check(self.t, "c" * 40, "physical/ref_tile/d2d_r7v", show=b.get))
        c["physical/ref_tile/d2d_r7v/gate_layout/REVIEW.json"] = json.dumps(dict(rev, geometry_sha256=lb["sha256"]))
        self.assertIn("geometry changed", SE.review_check(self.t, "c" * 40, "physical/ref_tile/d2d_r7v", show=c.get))

    def test_geometry_bound_receipt(self):
        fp = {"die": [0, 0, 100, 50], "core": [1, 1, 99, 49], "pins": {"W": ["a"], "E": ["b"]}, "clock_port": "ck",
              "blocks": [{"inst": "u", "master": "m", "x": 43.2, "y": 0, "w": 10, "h": 10, "orient": "R0"}]}
        files = {"k/gate_result.json": json.dumps({"commit": "new1234", "generated": "t2"}),
                 "k/floorplan.json": json.dumps(fp), "k/spec.json": json.dumps({"outline": {"w": 100, "h": 50}})}
        geo = SE.geometry_record(files.get, "k")
        good = {"reviewer": "coordinator (Claude)", "time": "now", "gate_commit": "abc0001", "verdict": "APPROVED",
                "checklist": {k: "ok" for k in SE.REVIEW_CHECKLIST}, "geometry_sha256": geo["sha256"], "geometry": geo}
        files["k/gate_layout/REVIEW.json"] = json.dumps(good)
        self.assertIsNone(SE.review_check(self.t, "c" * 40, "k", show=files.get))     # re-gated, same geometry
        moved = dict(fp, blocks=[dict(fp["blocks"][0], x=86.4)])
        files["k/floorplan.json"] = json.dumps(moved)
        r = SE.review_check(self.t, "c" * 40, "k", show=files.get)
        self.assertIn("geometry changed", r)
        self.assertIn("changed: macros", r)
        # legacy receipt (no geometry hash): the geometry at its gate_commit decides
        legacy = {k: v for k, v in good.items() if not k.startswith("geometry")}
        files["k/gate_layout/REVIEW.json"] = json.dumps(legacy)
        old = {"k/floorplan.json": json.dumps(fp), "k/spec.json": files["k/spec.json"]}
        self.assertIn("geometry changed since the review",
                      SE.review_check(self.t, "c" * 40, "k", show=files.get, show_at=lambda c, p: old.get(p)))
        files["k/floorplan.json"] = json.dumps(fp)
        self.assertIsNone(SE.review_check(self.t, "c" * 40, "k", show=files.get, show_at=lambda c, p: old.get(p)))
        self.assertIn("REVIEW_REQUIRED", SE.review_check(self.t, "c" * 40, "k", show=files.get,
                                                         show_at=lambda c, p: None))


    def test_reviewer_must_be_lock_holder(self):
        self.assertIsNone(SE.reviewer_allowed("coordinator (Claude 10-17)"))
        for bad in ("ROOT (Claude)", "Q-KV lead", "codex"):
            self.assertIsNotNone(SE.reviewer_allowed(bad), bad)
        self.lock.write_text('{"owner": "codex"}')
        self.assertIsNone(SE.reviewer_allowed("Codex coordinator"))
        self.assertIsNotNone(SE.reviewer_allowed("coordinator (Claude)"))


def test_bench_evidence_refusals():
    P = {"name": "pos", "cmd": "x", "expect": "pass"}
    F = {"name": "mut", "cmd": "y", "expect": "fail", "fail_regex": "MISMATCH", "fail_witness": "results/w.log"}
    st = lambda *b: dict(SPEC, stages={"bench": list(b)})  # noqa: E731
    assert S.bench_evidence_problems(st(P, F)) == ([], [])
    e, _ = S.bench_evidence_problems(dict(SPEC))
    assert e and "no benches" in e[0]
    e, _ = S.bench_evidence_problems(st(P))
    assert any("expect=fail mutant" in x for x in e)
    e, _ = S.bench_evidence_problems(st({"name": "lint", "cmd": "z", "expect": "pass"}, F))
    assert any("behavioural" in x for x in e)
    # GATE-FRICTION: a missing committed witness only WARNs (the loop captures it); a missing fail_regex still refuses
    nowit = dict(F, fail_witness=None)
    e, w = S.bench_evidence_problems(st(P, nowit))
    assert not e and w and "captures the real mutant log" in w[0]
    norx = dict(F, fail_regex=None, fail_witness=None)
    e, _ = S.bench_evidence_problems(st(P, norx))
    assert e and "fail_regex" in e[0]
    e, w = S.bench_evidence_problems(dict(st(P, norx), fail_witness_waiver="mutant log captured after the route"))
    assert not e and w and "[waived]" in w[0]
    e, w = S.bench_evidence_problems(st(P, norx), allow_missing_witness=True)
    assert not e and w
    assert S.bench_evidence_problems(dict(SPEC, hold_merge="never merges"))[0] == []


def test_housekeeping_generated_files(tmp_path):
    assert S.generated_only(["physical/ref_tile/k/gate_result.json", "physical/ref_tile/k/source_binding_history/a.json",
                             "physical/ref_tile/k/gate_layout/floorplan.png"])
    assert not S.generated_only(["physical/ref_tile/k/spec.json", "physical/ref_tile/k/gate_result.json"])
    assert not S.generated_only([])
    (tmp_path / "gate_result.json").write_text('{"verdict": "FAIL"}')
    assert not S.gate_file_ok(tmp_path, "gate_result.json")          # a FAIL gate is never auto-committed
    (tmp_path / "gate_result.json").write_text('{"verdict": "WARN"}')
    assert S.gate_file_ok(tmp_path, "gate_result.json")


def test_main_tools_reexec_skips_when_flagged(monkeypatch):
    monkeypatch.setenv("OT_SUBMIT_EXACT_MAIN", "x")
    assert S.main_tools_reexec(["spec.json"]) is None
    monkeypatch.delenv("OT_SUBMIT_EXACT_MAIN")
    assert S.main_tools_reexec(["spec.json", "--local-tools"]) is None
