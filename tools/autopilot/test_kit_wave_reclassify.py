#!/usr/bin/env python3
"""KIT-TRIAGE-1/G26 (11-01): kit-wave reasons carry the decisive error line (ot-run admission chatter stripped), the
G6 failure groups get named classes, and 'kit_wave.py reclassify' re-reads stored FAIL logs with the current RULES.
Snippets are the real 10-31/11-01 hub evidence (kit_wave/<item>/a<n>/*.log)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

ADMIT = ("ot-run: intel1         admits   266 GB (avail 493, reserve 0, fresh 139.3, peak 23.5, headroom 0, waiters 0/0 GB)"
         " load 77/112 running 38 disk 608 GB \not-run: -> intel1\not-heavy: request 16G is charged 9G (class 'gen.py:phys'"
         " measured peak 0.4G, n=6+0 proved); the cap stays 16G\not-heavy: admitted on key-cardinal as "
         "oth-ubuntu-302855-1793425708 after 1 s\n")
TB = 'Traceback (most recent call last):\n  File "/x/tools/die_plan/gen.py", line 295, in <module>\n    sys.exit(main())\n'


def log(body, rc=1):
    return ADMIT + body + f"\not-run: RAN on intel1 (unit oth-ubuntu-302855-1793425708): exit {rc}\n"


class Reasons(unittest.TestCase):
    def test_traceback_reason_is_the_exception_not_admission(self):
        cls, why = KW.classify("gen", log(TB + "IndexError: list index out of range"))
        self.assertEqual(cls, "INFRA")      # WF-1 11-14 (owner #2): a Python exception at kit_rtl/gen no rule names PLAN/RTL is INFRA
        self.assertIn("IndexError: list index out of range", why)
        self.assertNotIn("key-cardinal", why)
        self.assertNotIn("Traceback", why)

    def test_unclassified_names_the_last_error_line(self):
        cls, why = KW.classify("place", log("step 3\nsomething odd: widget count 7 mismatched\nOT_X FAIL widget"))
        self.assertTrue(why.startswith("unclassified failure @place (see log): "), why)
        self.assertIn("OT_X FAIL widget", why)

    def test_infra_still_reads_ot_run_lines(self):
        self.assertEqual(KW.classify("place", log("x", rc=137))[0], "INFRA")
        self.assertEqual(KW.classify("gen", "ot-run: NOT RUN (no host admits 16 GB)")[0], "INFRA")

    def test_missing_hostname_is_transport_not_design(self):
        text = "ssh: Could not resolve hostname intel2: Temporary failure in name resolution"
        self.assertEqual(KW.classify("mkdir", text)[0], "INFRA")
        self.assertTrue(KW.SSH_DROP.search(text))

    def test_gen_lint_killed_yosys_is_infra_not_rtl(self):
        text = "GEN_LINT FAIL rtl_check: yosys elaboration failed rc 137 (gen_lint_yosys.log)"
        self.assertEqual(KW.classify("gen_lint", log(text))[0], "INFRA")
        self.assertEqual(KW.classify("gen_lint", log("GEN_LINT FAIL rtl_check: undriven port q"))[0], "RTL")

    def test_s81_bind_source_missing_is_named_flow(self):
        cls, why = KW.classify("kit_rtl", log("bind: ERROR preferred HDL source missing: /srv/x/wt/die-s81-41-bind/"
                                              "physical/rom_host_ingest/rtl/dsfd_host.sv; restore the source checkout", 2))
        self.assertEqual(cls, "FLOW")
        self.assertIn("pruned bind worktree", why)
        self.assertIn("dsfd_host.sv", why)

    def test_qc_id_only_parameter_sets_are_plan(self):
        sets = ["#(.S_u_fab_u_x_2_2_sidx(3'b101), .S_u_t_2_2_tile_id(16'b0000000000000000))",
                "#(.S_u_fab_u_x_2_2_sidx(3'b101), .S_u_t_2_2_tile_id(16'b0000000000110000))"]
        t = f"bind: ERROR kit-rtl cbf_q11: instances of qfd_qc_cb_f_q11 carry different parameters {sets}: pass --instance (one kit per value set)"
        cls, why = KW.classify("kit_rtl", log(t, 2))
        self.assertEqual(cls, "PLAN")
        self.assertIn("parent_id_straps", why)
        self.assertIn("S_u_t_2_2_tile_id", why)
        self.assertNotIn("sidx", why)                 # equal across instances: not part of the diff
        logic = [x.replace("tile_id", "mode") for x in sets]
        t2 = f"bind: ERROR kit-rtl c: instances of c carry different parameters {logic}: pass --instance (one kit per value set)"
        cls2, why2 = KW.classify("kit_rtl", t2)
        self.assertEqual(cls2, "PLAN")                 # DIE-QC-97: LOGIC value sets -> plan split per value set
        self.assertIn("param_class_split.py", why2)

    def test_head_cohort_drift_is_plan(self):
        t = TB + "ValueError: bootstrap HEAD RTL differs from published source cohort"
        cls, why = KW.classify("kit_rtl", log(t))
        self.assertEqual(cls, "PLAN")
        self.assertIn("bootstrap HEAD RTL differs", why)

    def test_preflight_preflooor_lines(self):
        self.assertEqual(KW.classify("place", 'PORT_BIND FAIL {"extra": 48}\nFAIL_PREFLOOR port_bind')[1][:21],
                         "port bind (plan pins)")
        self.assertEqual(KW.classify("place", "FAIL_PREFLOOR port_bind")[0], "PLAN")
        cls, why = KW.classify("place", log("Warning: Wire top.\\u_sfu__side_y [0] is used but has no driver.\n"
                                            "ERROR: Found 65 problems in 'check -assert'.\nFAIL_PREFLOOR rtl_lint (FAIL or NOT RUN)", 8))
        self.assertEqual(cls, "RTL")

    def test_missing_tool_input_is_flow_with_path(self):
        t = TB + ("FileNotFoundError: [Errno 2] No such file or directory: '/srv/x/wt/kit-wave-5-kv/results/kv_host_regen_1/"
                  "rtl/qkd_hr_core_peer/qkd_hr_core_peer_core.json'")
        cls, why = KW.classify("gen", log(t))
        self.assertEqual(cls, "FLOW")
        self.assertIn("qkd_hr_core_peer_core.json", why)


class Reclassify(unittest.TestCase):
    def _state(self, t):
        d = Path(t, "kit_wave", "s81_x_b1", "a1")
        d.mkdir(parents=True)
        gen = log(TB + "ValueError: type x: macros have LEF but no timing liberty: " + ", ".join(
            f"u_x{i} (m{i})" for i in range(300)))
        (d / "gen.log").write_text(gen)
        # an old record: result.json without 'errors', tail = the last 3000 chars (the ValueError head cut off)
        (d / "result.json").write_text(json.dumps({"stage": "gen", "verdict": "FAIL", "tail": gen[-3000:]}))
        st = {"items": {
            "s81|x|b1": {"die": "s81", "item": "x", "status": "FAIL", "class": "FLOW", "attempt": 1, "stage": "gen",
                         "reason": "unclassified failure @gen (see log)", "dir": str(d)},
            "s81|y|b2": {"die": "s81", "item": "y", "status": "ENQUEUED", "class": "", "dir": str(d)}}}
        KW.save_state(st, t)
        return st

    def test_dry_run_and_write(self):
        with tempfile.TemporaryDirectory() as t:
            st = self._state(t)
            ch = KW.reclassify(st)
            self.assertEqual(len(ch), 1)
            key, old, new = ch[0]
            self.assertEqual((key, old[0], new[0]), ("s81|x|b1", "FLOW", "PLAN"))
            self.assertIn("WAIT-DEP", new[1])
            self.assertEqual(st["items"]["s81|x|b1"]["class"], "FLOW")         # dry run: untouched
            self.assertEqual(KW.main(["reclassify", "--ap-dir", t, "--quiet"]), 0)
            self.assertEqual(KW.load_state(t)["items"]["s81|x|b1"]["class"], "FLOW")
            self.assertEqual(KW.main(["reclassify", "--ap-dir", t, "--write", "--quiet"]), 0)
            rec = KW.load_state(t)["items"]["s81|x|b1"]
            self.assertEqual((rec["class"], rec["status"], rec["attempt"]), ("PLAN", "FAIL", 1))
            self.assertIn("WAIT-DEP", Path(t, KW.STAGES_FILE).read_text())
            self.assertEqual(KW.reclassify(KW.load_state(t)), [])             # idempotent
            # KW-FIX-1 11-02: a WAIT-DEP record is a dependency wait: PENDING-DEP in the stages table, not FAIL
            row = [ln.split("\t") for ln in Path(t, KW.STAGES_FILE).read_text().splitlines() if "\tx\t" in ln][0]
            self.assertEqual(row[KW.STAGE_COLS.index("status")], "PENDING-DEP")
            self.assertTrue(KW.is_wait_dep(rec))
            self.assertFalse(KW.is_wait_dep(dict(rec, reason="AUTO-GEOM rule FAIL (geometry)")))

    def test_record_from_another_result_is_left_alone(self):
        with tempfile.TemporaryDirectory() as t:
            st = self._state(t)
            st["items"]["s81|x|b1"]["stage"] = "geom"                       # recovery geom verdict, result.json says gen
            self.assertEqual(KW.reclassify(st), [])


if __name__ == "__main__":
    unittest.main()
