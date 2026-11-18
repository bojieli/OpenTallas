"""PUBLISH-GATE-1116: a tree switch is applied only with a matching PASS record of the pre-apply gate.
Runs the tree's real schema / plan_gate_pre / check.py (tools/die_plan) on tools/die_plan/examples/tiny_plan.json."""
import copy, hashlib, json, os, tempfile, unittest
from pathlib import Path
import apply_reviewed_tree_marker as A
import publish_gate as PG

REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "tools/die_plan/examples/tiny_plan.json"
MANIFEST = "ab" * 32


class TC:
    @staticmethod
    def identity(die, tree, want, hosts, checker): return dict(die=die, tree=tree)
    @staticmethod
    def read(d, ident): return dict(state="ok", full_ok=True, running=False, main_sha="a" * 40)
    @staticmethod
    def location(d, ident): return Path(d) / "x"


def sha(b): return hashlib.sha256(b).hexdigest()


def mk_view(tree, name="v1", fg=b"face guard source v1\n"):
    v = Path(tree) / "physical/ref_tile/x/views" / name
    le = v / "landing_evidence"
    le.mkdir(parents=True)
    (le / "face_guard_source.py").write_bytes(fg)
    (le / "netlist.v").write_bytes(b"module m; endmodule\n")
    (le / "manifest.json").write_text(json.dumps({"sha256": {"face_guard_source.py": sha(fg), "netlist.v": sha(b"module m; endmodule\n")}}))
    (v / "provenance.json").write_text(json.dumps({"kit": {"face_guard_sha256": sha(fg)}}))
    return v


def mk_tree(td, plan_obj=None, with_view=True):
    tree = Path(td) / "tree"
    tree.mkdir()
    os.symlink(REPO / "tools", tree / "tools")
    plan = tree / "plan.json"
    plan.write_text(json.dumps(plan_obj if plan_obj is not None else json.loads(PLAN.read_text())))
    if with_view:
        mk_view(tree)
    return tree, plan


def mk_coord(td):
    c = Path(td) / "coord"
    (c / "autopilot").mkdir(parents=True)
    (c / "lanes/handoff").mkdir(parents=True)
    d = {"src": "/x/old", "event": "E0", "plan": "/p0", "plan_sha256": "s0", "pilot_item": "t1", "work_root": "/tmp/pgwork"}
    (c / "autopilot/kit_wave.json").write_text(json.dumps({"dies": {"kv": d}}))
    return c


def cand(tree, plan):
    return {"die": "kv", "tree": str(tree), "manifest_hash": MANIFEST, "smoke": "PASS", "plan": str(plan),
            "plan_sha256": sha(Path(plan).read_bytes()), "hosts": ["epyc10"]}


def local_static(host, tree, plan, asbuilt, plan_sha):
    return PG.run_static(tree, plan, asbuilt, plan_sha, tempfile.mkdtemp(prefix="pgt-"))


def hash_static(host, tree, plan, asbuilt, plan_sha):
    """schema / PRE / G0 are exercised by the two real-tool tests (PRE alone takes ~20 s); the rest run the real hash check only"""
    f, n = PG.check_hashes(tree, plan, plan_sha)
    cf = PG.check_contained(tree, plan)
    ok = {"verdict": "PASS"}
    return {"schema": ok, "pre_g0": ok, "hashes": {"verdict": "PASS" if not f and n else "FAIL", "views": n, "findings": f},
            "contained": {"verdict": "PASS" if not cf else "FAIL", "findings": cf}}


def dry_pass(text, die, item, kind, host, want):
    cfg = json.loads(text)["dies"][die]
    assert cfg["src"] != "/x/old" and item == "t1"             # the dry gen sees the PROJECTED die config and the pilot item
    return {"verdict": "PASS", "item": item}


def dry_must_not_run(*a):
    raise AssertionError("dry gen stub: raises (LATENCY-R 11-18: it runs alongside the static checks, a raise is a recorded FAIL)")


class Gate(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp(prefix="pgtest-")
        self.c = mk_coord(self.td)

    def gate(self, tree, plan, dry=dry_pass, static=hash_static):
        return PG.run_gate(self.c, cand(tree, plan), "/x/old", "E0", static_fn=static, dry_fn=dry, TC=TC)

    def apply(self, tree, plan):
        return A.apply_marker(self.c, cand(tree, plan), "/x/old", "E0", pilot_item="t1", TC=TC)

    def test_good_tree_passes_and_applies(self):
        tree, plan = mk_tree(self.td)
        rec = self.gate(tree, plan, static=local_static)
        self.assertEqual(rec["verdict"], "PASS", json.dumps(rec["checks"])[:900])
        self.assertTrue(all(rec["checks"][c]["verdict"] == "PASS" for c in PG.CHECKS))
        self.assertEqual(rec["checks"]["hashes"]["views"], 1)
        self.assertEqual(PG.require_pass(self.c, "kv", str(tree), MANIFEST, cand(tree, plan)["plan_sha256"]), "")
        r = self.apply(tree, plan)
        self.assertEqual(r["applied"], "kv")
        d = json.loads((self.c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["src"], str(tree))

    def test_bad_schema_field_refuses(self):
        p = json.loads(PLAN.read_text())
        p["clock"]["die_tree"] = {"id": "advisory", "taps": 11571}       # the D8 class: an unknown advisory field
        tree, plan = mk_tree(self.td, p)
        rec = self.gate(tree, plan, dry=dry_must_not_run, static=local_static)
        self.assertEqual(rec["verdict"], "FAIL")
        self.assertEqual(rec["checks"]["schema"]["verdict"], "FAIL")
        self.assertIn("die_tree", rec["checks"]["schema"]["tail"])
        self.assertEqual(rec["checks"]["pre_g0"]["verdict"], "FAIL")
        self.assertEqual(rec["checks"]["dry_gen"]["verdict"], "FAIL")           # LATENCY-R 11-18: runs alongside the static checks (here it raises: recorded FAIL)
        with self.assertRaises(AssertionError) as cm:
            self.apply(tree, plan)
        self.assertIn("publish gate", str(cm.exception))
        self.assertEqual(json.loads((self.c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]["src"], "/x/old")

    def test_wrong_view_hash_refuses(self):
        tree, plan = mk_tree(self.td)
        v = mk_view(tree, "v2")
        os.chmod(v / "landing_evidence/face_guard_source.py", 0o644)
        (v / "landing_evidence/face_guard_source.py").write_bytes(b"a different frozen view file\n")   # the D5 class
        rec = self.gate(tree, plan, dry=dry_must_not_run)
        self.assertEqual(rec["verdict"], "FAIL")
        h = rec["checks"]["hashes"]
        self.assertEqual(h["verdict"], "FAIL")
        self.assertTrue(any("v2" in f and "face_guard_source.py" in f for f in h["findings"]), h["findings"])
        self.assertFalse(any("v1" in f for f in h["findings"]))
        with self.assertRaises(AssertionError):
            self.apply(tree, plan)

    def test_provenance_face_guard_mismatch_alone_refuses(self):
        tree, plan = mk_tree(self.td, with_view=False)
        v = mk_view(tree)
        (v / "provenance.json").write_text(json.dumps({"kit": {"face_guard_sha256": sha(b"other")}}))
        rec = self.gate(tree, plan, dry=dry_must_not_run)
        self.assertTrue(any("provenance kit.face_guard_sha256" in f for f in rec["checks"]["hashes"]["findings"]))

    def test_plan_outside_the_tree_refuses(self):         # S81 D4: plan + census sidecar in a lane dir on one host
        tree, plan = mk_tree(self.td)
        lane = Path(self.td) / "lane/die_plan/s81"
        (lane / "census").mkdir(parents=True)
        (lane / "census/s81_lanes.tsv").write_text("x\n")
        outside = lane / "plan.json"
        outside.write_text(plan.read_text())
        rec = self.gate(tree, outside, dry=dry_must_not_run)
        self.assertEqual(rec["verdict"], "FAIL")
        c = rec["checks"]["contained"]
        self.assertEqual(c["verdict"], "FAIL")
        self.assertTrue(any("outside the tree" in f for f in c["findings"]), c)
        with self.assertRaises(AssertionError):
            self.apply(tree, outside)

    def test_plan_naming_a_file_outside_the_tree_refuses(self):
        side = Path(self.td) / "elsewhere.json"
        side.write_text("{}")
        p = json.loads(PLAN.read_text())
        p["extra_input"] = str(side)
        tree, plan = self._tp(p)
        self.assertEqual(PG.check_contained(tree, plan), [] if not str(side).startswith("/srv/") else PG.check_contained(tree, plan))
        f = PG.check_contained(tree, plan, roots=(self.td,))
        self.assertTrue(any("elsewhere.json" in x for x in f), f)
        (Path(tree) / "inside.json").write_text("{}")             # a sidecar inside the tree is fine
        p["extra_input"] = str(Path(tree) / "inside.json")
        Path(plan).write_text(json.dumps(p))
        self.assertEqual(PG.check_contained(tree, plan, roots=(self.td,)), [])

    def _tp(self, p):
        tree, plan = mk_tree(tempfile.mkdtemp(dir=self.td), p)
        return tree, plan

    def test_dry_gen_failure_refuses(self):
        tree, plan = mk_tree(self.td)
        rec = self.gate(tree, plan, dry=lambda *a: {"verdict": "FAIL", "why": "stage gen: face_guard hash != provenance"})
        self.assertEqual(rec["verdict"], "FAIL")
        with self.assertRaises(AssertionError):
            self.apply(tree, plan)

    def test_no_record_refuses(self):
        tree, plan = mk_tree(self.td)
        with self.assertRaises(AssertionError) as cm:
            self.apply(tree, plan)
        self.assertIn("no PASS record", str(cm.exception))

    def test_record_is_keyed_to_the_manifest_and_plan(self):
        tree, plan = mk_tree(self.td)
        self.assertEqual(self.gate(tree, plan)["verdict"], "PASS")
        ps = cand(tree, plan)["plan_sha256"]
        self.assertIn("no PASS record", PG.require_pass(self.c, "kv", str(tree), "cd" * 32, ps))       # another manifest sha
        self.assertIn("plan_sha256", PG.require_pass(self.c, "kv", str(tree), MANIFEST, "0" * 64))
        self.assertIn("tree", PG.require_pass(self.c, "kv", "/other/tree", MANIFEST, ps))
        rp = PG.record_path(self.c, "kv", MANIFEST)
        r = json.loads(rp.read_text()); r["checks"]["dry_gen"]["verdict"] = "FAIL"; rp.write_text(json.dumps(r))
        self.assertIn("checks not PASS: dry_gen", PG.require_pass(self.c, "kv", str(tree), MANIFEST, ps))

    def test_gate_that_cannot_run_is_a_fail(self):
        tree, plan = mk_tree(self.td)
        def boom(*a): raise OSError("ssh dropped")
        rec = PG.run_gate(self.c, cand(tree, plan), "/x/old", "E0", static_fn=boom, dry_fn=dry_pass, TC=TC)
        self.assertEqual(rec["verdict"], "FAIL")
        self.assertIn("ssh dropped", rec["checks"]["gate"]["why"])

    def test_the_projection_never_touches_the_live_config(self):
        tree, plan = mk_tree(self.td)
        before = (self.c / "autopilot/kit_wave.json").read_text()
        self.gate(tree, plan)
        self.assertEqual((self.c / "autopilot/kit_wave.json").read_text(), before)
        self.assertFalse(list((self.c / "lanes/handoff").iterdir()))


class Concurrent(unittest.TestCase):
    def test_static_and_dry_gen_run_at_the_same_time(self):
        import threading
        td = tempfile.mkdtemp(prefix="pgconc-"); c = mk_coord(td); tree, plan = mk_tree(td)
        both = threading.Barrier(2, timeout=20)

        def static(*a):
            both.wait(); return {k: {"verdict": "PASS"} for k in ("schema", "pre_g0", "hashes", "contained")}

        def dry(*a):
            both.wait(); return {"verdict": "PASS"}
        rec = PG.run_gate(c, cand(tree, plan), "/x/old", "E0", static_fn=static, dry_fn=dry, TC=TC)   # serial calls would break the barrier
        self.assertEqual(rec["verdict"], "PASS"); self.assertEqual(rec["advisory"], [])
        self.assertIn("gate_s", rec)


if __name__ == "__main__":
    unittest.main()


def test_static_step_budget_covers_a_long_g0():
    """QC M5 11-17: check.py G0 on the QC plan runs ~48 min; the static step budget must not fail it on time."""
    import inspect
    import publish_gate as PG
    assert PG.STEP_TIMEOUT_S >= 3 * 3600
    assert inspect.signature(PG._sub).parameters["timeout"].default == PG.STEP_TIMEOUT_S
    seen = {}

    class R:
        stdout, stderr, returncode = "PG_STATIC {}", "", 0

    def runner(argv, **kw):
        seen.update(kw)
        return R()
    PG.static_remote("hostx", "/tmp/w", "/t", "/t/p.json", None, "0" * 64, runner=runner)
    assert seen["timeout"] >= 3 * PG.STEP_TIMEOUT_S


class RowsProof(unittest.TestCase):
    """QC N2B 11-17: candidate.rows_proofs reaches plan_gate_pre as --rows-proof (ROWS-NO-PROOF otherwise) and must lie in the tree"""
    def setUp(self):
        self.td = tempfile.mkdtemp(prefix="pgrp-")
        self.tree = Path(self.td) / "tree"; self.tree.mkdir()
        self.plan = self.tree / "plan.json"; self.plan.write_text("{}")
        (self.tree / "por").mkdir(); (self.tree / "por/rows_proof.json").write_text("{}")

    def static(self, proofs):
        seen = []
        orig = PG._sub
        PG._sub = lambda argv, cwd, timeout=None: (seen.append(argv), (0, ""))[1]
        try:
            res = PG.run_static(self.tree, self.plan, None, "0" * 64, tempfile.mkdtemp(prefix="pgrpw-"), rows_proofs=proofs)
        finally:
            PG._sub = orig
        pre = [a for a in seen if any(str(x).endswith("plan_gate_pre.py") for x in a)][0]
        return res, pre

    def test_rows_proof_is_forwarded_to_pre_and_contained(self):
        res, pre = self.static(["por/rows_proof.json"])
        i = pre.index("--rows-proof")
        self.assertEqual(pre[i + 1], str(self.tree / "por/rows_proof.json"))
        self.assertEqual(res["contained"]["verdict"], "PASS", res["contained"])

    def test_no_rows_proof_keeps_the_old_pre_call(self):
        _res, pre = self.static(None)
        self.assertNotIn("--rows-proof", pre)

    def test_rows_proof_outside_the_tree_or_missing_fails_contained(self):
        out = Path(self.td) / "lane_proof.json"; out.write_text("{}")
        res, _pre = self.static([str(out), "por/nope.json"])
        self.assertEqual(res["contained"]["verdict"], "FAIL")
        f = " ".join(res["contained"]["findings"])
        self.assertIn("outside the tree", f); self.assertIn("missing", f)

    def test_static_remote_ships_every_proof(self):
        got = {}

        class R:
            stdout, stderr, returncode = "PG_STATIC {}", "", 0

        def runner(argv, **kw):
            got["cmd"] = argv[-1]
            return R()
        PG.static_remote("hostx", "/tmp/w", "/t", "/t/p.json", None, "0" * 64, runner=runner, rows_proofs=["/t/a.json", "/t/b.json"])
        self.assertIn("--rows-proof /t/a.json", got["cmd"]); self.assertIn("--rows-proof /t/b.json", got["cmd"])

    def test_run_gate_takes_rows_proofs_from_the_candidate(self):
        c = mk_coord(self.td)
        tree, plan = mk_tree(tempfile.mkdtemp(prefix="pgrpt-"))
        seen = {}
        orig = PG.static_remote

        def fake(host, work_dir, t, p, ab, ps, **kw):
            seen.update(kw)
            return {k: {"verdict": "FAIL", "why": "stub"} for k in ("schema", "pre_g0", "hashes", "contained")}
        PG.static_remote = fake
        try:
            obj = dict(cand(tree, plan), rows_proofs=["plan_of_record/zz.rows_proof.json"])
            rec = PG.run_gate(c, obj, "/x/old", "E0", dry_fn=dry_must_not_run, TC=TC)
        finally:
            PG.static_remote = orig
        self.assertEqual(seen.get("rows_proofs"), ["plan_of_record/zz.rows_proof.json"])
        self.assertEqual(rec["rows_proofs"], ["plan_of_record/zz.rows_proof.json"])
