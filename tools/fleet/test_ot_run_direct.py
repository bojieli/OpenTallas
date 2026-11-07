"""DIRECT_1107 (OWNER 11-07): ot-run --direct places on real free memory and ot-heavy starts it on MemAvailable >= mem + 32 GB."""
import importlib.machinery
import importlib.util
import os
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent


def load():
    loader = importlib.machinery.SourceFileLoader("ot_run_direct", str(HERE / "ot-run"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    return m


def row(admit, avail, load=300.0):
    return dict(admit_gb=admit, free_gb=admit, avail_gb=avail, cpu_load1=load, ncpu=128, total_gb=1000, disk_gb=1000,
                headroom_gb=0, floor_gb=50, waiting=0, waiting_gb=0, running=1, fresh=0)


class Choose(unittest.TestCase):
    def setUp(self):
        self.m = load()
        os.environ.pop("OT_RUN_DIRECT", None)
        self.addCleanup(os.environ.pop, "OT_RUN_DIRECT", None)

    def test_most_real_free_memory_wins(self):
        os.environ["OT_RUN_DIRECT"] = "1"
        self.assertEqual(self.m.choose({"a": row(-50, 300), "b": row(500, 200, load=1.0)}, 48), ("a", False))

    def test_headroom_is_the_floor(self):
        os.environ["OT_RUN_DIRECT"] = "1"
        self.assertEqual(self.m.choose({"a": row(500, 79), "b": row(500, 80)}, 48), ("b", False))
        self.assertEqual(self.m.choose({"a": row(500, 79), "b": row(500, 70)}, 48), ("a", True))    # waits, no start

    def test_off_by_default(self):
        self.assertEqual(self.m.choose({"a": row(-50, 300), "b": row(500, 200, load=1.0)}, 48)[0], "b")


class Heavy(unittest.TestCase):
    def test_block_sits_after_the_gates_and_keeps_the_floor(self):
        s = (HERE / "ot-heavy").read_text()
        self.assertLess(s.index("LOADCAP_1101 (FLOW-21"), s.index('if [ "${OT_HEAVY_DIRECT:-}" = 1 ]'))
        self.assertLess(s.index('if [ "${OT_HEAVY_DIRECT:-}" = 1 ]'), s.index('if [ "$V" = OK ]; then\n    echo "$UNIT $RES"'))
        self.assertIn('-ge $(( MEM + 32 ))', s)
