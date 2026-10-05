import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import h4_hbm_pc10_r41_lineage as m

class LineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.expanded, cls.native = m.regenerate()

    def provider(self):
        return SimpleNamespace(homes=self.expanded, native=self.native, generation=1, locations={})

    def test_original_exact_still_admitted(self):
        p = SimpleNamespace(homes=self.original, generation=1, locations={})
        self.assertEqual(m.ProductionPC10(p).lineage, 'original_exact')

    def test_actual_full_r41_regeneration_admitted(self):
        p = self.provider(); a = m.ProductionPC10(p)
        self.assertEqual(len(p.homes), 290730)
        self.assertEqual(len(self.original), 286114)
        self.assertEqual(a.lineage, 'R41_full_source_regeneration')
        for rank in (0, 31, 64, 95):
            self.assertEqual(a.identity(rank)['home_indices'],
                [i for i in a.plan['source_writes'][0]['home_indices'] if rank in self.original[i]['rank_group']])
        with self.assertRaisesRegex(ValueError, 'PC9 production'): a.ready(0)

    def test_arbitrary_append_refused(self):
        p = self.provider(); p.homes = self.expanded + [self.expanded[-1]]
        with self.assertRaisesRegex(ValueError, 'R41 homes'): m.ProductionPC10(p)

    def test_missing_extension_refused(self):
        p = self.provider(); p.homes = self.expanded[:-1]
        with self.assertRaisesRegex(ValueError, 'R41 homes'): m.ProductionPC10(p)

    def test_extension_mutation_refused(self):
        p = self.provider(); p.homes = list(self.expanded)
        p.homes[-1] = copy.deepcopy(p.homes[-1]); p.homes[-1]['word_count'] += 1
        with self.assertRaisesRegex(ValueError, 'R41 homes'): m.ProductionPC10(p)

    def test_prefix_mutation_refused(self):
        p = self.provider(); p.homes = list(self.expanded)
        p.homes[0] = dict(p.homes[0], version='forged')
        with self.assertRaisesRegex(ValueError, 'prefix changed'): m.ProductionPC10(p)

    def test_source_native_required(self):
        p = self.provider(); del p.native
        with self.assertRaisesRegex(ValueError, 'R41 native'): m.ProductionPC10(p)

    def test_pc10_native_reference_mutation_refused(self):
        p = self.provider(); p.native = dict(self.native, instructions=list(self.native['instructions']))
        op = copy.deepcopy(p.native['instructions'][10]); op['writes'][0]['home_indices'][0] += 1
        p.native['instructions'][10] = op
        with self.assertRaisesRegex(ValueError, 'R41 native'): m.ProductionPC10(p)

    def test_source_archive_corruption_refused(self):
        import tempfile
        old = m.BASE
        with tempfile.TemporaryDirectory() as t:
            import shutil
            shutil.copytree(old, Path(t) / 'archive'); m.BASE = Path(t) / 'archive'
            try:
                p = m.BASE / 'inputs/r41.py'; p.write_bytes(p.read_bytes() + b'\n')
                with self.assertRaisesRegex(ValueError, 'source pin'): m.regenerate()
            finally: m.BASE = old

if __name__ == '__main__': unittest.main()
