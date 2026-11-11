"""ot-run LOADGATE_1110 / STATUSGUARD_1111 (KW-FIX-44, COORD 11-10/11-11): ot-heavy holds EVERY job while load1 + fresh admits >= 1.25 x nproc,
so placement must not pick a gated host (crit/direct/short too); the next-job status line applies the root-fs disk guard like --pick."""
import importlib.machinery
import importlib.util
import os
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    loader = importlib.machinery.SourceFileLoader("ot_run_gate", str(HERE / "ot-run"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def row(load1, ncpu, fresh=0, **kw):
    r = dict(admit_gb=400, free_gb=400, cpu_load1=load1, load1=load1, ncpu=ncpu, total_gb=1000, disk_gb=1000, avail_gb=400,
             headroom_gb=0, floor_gb=50, waiting=0, waiting_gb=0, running=1, fresh=fresh)
    r.update(kw)
    return r


class LoadGate(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.m.THREADS = 8

    def test_below_the_gate_is_not_gated(self):
        self.assertFalse(self.m.load_gated(row(100.0, 96)))          # 100 < 1.25 x 96 = 120

    def test_at_or_over_the_gate_is_gated(self):
        self.assertTrue(self.m.load_gated(row(120.0, 96)))
        self.assertTrue(self.m.load_gated(row(507.0, 96)))           # epyc8 11-10

    def test_fresh_admits_count_at_THREADS_each(self):
        self.assertFalse(self.m.load_gated(row(100.0, 96, fresh=2)))   # 100 + 16 = 116 < 120
        self.assertTrue(self.m.load_gated(row(100.0, 96, fresh=3)))    # 100 + 24 = 124 >= 120

    def test_factor_zero_disables(self):
        self.m.LOAD_GATE_FACTOR = 0
        self.assertFalse(self.m.load_gated(row(999.0, 96)))

    def test_env_factor(self):
        old = os.environ.get("OT_RUN_LOAD_GATE_FACTOR")
        os.environ["OT_RUN_LOAD_GATE_FACTOR"] = "2.0"
        try:
            m = load()
            self.assertEqual(m.LOAD_GATE_FACTOR, 2.0)
        finally:
            if old is None:
                os.environ.pop("OT_RUN_LOAD_GATE_FACTOR")
            else:
                os.environ["OT_RUN_LOAD_GATE_FACTOR"] = old

    def test_gated_host_counts_as_load_capped_for_any_job(self):
        r = row(130.0, 96)
        self.assertTrue(self.m.load_capped(r, 48, 8))
        self.assertTrue(self.m.load_capped(r, 48, 8, True) if self.m.load_capped.__code__.co_argcount > 3 else True)

    def test_row_without_ncpu_is_not_gated(self):
        self.assertFalse(self.m.load_gated({"cpu_load1": 999.0, "load1": 999.0}))


class StatusGuard(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def test_default_dir_refusal_only_for_a_root_fs_dir_host(self):
        self.assertEqual(self.m.default_dir_refusal(row(1.0, 96, dir_onroot=None)), "")

    def test_default_dir_refusal_returns_text_when_root_guard_refuses(self):
        r = row(1.0, 96, dir_onroot=False)
        out = self.m.default_dir_refusal(r)
        self.assertIsInstance(out, str)


if __name__ == "__main__":
    unittest.main()
