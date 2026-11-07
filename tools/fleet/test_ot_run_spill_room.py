"""AUTOCLEAN-3 11-07: a spill states what it writes; the target disk must hold it plus a margin, also against other copies."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from test_ot_run_spill import FAKE_SSH, load  # noqa: F401


def local_ssh(m):
    def run(host, cmd, timeout=120):
        return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=timeout)
    m.ssh_sh = run


class RoomTest(unittest.TestCase):
    def setUp(self):
        self.m = load()
        local_ssh(self.m)
        self.t = tempfile.mkdtemp(prefix="otroom")
        self.m.SPILL_RESV_DIR = self.t + "/resv"
        self.root = self.t + "/lane"
        os.makedirs(self.root)
        v = os.statvfs(self.t)
        self.free = v.f_bavail * v.f_frsize / 1e9

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.t])

    def test_fits_and_does_not(self):
        self.assertEqual(self.m.spill_room("h", [self.root], 0.001, 0)[0], True)
        fits, why = self.m.spill_room("h", [self.root], self.free + 100, 0)
        self.assertIs(fits, False)
        self.assertIn("free", why)
        # the margin counts: size alone fits, size + margin does not
        self.assertIs(self.m.spill_room("h", [self.root], 1, self.free)[0], False)

    def test_missing_root_lands_on_nearest_parent(self):
        self.assertEqual(self.m.spill_room("h", [self.t + "/new/lane/x"], 0.001, 0)[0], True)
        self.assertIs(self.m.spill_room("h", [self.t + "/new/lane/x"], self.free + 100, 0)[0], False)

    def test_existing_copy_is_not_charged_again(self):
        huge = self.free + 100                    # sparse: du -sb sees it, the disk does not
        with open(self.root + "/kit.bin", "wb") as f:
            f.truncate(int(huge * 1e9))
        self.assertIs(self.m.spill_room("h", [self.root], huge, 0)[0], True, "a re-spill sends only the delta")
        self.assertIs(self.m.spill_room("h", [self.root], huge + self.free + 100, 0)[0], False)

    def test_two_copies_are_charged_against_each_other(self):
        half = self.free * 0.6
        self.assertIs(self.m.spill_room("h", [self.root], half, 0, tag="fwd-a")[0], True)
        fits, why = self.m.spill_room("h", [self.root], half, 0, tag="fwd-b")
        self.assertIs(fits, False, "second copy must see the first one's reservation")
        self.assertIn("other copies", why)
        self.assertIs(self.m.spill_room("h", [self.root], half, 0, tag="fwd-a")[0], True, "own reservation is not charged twice")
        self.m.spill_room_release("h", "fwd-a")
        self.assertIs(self.m.spill_room("h", [self.root], half, 0, tag="fwd-b")[0], True)

    def test_dead_client_reservation_expires(self):
        half = self.free * 0.6
        self.assertIs(self.m.spill_room("h", [self.root], half, 0, tag="fwd-a")[0], True)
        p = self.m.SPILL_RESV_DIR + "/fwd-a.json"
        x = json.load(open(p))
        x["t"] -= self.m.SPILL_RESV_TTL_S + 1
        with open(p, "w") as f:
            json.dump(x, f)
        self.assertIs(self.m.spill_room("h", [self.root], half, 0, tag="fwd-b")[0], True)
        self.assertFalse(os.path.exists(p))

    def test_failed_probe_is_unknown(self):
        self.m.ssh_sh = lambda host, cmd, timeout=120: subprocess.CompletedProcess([], 255, "", "ssh: no route")
        self.assertIsNone(self.m.spill_room("h", [self.root], 1, 0)[0])


class BackCopyTest(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.m.SPILL_BACK_ROOM_POLL_S = 0
        self.m.SPILL_BACK_TRIES = 1
        self.tars = []
        self.released = []
        self.m.ssh_sh = lambda host, cmd, timeout=120: subprocess.CompletedProcess([], 0, "", "")
        self.m.spill_room_release = lambda host, tag: self.released.append(tag)
        self.m.spill_back_size_gb = lambda dst, roots, stamp, only=None: 78.0
        self.m.spill_repair_partials = lambda *a, **k: ""
        run = subprocess.run

        def fake(a, **k):
            self.tars.append(a)
            return subprocess.CompletedProcess(a, 0, "", "")
        self.m.subprocess.run, self.restore = fake, run

    def tearDown(self):
        self.m.subprocess.run = self.restore

    def test_no_room_starts_no_writer(self):
        self.m.spill_room = lambda *a, **k: (False, "epyc4: free 52 GB")
        ok, err = self.m.spill_copy_back("epyc4", "intel2", ["/r"], "/tmp/st")
        self.assertFalse(ok)
        self.assertIn(self.m.SPILL_NOROOM, err)
        self.assertEqual(self.tars, [], "the 06:08 failure: a writer started on a full disk")

    def test_waits_then_copies_and_releases(self):
        answers = [(False, "full"), (False, "full"), (True, "")]
        self.m.spill_room = lambda *a, **k: answers.pop(0)
        ok, err = self.m.spill_copy_back("epyc4", "intel2", ["/r"], "/tmp/st", wait_s=3600)
        self.assertTrue(ok, err)
        self.assertEqual(len(self.tars), 1)
        self.assertEqual(self.released, ["back-st"])

    def test_margin_and_size_reach_the_check(self):
        seen = {}

        def room(host, roots, need, margin, tag=None):
            seen.update(host=host, need=need, margin=margin, tag=tag)
            return True, ""
        self.m.spill_room = room
        self.m.spill_copy_back("epyc4", "intel2", ["/r"], "/tmp/st")
        self.assertEqual(seen, dict(host="epyc4", need=78.0, margin=self.m.SPILL_BACK_MARGIN_GB, tag="back-st"))

    def test_unknown_never_holds_results_back(self):
        self.m.spill_room = lambda *a, **k: (None, "ssh")
        self.assertTrue(self.m.spill_copy_back("epyc4", "intel2", ["/r"], "/tmp/st")[0])
        self.m.spill_back_size_gb = lambda *a, **k: None
        self.assertTrue(self.m.spill_copy_back("epyc4", "intel2", ["/r"], "/tmp/st")[0])


class SizeListingTest(unittest.TestCase):
    def test_size_uses_the_copy_listing(self):
        m = load()
        local_ssh(m)
        t = tempfile.mkdtemp(prefix="otsize")
        try:
            root = t.lstrip("/") + "/lane"
            os.makedirs("/" + root)
            st = t + "/stamp"
            open(st, "w").close()
            os.utime(st, (1_000_000_000, 1_000_000_000))
            with open("/" + root + "/out.bin", "wb") as f:
                f.write(b"x" * 1_000_000)
            got = m.spill_back_size_gb("h", ["/" + root], st)
            self.assertAlmostEqual(got, 0.001, places=3)
        finally:
            subprocess.run(["rm", "-rf", t])


class ForwardPlanTest(unittest.TestCase):
    def test_full_host_dropped_for_one_with_room(self):
        m = load()
        m.SPILL_MAX_GB = 1000
        m.spill_paths_ok = lambda cmd, d, root: ("", set())
        m.spill_scan = lambda src, roots, strict=False: ([], 78.0, "", False, set())
        m.HOSTS[:] = ["src", "full", "roomy"]
        row = lambda: dict(ncpu=128, disk_gb=500, free_gb=500, admit_gb=500, cpu_load1=1.0, mem_total_gb=700)
        m.probe = lambda h, b, spill_ok=False: (h, row())
        m.physically_capable = lambda r, mem: True
        m.host_refusal = lambda r: ""
        m.spill_dst_full = lambda h, r, roots=(), cmd=(): False
        m.drop_low_disk = lambda ok, die, need, say=None: ok
        m.choose = lambda ok, mem, threads, die: (sorted(ok)[0] if ok else None, False)
        m.spill_room = lambda h, roots, need, margin, tag=None: (h == "roomy", f"{h}: free 52 GB")
        lane = "/srv/opentallas-scratch2/claude/l"
        plan, why, perm = m.spill_plan("src", lane + "/k", ["x"], 8, 4, False, 20, set(), print)
        self.assertIsNotNone(plan, why)
        self.assertEqual(plan[0], "roomy")
        m.spill_room = lambda h, roots, need, margin, tag=None: (False, f"{h}: free 52 GB")
        plan, why, perm = m.spill_plan("src", lane + "/k", ["x"], 8, 4, False, 20, set(), print)
        self.assertIsNone(plan)
        self.assertFalse(perm, "no room is not permanent: the caller waits and places again")
        self.assertIn("no spill host has room", why)


if __name__ == "__main__":
    unittest.main()
