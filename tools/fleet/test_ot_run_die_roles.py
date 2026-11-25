"""Die role preferences must never hide a host that admits useful work now."""
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest

loader = importlib.machinery.SourceFileLoader("ot_run_die_roles", str(Path(__file__).with_name("ot-run")))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)

def row(admit, free=None):
    return dict(admit_gb=admit, free_gb=admit if free is None else free, ncpu=128, load1=0, fresh=0)

class DieRolePlacement(unittest.TestCase):
    def test_throughput_admits_while_normal_queues(self):
        self.assertEqual(m.choose({"ot-gold1":row(-27),"ot-epyc9":row(160)},150,die=True),("ot-epyc9",False))

    def test_small_disk_admits_while_normal_queues(self):
        self.assertEqual(m.choose({"ot-epyc5":row(40),"ot-epyc8":row(900)},300,die=True),("ot-epyc8",False))

    def test_normal_preferred_when_both_admit(self):
        self.assertEqual(m.choose({"ot-gold1":row(160),"ot-epyc9":row(900)},150,die=True),("ot-gold1",False))

    def test_normal_queue_preference_when_nobody_admits(self):
        self.assertEqual(m.choose({"ot-gold1":row(10),"ot-epyc9":row(100)},150,die=True),("ot-gold1",True))

    def test_admit_field_is_authoritative_despite_free_field(self):
        self.assertEqual(m.choose({"ot-gold1":row(-27,999),"ot-epyc9":row(160,0)},150,die=True),("ot-epyc9",False))

    def test_non_die_selection_unchanged(self):
        self.assertEqual(m.choose({"ot-gold1":row(-27),"ot-epyc9":row(160)},150),("ot-epyc9",False))

class DieLevelAutoClass(unittest.TestCase):
    """COORD 11-25 (45): compose / PRE / gate / bind / census commands are die class without --die"""
    def test_die_level_commands(self):
        for c in (["python3", "-I", "tools/die_plan/plan_gate_pre.py", "x.json"], ["bash", "compose3.sh"], ["python3", "compose3.py", "in.json"],
                  ["bash", "/srv/x/gate_sp.sh", "W"], ["bash", "bind_w.sh"], ["python3", "tools/die_plan/bind.py", "strict", "p.json"],
                  ["python3", "tools/die_plan/check.py", "p.json"], ["python3", "plan_census.py"]):
            self.assertTrue(m.die_like(c, "/srv/x"), c)

    def test_kits_are_not_die_level(self):
        for c in (["bash", "run_kit.sh", "slw_fw_v3", "route", "48", "8"], ["python3", "tools/die_plan/bind.py", "kit-rtl", "k"], ["openroad", "-exit", "gcompose_not.tcl"]):
            self.assertFalse(m.die_like(c, "/srv/kit-wave/x"), c)

if __name__ == "__main__":
    unittest.main()


class V16MeasuredReserve(unittest.TestCase):
    """v16 MEASURED RESERVE (coordinator 10-22): ep7 admits 176 GB for tile work, MemAvailable - 64 = 568 for a die job"""
    def test_die_job_uses_die_admit_gb(self):
        r = dict(row(176), die_admit_gb=568, total_gb=1008, floor_gb=50, ncpu=96)
        self.assertEqual(m.choose({"ot-epyc7": r}, 300, 1, die=True), ("ot-epyc7", False))
        self.assertEqual(m.choose({"ot-epyc7": r}, 300, 1, die=False), ("ot-epyc7", True))
