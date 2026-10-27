import tempfile
import unittest
from pathlib import Path
from native_boot_sources import NAMES, refresh

class NativeBootSources(unittest.TestCase):
    def fixture(self, p):
        tree = p / 'tree'; src = tree / 'rtl/qwen_sys/static_kv_20261014'; src.mkdir(parents=True)
        vehicle = p / 'vehicle'
        for n in NAMES: (src / n).write_text('qualified boot_win ' + n)
        for d in ('direct', 'library'):
            v = vehicle / 'src' / d; v.mkdir(parents=True)
            for n in NAMES[:4]: (v / n).write_text('old')
        return tree, vehicle

    def test_all_selected_copies_refreshed(self):
        with tempfile.TemporaryDirectory() as td:
            tree, vehicle = self.fixture(Path(td))
            records = refresh(vehicle, tree)
            self.assertEqual(len(records), 8)
            for row in records: self.assertIn('boot_win', (vehicle / row['file']).read_text())
            self.assertFalse(list((vehicle / 'src').rglob(NAMES[4])))

    def test_missing_source_fails_before_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            tree, vehicle = self.fixture(Path(td))
            for f in (vehicle / 'src').rglob(NAMES[1]): f.unlink()
            with self.assertRaises(ValueError): refresh(vehicle, tree)
            for f in (vehicle / 'src').rglob(NAMES[0]): self.assertEqual(f.read_text(), 'old')

if __name__ == '__main__': unittest.main()
