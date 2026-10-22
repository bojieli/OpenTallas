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

if __name__ == "__main__":
    unittest.main()
