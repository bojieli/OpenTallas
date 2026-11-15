"""SPILL-PROOF-1: a spilled PLACE hands its physical result to the source host at phase_done while the proof stays on the
spill host.  Real copy commands with test_ot_run_spill's fake ssh (one directory tree per host), the real kit_wave
PLACE_RECEIPT and the real lec_async.sh."""
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import threading
import time
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_ot_run_spill as base  # noqa: E402

REPO_TOOLS = HERE.parent
_w = (REPO_TOOLS / "autopilot" / "kit_wave.py").read_text()
PLACE_RECEIPT = re.search(r'PLACE_RECEIPT = r"""(.*?)"""', _w, re.S).group(1)
LEC_ASYNC = REPO_TOOLS / "die_plan" / "lec_async.sh"


def write(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    return path


class Handoff(base.Spill):
    # only the new tests; the inherited setUp/tearDown give the fake hosts
    for _n in [n for n in dir(base.Spill) if n.startswith("test_")]:
        locals()[_n] = None
    del _n

    def setUp(self):
        super().setUp()
        self.kit = self.root + "/gen/kit"
        self.k_src = self.host("src") + "/gen/kit"
        self.k_dst = self.host("dst") + "/gen/kit"
        write(self.k_src + "/config.mk", "export DESIGN_NAME = x\n")
        write(self.k_src + "/lec.py", "# proof driver\n")
        write(self.k_src + "/rtl/a.v", "module a; endmodule\n")
        self.st = self.stamp()
        self.roots = [self.kit]
        self.m.STAGE[:] = [self.kit]
        self.assertEqual(self.m.spill_copy_fwd("src", "dst", self.roots, self.st).returncode, 0)
        time.sleep(0.02)
        self.rec = dict(tag="h1", pid=os.getpid(), src="src", dst="dst", roots=self.roots, stamp=self.st, unit="u", t=0, cmd="x")
        self.say = []

    def tearDown(self):
        self.m.STAGE[:] = []
        super().tearDown()

    def run_place(self, rc=0, pending=True, goal="place"):
        """what the place flow leaves on the spill copy at phase_done, in lec_async.sh's own file layout"""
        k = self.k_dst
        odb = write(k + "/run/results/asap7/x/base/3_place.odb", "ODB" * 100)
        ns = (time.time_ns() // 10**9 + 1) * 10**9 + 348316942      # newer than the stamp, with sub-second digits
        os.utime(odb, ns=(ns, ns))
        write(k + "/run/logs/asap7/x/base/3_place.log", "placed\n")
        write(k + "/lec_async.ready", "1\npython3 -I /work/lec.py /work --out /work/lec > /work/lec_run.log 2>&1\n")
        write(k + "/lec_async.source_identity", "src\n")
        write(k + "/lec_async.owner", "owner1\n")
        write(k + "/lec_async.pid", "4242\n")
        write(k + "/lec_async.on")
        write(k + "/lec_async.lock")
        write(k + "/lec_async.log", "LEC_ASYNC start\n")
        write(k + "/lec_run.log", "running\n")
        write(k + "/lec/gold.aig", "partial proof\n")
        ident = subprocess.run(["bash", "-c", f"source <(sed -n '/^identity()/,/^}}/p' {LEC_ASYNC}); identity {shlex.quote(k)}"],
                               capture_output=True, text=True, check=True).stdout.strip()
        write(k + "/lec_async.identity", ident + "\n")
        write(k + "/lec_async.runs/owner1.json", json.dumps(dict(run_id="owner1", goal=goal, started=time.time())) + "\n")
        st = os.stat(odb)
        r = dict(schema="opentallas.physical_completion.v1", goal=goal, rc=rc, run_id="owner1", started=time.time(),
                 proof_id=ident, proof_owner="owner1", proof_pending=pending, host="dst-host",
                 checkpoint=dict(path="run/results/asap7/x/base/3_place.odb", size=st.st_size, mtime_ns=st.st_mtime_ns))
        write(k + "/physical_completion/owner1.json", json.dumps(r) + "\n")
        return r

    def receipt_on_src(self):
        p = subprocess.run([sys.executable, "-c", PLACE_RECEIPT, self.k_src, "0"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = [ln for ln in p.stdout.splitlines() if ln.startswith("KW_PLACE_RECEIPT ")]
        return json.loads(got[-1][len("KW_PLACE_RECEIPT "):]) if got else None

    def handoff(self, **kw):
        return self.m.spill_handoff("src", "dst", self.roots, self.kit, self.st, self.rec, self.say.append, **kw)

    def lec_async(self, *args, timeout=30):
        return subprocess.run(["bash", str(LEC_ASYNC), *args], capture_output=True, text=True, timeout=timeout)

    def test_due_only_for_a_fresh_ok_receipt_with_pending_proof(self):
        ok = json.dumps(dict(schema="opentallas.physical_completion.v1", goal="place", rc=0, proof_pending=True))
        due = self.m.handoff_due
        self.assertTrue(due(ok, "place"))
        self.assertFalse(due(ok, "route"))
        self.assertFalse(due(ok.replace('"rc": 0', '"rc": 3'), "place"), "a failed place stays on the full back-copy")
        self.assertFalse(due(ok.replace("true", "false"), "place"), "a finished proof: the client ends by itself")
        self.assertFalse(due(ok + "\nOT_STOP", "place"))
        self.assertFalse(due(ok + "\nOT_NOSTAMP", "place"))
        self.assertFalse(due("garbage\n", "place"))

    def test_state_cmd_sees_only_a_receipt_of_this_run(self):
        write(self.k_src + "/physical_completion/old.json", "{}")   # would be a stale forward copy
        self.run_place()
        os.utime(self.k_dst + "/physical_completion/owner1.json", (1, 1))
        out = self.m.ssh_sh("dst", self.m.handoff_state_cmd(self.kit, self.st)).stdout
        self.assertFalse(self.m.handoff_due(out, "place"))
        os.utime(self.k_dst + "/physical_completion/owner1.json")
        out = self.m.ssh_sh("dst", self.m.handoff_state_cmd(self.kit, self.st)).stdout
        self.assertTrue(self.m.handoff_due(out, "place"))
        write(self.k_dst + "/lec_async.stop")
        out = self.m.ssh_sh("dst", self.m.handoff_state_cmd(self.kit, self.st)).stdout
        self.assertFalse(self.m.handoff_due(out, "place"), "a stopped proof never releases a route")

    def test_physical_result_and_receipt_reach_src_and_the_wave_accepts_them(self):
        self.assertIsNone(self.receipt_on_src())
        r = self.run_place()
        self.assertTrue(self.handoff(), self.say)
        got = self.receipt_on_src()
        self.assertIsNotNone(got, "the wave's own check must accept the receipt (checkpoint mtime_ns kept)")
        self.assertEqual(got["proof_owner"], "owner1")
        self.assertEqual(os.stat(self.k_src + "/" + r["checkpoint"]["path"]).st_mtime_ns, r["checkpoint"]["mtime_ns"])
        for f in ("lec_async.identity", "lec_async.ready", "lec_async.owner", "lec_async.on", "lec_async.runs/owner1.json"):
            self.assertTrue(os.path.exists(f"{self.k_src}/{f}"), f)
        for f in ("lec", "lec_run.log", "lec_async.log", "lec_async.pid", "lec_async.done", "lec_async.rc"):
            self.assertFalse(os.path.exists(f"{self.k_src}/{f}"), f + " belongs to the proof on dst")
        self.assertEqual(open(f"{self.k_src}/{self.m.PROOF_AWAY}").read().strip(), "dst")
        self.assertFalse(os.path.exists(self.st + ".next"))
        self.assertTrue(self.rec["late"])
        self.assertEqual(json.load(open(os.path.join(self.m.SPILL_PENDING, "h1.json")))["late"], self.rec["late"])

    def test_final_back_copy_cannot_meet_the_route(self):
        self.run_place()
        self.assertTrue(self.handoff(), self.say)
        # the route on src
        write(self.k_src + "/run/logs/asap7/x/base/5_route.log", "route on src\n")
        cfg = self.k_src + "/run/results/asap7/x/base/3_place.odb"
        # newer on dst than anything on src: must still stay on dst
        write(self.k_dst + "/run/results/asap7/x/base/4_cts.odb", "beside\n")
        write(self.k_dst + "/run/logs/asap7/x/base/5_route.log", "stale from the spill copy\n")
        write(self.k_dst + "/image.txt", "end\n")
        os.utime(self.k_dst + "/run/logs/asap7/x/base/5_route.log", (time.time() + 100, time.time() + 100))
        # the proof ends on dst
        write(self.k_dst + "/lec/lec.json", '{"verdict": "EQUIVALENT"}')
        write(self.k_dst + "/lec_async.rc", "0\n")
        write(self.k_dst + "/lec_async.done")
        before = os.stat(cfg).st_mtime_ns
        ok, err = self.m.spill_copy_back("src", "dst", self.roots, self.st, only=self.rec["late"])
        self.assertTrue(ok, err)
        self.assertEqual(open(self.k_src + "/lec/gold.aig").read(), "partial proof\n", "older proof files must come too")
        self.assertIn("EQUIVALENT", open(self.k_src + "/lec/lec.json").read())
        for f in ("lec_async.rc", "lec_async.done", "lec_run.log", "lec_async.log"):
            self.assertTrue(os.path.exists(f"{self.k_src}/{f}"), f)
        self.assertEqual(open(self.k_src + "/run/logs/asap7/x/base/5_route.log").read(), "route on src\n")
        self.assertFalse(os.path.exists(self.k_src + "/run/results/asap7/x/base/4_cts.odb"))
        self.assertFalse(os.path.exists(self.k_src + "/image.txt"))
        self.assertEqual(os.stat(cfg).st_mtime_ns, before)
        self.assertFalse(os.path.exists(self.st))

    def test_sweep_of_a_dead_client_after_handoff_carries_only_the_proof(self):
        self.run_place()
        self.assertTrue(self.handoff(), self.say)
        write(self.k_dst + "/run/results/asap7/x/base/4_cts.odb", "beside\n")
        write(self.k_dst + "/lec_async.done")
        dead = subprocess.Popen(["true"])
        dead.wait()
        rec = dict(self.rec, pid=dead.pid, unit=None)
        self.m.pending_write(rec)
        self.assertEqual(self.m.spill_sweep(say=lambda m: None), 0)
        self.assertTrue(os.path.exists(self.k_src + "/lec_async.done"))
        self.assertFalse(os.path.exists(self.k_src + "/run/results/asap7/x/base/4_cts.odb"))

    def test_failed_physical_copy_releases_nothing(self):
        self.run_place()
        real = self.m.handoff_pipe
        self.m.handoff_pipe = lambda *a, **k: False
        self.assertFalse(self.handoff())
        self.m.handoff_pipe = real
        self.assertIsNone(self.receipt_on_src())
        self.assertFalse(os.path.exists(f"{self.k_src}/{self.m.PROOF_AWAY}"))
        self.assertNotIn("late", self.rec)
        # the full back-copy of the client end still brings everything
        ok, err = self.m.spill_copy_back("src", "dst", self.roots, self.st, only=self.rec.get("late"))
        self.assertTrue(ok, err)
        self.assertTrue(os.path.exists(self.k_src + "/lec/gold.aig"))

    def test_receipt_comes_last_and_a_retry_sends_only_the_receipt(self):
        self.run_place()
        real, seen = self.m.handoff_pipe, []

        def fail_receipt(cmd, what, say, tries=1):
            seen.append(what)
            return what != "receipt copy" and real(cmd, what, say, 1)
        self.m.handoff_pipe = fail_receipt
        self.assertFalse(self.handoff())
        self.assertEqual(seen[-1], "receipt copy")
        self.assertTrue(os.path.exists(self.k_src + "/run/results/asap7/x/base/3_place.odb"))
        self.assertIsNone(self.receipt_on_src())
        seen.clear()
        self.m.handoff_pipe = lambda cmd, what, say, tries=1: (seen.append(what), real(cmd, what, say, 1))[1]
        self.assertTrue(self.handoff(), self.say)
        self.assertEqual(seen, ["receipt copy"])
        self.assertIsNotNone(self.receipt_on_src())

    def test_unreadable_file_fails_the_physical_copy(self):
        if os.geteuid() == 0:
            self.skipTest("root reads everything")
        self.run_place()
        f = write(self.k_dst + "/run/secret.log", "x")
        os.chmod(f, 0)
        try:
            self.m.HANDOFF_TRIES = 1
            self.assertFalse(self.m.handoff_pipe(self.m.handoff_files_cmd(
                "src", "dst", self.roots, self.m.handoff_physical_listing(self.roots, self.kit, self.st)), "physical copy", self.say.append, 1))
        finally:
            os.chmod(f, 0o644)

    def test_route_of_a_handed_off_kit_does_not_spill_until_the_verdict_is_back(self):
        self.run_place()
        self.assertTrue(self.handoff(), self.say)
        self.assertTrue(self.m.proof_away("src", [self.kit]))
        plan, why, permanent = self.m.spill_plan("src", self.kit, ["bash", "x"], 8, 4, False, 0, set(), self.say.append)
        self.assertIsNone(plan)
        self.assertIn("proof", why)
        self.assertFalse(permanent, "only until the verdict is back")
        write(self.k_src + "/lec_async.done")
        self.assertFalse(self.m.proof_away("src", [self.kit]))

    def test_proof_away_fails_closed_on_an_unreachable_source(self):
        self.m.ssh_sh = lambda *a, **k: subprocess.CompletedProcess([], 255, "", "no route")
        self.assertTrue(self.m.proof_away("src", [self.kit]))

    def test_route_on_src_reuses_the_proof_by_identity_and_waits_for_the_verdict(self):
        """the real lec_async.sh of a kit generated before this fix: start = reuse (no second proof, no docker),
        cts/grt do not wait, route/finish wait for lec_async.done and take the stop rc"""
        self.run_place()
        self.assertTrue(self.handoff(), self.say)
        k = self.k_src
        s = self.lec_async("start", k, "route1", "img", "1", "1", "false", "route")
        self.assertEqual(s.returncode, 0, s.stderr)
        self.assertIn("reuse proof", s.stderr)
        self.assertFalse(os.path.exists(k + "/lec_async.pid"), "no watcher on the source host")
        self.assertEqual(self.lec_async("finish", k, "0", "5", "cts1", "cts").stdout.strip(), "0")
        self.assertEqual(self.lec_async("wait", k, "route1", "route", "0").returncode, 0, "the route container never waits")
        p = subprocess.Popen(["bash", str(LEC_ASYNC), "finish", k, "0", "5", "route1", "route"], stdout=subprocess.PIPE, text=True,
                             env=dict(os.environ, OT_LEC_ASYNC_POLL="0.1"))
        time.sleep(0.5)
        self.assertIsNone(p.poll(), "sign-off still waits for the proof's verdict")
        write(k + "/lec_async.stop")
        write(k + "/lec_async.done")
        self.assertEqual(p.communicate(timeout=20)[0].strip(), "5", "a NOT EQUIVALENT proof stops the kit before sign-off")

    def test_changed_proof_input_on_src_is_still_refused(self):
        self.run_place()
        self.assertTrue(self.handoff(), self.say)
        write(self.k_src + "/rtl/a.v", "module b; endmodule\n")
        s = self.lec_async("start", self.k_src, "route1", "img", "1", "1", "false", "route")
        self.assertEqual(s.returncode, 11, s.stderr)

    def spill_with(self, body, env=True):
        """spill_run with the real copies and a stub for the remote job"""
        os.environ.pop(self.m.HANDOFF_ENV, None)
        if env:
            os.environ[self.m.HANDOFF_ENV] = "place"
        self.m.HANDOFF_POLL_S = 0.1
        self.m.log_signal = lambda *a: None

        def fake_run(dst, mem, cmd, d, max_wait, on_start=None, disk=None, quiet_notrun=False):
            on_start("u1")
            return body(), True
        self.m.run = fake_run
        return self.m.spill_run("src", "dst", self.roots, 0.1, 8, ["bash", "x"], self.kit, None, self.say.append)

    def test_spill_run_hands_off_while_the_job_runs_then_copies_only_the_proof(self):
        def body():
            self.run_place()
            for _ in range(300):
                if self.receipt_on_src():
                    break
                time.sleep(0.05)
            self.assertIsNotNone(self.receipt_on_src(), self.say)      # released while the proof still runs
            self.assertFalse(os.path.exists(self.k_src + "/lec_async.done"))
            write(self.k_src + "/run/logs/asap7/x/base/5_route.log", "route on src\n")
            write(self.k_dst + "/lec/lec.json", "{}")
            write(self.k_dst + "/lec_async.done")
            write(self.k_dst + "/run/logs/asap7/x/base/5_route.log", "stale\n")
            os.utime(self.k_dst + "/run/logs/asap7/x/base/5_route.log", (time.time() + 100, time.time() + 100))
            return 0
        self.m.spill_drop_stage = lambda *a, **k: None
        self.assertEqual(self.spill_with(body), 0)
        self.assertTrue(os.path.exists(self.k_src + "/lec_async.done"))
        self.assertEqual(open(self.k_src + "/run/logs/asap7/x/base/5_route.log").read(), "route on src\n")
        self.assertFalse(os.path.exists(os.path.join(self.m.SPILL_PENDING, "%s.json" % "h1")))

    def test_spill_run_without_the_env_or_with_a_failed_place_keeps_the_full_back_copy(self):
        def body():
            self.run_place()
            time.sleep(0.4)
            self.assertFalse(os.path.exists(self.k_src + "/run"), "no hand-off")
            write(self.k_dst + "/lec_async.done")
            return 0
        self.m.spill_drop_stage = lambda *a, **k: None
        self.assertEqual(self.spill_with(body, env=False), 0)
        self.assertTrue(os.path.exists(self.k_src + "/run/results/asap7/x/base/3_place.odb"))

        self.tearDown()
        self.setUp()

        def failed():
            self.run_place(rc=3)
            time.sleep(0.4)
            self.assertFalse(os.path.exists(self.k_src + "/run"), "a failed place is not handed off")
            return 3
        self.m.spill_drop_stage = lambda *a, **k: None
        self.assertEqual(self.spill_with(failed), 3)
        self.assertTrue(os.path.exists(self.k_src + "/lec/gold.aig"), "its logs and files all come back")

    def test_cli_for_a_running_old_client(self):
        """--spill-handoff on a client whose final back-copy is stamp-only: older proof files go in the snapshot, the stamp
        moves, and that old final copy then brings only what dst wrote later"""
        self.run_place()
        self.m.pid_alive = lambda pid: True
        self.m.pending_write(self.rec)
        out = []
        self.assertEqual(self.m.spill_handoff_cli("h1", dry=True, say=out.append), 0)
        self.assertIn("DRY", out[-1])
        self.assertFalse(os.path.exists(self.k_src + "/run"), "a dry run writes nothing")
        self.assertEqual(self.m.spill_handoff_cli("h1", say=out.append), 0)
        self.assertIsNotNone(self.receipt_on_src())
        self.assertEqual(open(self.k_src + "/lec/gold.aig").read(), "partial proof\n")
        self.assertFalse(os.path.exists(self.k_src + "/lec_async.pid"))
        self.assertEqual(self.m.spill_handoff_cli("h1", say=out.append), 0, "idempotent")
        write(self.k_src + "/run/logs/asap7/x/base/5_route.log", "route on src\n")
        time.sleep(0.02)
        write(self.k_dst + "/lec/lec.json", "{}")
        write(self.k_dst + "/lec_async.done")
        old_final = subprocess.run(["bash", "-o", "pipefail", "-c", self.m.spill_back_cmd("src", "dst", self.roots, self.st)],
                                   capture_output=True, text=True)
        self.assertEqual(old_final.returncode, 0, old_final.stderr)
        self.assertTrue(os.path.exists(self.k_src + "/lec/lec.json"))
        self.assertTrue(os.path.exists(self.k_src + "/lec_async.done"))
        self.assertEqual(open(self.k_src + "/run/logs/asap7/x/base/5_route.log").read(), "route on src\n")
        self.assertFalse(os.path.exists(self.k_src + "/lec_async.stop"))

    def test_cli_refuses_when_not_due(self):
        self.m.pid_alive = lambda pid: True
        self.m.pending_write(self.rec)
        self.run_place(rc=3)
        self.assertEqual(self.m.spill_handoff_cli("h1", say=lambda m: None), 3)
        self.assertFalse(os.path.exists(self.k_src + "/run"))


if __name__ == "__main__":
    unittest.main()
