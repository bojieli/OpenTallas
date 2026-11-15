"""ot-mem-grow: raise a container cap by 50 % (max 2x its request) when it is above 85 % and the host can pay for it"""
import importlib.machinery, importlib.util, pathlib, unittest

P = str(pathlib.Path(__file__).with_name("ot-mem-grow"))
loader = importlib.machinery.SourceFileLoader("ot_mem_grow", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_mem_grow", loader))
loader.exec_module(M)
G = M.GB


class Grow(unittest.TestCase):
    def test_below_85_percent_nothing(self):
        self.assertIsNone(M.decide(32 * G, 32 * G, int(23 * G), 200, 48))        # 23 / 32 = 72 %
        self.assertEqual(M.decide(32 * G, 32 * G, int(24 * G), 200, 48), 48 * G)  # 75 %: the trigger moved down from 85 %

    def test_t28_case_32_to_48(self):
        self.assertEqual(M.decide(32 * G, 32 * G, int(28.7 * G), 200, 48), 48 * G)

    def test_second_step_is_capped_at_twice_the_request(self):
        self.assertEqual(M.decide(48 * G, 32 * G, int(45 * G), 200, 48), 64 * G)  # 48 x 1.5 = 72 -> 2 x 32 = 64
        self.assertIsNone(M.decide(64 * G, 32 * G, int(60 * G), 200, 48))          # already 2x

    def test_host_must_cover_the_increase_above_the_headroom(self):
        self.assertIsNone(M.decide(32 * G, 32 * G, int(30 * G), 63, 48))           # increase 16 GB > 63 - 48
        self.assertEqual(M.decide(32 * G, 32 * G, int(30 * G), 64, 48), 48 * G)

    def test_no_cap_no_action(self):
        self.assertIsNone(M.decide(0, 0, 10 * G, 200, 48))


    def test_scope_rows_read_memory_max_and_current(self):
        import tempfile, os
        d = tempfile.mkdtemp()
        base = os.path.join(d, "user.slice/user-1000.slice/user@1000.service/app.slice/oth-ubuntu-1-2.scope"); os.makedirs(base)
        open(base + "/memory.max", "w").write(str(48 * G)); open(base + "/memory.current", "w").write(str(40 * G))
        un = os.path.join(d, "user.slice/user-1000.slice/user@1000.service/app.slice/oth-ubuntu-3-4.scope"); os.makedirs(un)
        open(un + "/memory.max", "w").write("max"); open(un + "/memory.current", "w").write("1")
        import glob
        orig = glob.glob
        glob.glob = lambda pat: orig(pat.replace("/sys/fs/cgroup", d))
        try:
            rows = M.scope_rows()
        finally:
            glob.glob = orig
        self.assertEqual([(os.path.basename(r[0]), r[1], r[2]) for r in rows], [("oth-ubuntu-1-2.scope", 48 * G, 40 * G)])


    def test_refusal_is_reported_only_when_the_headroom_guard_said_no(self):
        self.assertEqual(M.refusal(32 * G, 32 * G, int(30 * G), 63, 48), 48 * G)       # wanted 16 GB, host has 15 above the headroom
        self.assertIsNone(M.refusal(32 * G, 32 * G, int(30 * G), 64, 48))              # funded: decide() raises it, nothing refused
        self.assertIsNone(M.refusal(64 * G, 32 * G, int(60 * G), 10, 48))              # already at 2x the request: not a refusal
        self.assertIsNone(M.refusal(32 * G, 32 * G, int(10 * G), 10, 48))              # below the trigger


if __name__ == "__main__":
    unittest.main()
