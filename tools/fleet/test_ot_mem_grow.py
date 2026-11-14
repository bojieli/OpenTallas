"""ot-mem-grow: raise a container cap by 50 % (max 2x its request) when it is above 85 % and the host can pay for it"""
import importlib.machinery, importlib.util, pathlib, unittest

P = str(pathlib.Path(__file__).with_name("ot-mem-grow"))
loader = importlib.machinery.SourceFileLoader("ot_mem_grow", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_mem_grow", loader))
loader.exec_module(M)
G = M.GB


class Grow(unittest.TestCase):
    def test_below_85_percent_nothing(self):
        self.assertIsNone(M.decide(32 * G, 32 * G, int(27 * G), 200, 48))        # 27 / 32 = 84 %

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


if __name__ == "__main__":
    unittest.main()
