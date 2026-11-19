import json, os, tempfile, unittest
from pathlib import Path
import apply_reviewed_tree_marker as A
import hold_records as HR


class PGOK:                                   # PUBLISH-GATE-1116: these tests are about the apply, the gate has its own tests
    @staticmethod
    def require_pass(*a): return ""


def apply(*a, **k):
    k.setdefault("PG", PGOK)
    return A.apply_marker(*a, **k)

SHA = "13f758a4fe342e4838cebd2401f11f37570e92e46e226642e518ad78245f776d"


class TC:
    @staticmethod
    def identity(die, tree, want, hosts, checker): return dict(die=die, tree=tree)
    @staticmethod
    def read(d, ident): return dict(state="ok", full_ok=True, running=False, main_sha="a" * 40)
    @staticmethod
    def location(d, ident): return Path(d) / "x"


def mk(die_extra=None):
    c = Path(tempfile.mkdtemp()); (c / "autopilot").mkdir(); (c / "lanes/handoff").mkdir(parents=True)
    d = {"src": "/x/old", "event": "E0", "plan": "/p0", "plan_sha256": "s0", "hold_event_items": {"s0": ["t3", "t1"]}}
    d.update(die_extra or {})
    (c / "autopilot/kit_wave.json").write_text(json.dumps({"dies": {"kv": d}}))
    return c


def cand():
    return {"die": "kv", "tree": "/x/new", "manifest_hash": SHA, "smoke": "PASS", "plan": "/p1", "plan_sha256": "s1", "hosts": ["epyc10"]}


class Apply(unittest.TestCase):
    def test_atomic_apply_adds_the_pilot_hold_and_queues_the_old_tree(self):
        c = mk()
        r = apply(c, cand(), "/x/old", "E0", pilot_item="t1", TC=TC)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["src"], "/x/new"); self.assertEqual(d["rollback_tree"], "/x/old")
        rec = [x for x in d["hold_records"] if x.get("auto_pilot")][0]
        self.assertEqual(rec["release"], ["gen_pilot:kv:13f758a4fe34"]); self.assertEqual(rec["pilot_items"], ["t1"])
        self.assertEqual(r["pilot"]["item"], "t1"); self.assertTrue(r["pilot"]["hold_added"])
        self.assertTrue((c / "lanes/handoff/tree_switch_kv.json").exists())

    def test_superseded_auto_pilot_is_preserved_in_apply_receipt(self):
        old = {"id": "pilot-kv-deadbeefdead", "plan_sha": "s0", "items": ["*"],
               "pilot_items": ["t3"], "release": ["gen_pilot:kv:deadbeefdead"],
               "reason": "old source", "auto_pilot": True, "follow_plan": True}
        physical = {"id": "physical", "plan_sha": "s0", "items": ["t3"],
                    "release": ["proof:cts"], "reason": "physical proof", "carry": True}
        c = mk({"hold_records": [old, physical]})
        result = apply(c, cand(), "/x/old", "E0", pilot_item="t1", TC=TC)
        after = json.loads((c / "autopilot/kit_wave.json").read_text())
        records = after["dies"]["kv"]["hold_records"]
        self.assertIn(physical, records)
        self.assertNotIn(old, records)
        receipt = json.loads(Path(result["receipt"]).read_text())
        self.assertEqual(receipt["pilot"]["retired"], [old])
        self.assertNotIn("retired_pilots", after)
        self.assertNotIn("retired_pilots", after["dies"]["kv"])

    def test_apply_records_the_replaced_event_in_the_event_lineage(self):
        """r631: event_adopt terms of any ancestor stay met, so each apply that changes the event appends the one it replaces"""
        c = mk()
        c1 = dict(cand(), config={"event": "E1"})
        apply(c, c1, "/x/old", "E0", pilot_item="t1", TC=TC)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual((d["event"], d["event_lineage"]), ("E1", ["E0"]))
        c2 = dict(cand(), tree="/x/new2", config={"event": "E2"}, manifest_hash="aa" * 32)
        apply(c, c2, "/x/new", "E1", pilot_item="t1", TC=TC)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual((d["event"], d["event_lineage"]), ("E2", ["E0", "E1"]))
        c3 = mk()
        apply(c3, cand(), "/x/old", "E0", pilot_item="t1", TC=TC)                      # the event did not change: no lineage entry
        self.assertNotIn("event_lineage", json.loads((c3 / "autopilot/kit_wave.json").read_text())["dies"]["kv"])

    def test_apply_adds_the_event_to_gate_events_extra(self):
        """the wave gate refuses an event that is not a plan of record: the apply must add its label atomically (HEAD NF15f was OFF 3 h)"""
        c = mk()
        apply(c, dict(cand(), config={"event": "E1"}), "/x/old", "E0", pilot_item="t1", TC=TC)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["gate_events_extra"], ["E1"])
        apply(c, dict(cand(), tree="/x/new2", config={"event": "E2"}, manifest_hash="aa" * 32), "/x/new", "E1", pilot_item="t1", TC=TC)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["gate_events_extra"], ["E1", "E2"])

    def test_default_pilot_item_is_the_smallest_known_item(self):
        c = mk()
        apply(c, cand(), "/x/old", "E0", TC=TC)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["pilot_item"], "t1")

    def test_no_resolvable_pilot_refuses_before_writing(self):
        c = mk({"hold_event_items": {}})
        with self.assertRaises(SystemExit):
            apply(c, cand(), "/x/old", "E0", TC=TC)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["src"], "/x/old")                         # untouched
        r = apply(c, cand(), "/x/old", "E0", no_pilot=True, TC=TC)
        self.assertEqual(r["pilot"], "NONE")

    def test_stale_expectation_refused(self):
        c = mk()
        with self.assertRaises(AssertionError):
            apply(c, cand(), "/x/other", "E0", pilot_item="t1", TC=TC)


class KeepGenHosts(unittest.TestCase):
    """HEAD-DIE-R (COORD r400/r401): keep_gen_hosts keeps the die's current gen_hosts, guarded and fail-closed."""

    def _tc(self, seen, mutate=None):
        class T(TC):
            @staticmethod
            def identity(die, tree, want, hosts, checker):
                seen.append(sorted(hosts)); return dict(die=die, tree=tree, hosts=sorted(hosts))
            @staticmethod
            def read(d, ident):
                if mutate:
                    mutate()
                return dict(state="ok", full_ok=True, running=False, main_sha="a" * 40)
        return T

    def test_keeps_current_hosts_and_guards_them(self):
        c = mk({"gen_hosts": ["epyc10", "epyc8"], "gen_host": "epyc8"})
        seen = []
        o = dict(cand(), config={"gen_hosts": ["epyc10"], "gen_host": "epyc10"})
        apply(c, {"marker": o, "keep_gen_hosts": True}, "/x/old", "E0", pilot_item="t1", TC=self._tc(seen))
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["gen_hosts"], ["epyc10", "epyc8"]); self.assertEqual(d["gen_host"], "epyc8")
        self.assertEqual(seen, [["epyc10", "epyc8"]])

    def test_flag_argument_equals_candidate_key(self):
        c = mk({"gen_hosts": ["epyc10", "epyc8"]})
        apply(c, cand(), "/x/old", "E0", pilot_item="t1", TC=self._tc([]), keep_gen_hosts=True)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["gen_hosts"], ["epyc10", "epyc8"]); self.assertEqual(d["gen_host"], "epyc10")

    def test_hosts_changed_after_guard_read_refuses_untouched(self):
        c = mk({"gen_hosts": ["epyc10", "epyc8"]})
        p = c / "autopilot/kit_wave.json"
        def mutate():
            cfg = json.loads(p.read_text()); cfg["dies"]["kv"]["gen_hosts"] = ["epyc10"]; p.write_text(json.dumps(cfg))
        with self.assertRaises(AssertionError):
            apply(c, {"marker": cand(), "keep_gen_hosts": True}, "/x/old", "E0", pilot_item="t1", TC=self._tc([], mutate))
        d = json.loads(p.read_text())["dies"]["kv"]
        self.assertEqual(d["src"], "/x/old"); self.assertFalse((c / "lanes/handoff/tree_switch_kv.json").exists())

    def test_no_current_hosts_refuses(self):
        c = mk()
        with self.assertRaises(AssertionError):
            apply(c, {"marker": cand(), "keep_gen_hosts": True}, "/x/old", "E0", pilot_item="t1", TC=self._tc([]))

    def test_default_never_narrows_the_die_it_replicates_or_refuses(self):
        """FABLE-FLOW-1700 item 3: the candidate lists only epyc10 but the die serves epyc10 and epyc8: the tree is replicated to epyc8 (and verified) before the switch, else nothing is applied"""
        seen = []
        orig = A.ensure_tree_on_hosts
        A.ensure_tree_on_hosts = lambda tree, want, cur, hosts, rt, run=None, link_from="": (seen.append((cur, hosts)) or (list(hosts) + [h for h in cur if h not in hosts], ["replicated"]))
        try:
            c = mk({"gen_hosts": ["epyc10", "epyc8"]})
            apply(c, cand(), "/x/old", "E0", pilot_item="t1", TC=self._tc([]))
        finally:
            A.ensure_tree_on_hosts = orig
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(seen, [(["epyc10", "epyc8"], ["epyc10"])])
        self.assertEqual(sorted(d["gen_hosts"]), ["epyc10", "epyc8"])
        c2 = mk({"gen_hosts": ["epyc10", "epyc8"]})
        A.ensure_tree_on_hosts = lambda *a, **k: (_ for _ in ()).throw(SystemExit("REPLICATE: failed; nothing applied"))
        try:
            with self.assertRaises(SystemExit):
                apply(c2, cand(), "/x/old", "E0", pilot_item="t1", TC=self._tc([]))
        finally:
            A.ensure_tree_on_hosts = orig
        self.assertEqual(json.loads((c2 / "autopilot/kit_wave.json").read_text())["dies"]["kv"]["src"], "/x/old")           # untouched


def test_commit_apply_commits_the_written_files_through_coord_commit(tmp_path):
    import os
    coord = tmp_path / "coord"; (coord / "bin").mkdir(parents=True); (coord / "lanes/handoff").mkdir(parents=True); (coord / "autopilot").mkdir()
    (coord / "bin/coord-commit.sh").write_text('#!/bin/bash\necho "$@" > "$(dirname "$0")/../called.txt"\n')
    receipt = coord / "lanes/handoff/s81_atomic_apply_1.json"; receipt.write_text("{}")
    out = A.commit_apply(str(coord), {"applied": "s81", "event": "ev1", "receipt": str(receipt)})
    assert out == "ok"
    called = (coord / "called.txt").read_text()
    assert "autopilot/kit_wave.json" in called and "tree_switch_s81.json" in called and "s81_atomic_apply_1.json" in called
    assert A.commit_apply(str(tmp_path / "nocoord"), {"applied": "s81"}).startswith("skipped")


def test_ensure_tree_drops_a_host_that_cannot_take_the_tree():
    """LATENCY-R 11-18 (QC N3 blocked on a full intel1): per-host replicate; a refusal drops that host, the rest apply"""
    cmds = []

    def run(cmd):
        cmds.append(cmd)
        if "--hosts intel1" in cmd:
            return (1, "intel1: refuse (free 0 GB)")            # no copy there: the verify-first check fails, then replicate is refused
        return (0, "OK")
    hosts, notes = A.ensure_tree_on_hosts("/t", "h", ["epyc9", "intel1", "epyc8"], ["epyc9"], "/rt", run=run)
    assert hosts == ["epyc9", "epyc8"]
    assert any(n.startswith("DROPPED intel1") for n in notes) and notes[0].startswith("replicated from epyc9 and verified on epyc8")


def test_ensure_tree_keeps_a_host_that_already_holds_a_verified_copy_without_replicating():
    """QC N4.2 11-19: epyc10 was dropped 3 times with 'target exists' because replicate ran against a finished copy; verify first, keep, no replicate"""
    cmds = []

    def run(cmd):
        cmds.append(cmd)
        return (0, "OK")
    hosts, notes = A.ensure_tree_on_hosts("/t", "h", ["epyc9", "epyc10"], ["epyc9"], "/rt", run=run)
    assert hosts == ["epyc9", "epyc10"] and any("epyc10: already holds a verified copy" in n for n in notes)
    assert not any("replicate" in c for c in cmds)


def test_optimistic_apply_is_advisory_and_launches_every_type():
    """COORD 11-18: no gate record, guard not ready, smoke not PASS -> applied with warnings; no pilot hold"""
    class NoPG:
        @staticmethod
        def require_pass(*a): return "no PASS record"

    class TCbad(TC):
        @staticmethod
        def read(d, ident): return dict(state="running", full_ok=False, running=True)
    c = mk()
    r = A.apply_marker(c, dict(cand(), smoke="NOTRUN", optimistic=True), "/x/old", "E0", TC=TCbad, PG=NoPG)
    d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
    assert d["src"] == "/x/new" and r["pilot"] == "NONE" and r["optimistic"]
    assert not [x for x in d.get("hold_records") or [] if x.get("auto_pilot")]
    assert any("publish_gate" in w for w in r["warnings"]) and any("guard" in w for w in r["warnings"]) and any("smoke" in w for w in r["warnings"])
    c2 = mk()
    try:
        A.apply_marker(c2, cand(), "/x/old", "E0", pilot_item="t1", TC=TC, PG=NoPG)          # the strict path is unchanged
        raise SystemExit("strict apply passed without a gate record")
    except AssertionError:
        pass


class RepointEnv(unittest.TestCase):
    def test_gen_env_paths_into_the_old_tree_follow_the_new_tree_and_a_missing_file_fails(self):
        import apply_reviewed_tree_marker as A
        d = {"die_gen_env": {"OT_SIGNED_VIEW_SHA": "/k/old/physical/sv.json", "OT_X": "/k/other/f", "OT_N": "4"}, "item_env": {"i": {"OT_Y": "/k/old/a"}}}
        done = A.repoint_gen_env(d, "/k/old", "/k/new", exists=lambda p: True)
        self.assertEqual(d["die_gen_env"]["OT_SIGNED_VIEW_SHA"], "/k/new/physical/sv.json")
        self.assertEqual((d["die_gen_env"]["OT_X"], d["item_env"]["i"]["OT_Y"]), ("/k/other/f", "/k/new/a"))
        self.assertEqual(len(done), 2)
        d2 = {"die_gen_env": {"OT_SIGNED_VIEW_SHA": "/k/old/physical/sv.json"}}
        with self.assertRaises(SystemExit):
            A.repoint_gen_env(d2, "/k/old", "/k/new", exists=lambda p: False)
