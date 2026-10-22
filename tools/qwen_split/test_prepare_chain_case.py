import tempfile
import unittest
from pathlib import Path
from prepare_chain_case import prepare


class PrepareCaseTest(unittest.TestCase):
    def test_fresh_input_is_kept(self):
        with tempfile.TemporaryDirectory() as t:
            c = Path(t) / 'case'
            c.mkdir()
            (c / 'die.v').write_text('original')
            self.assertIsNone(prepare(c))
            self.assertEqual((c / 'die.v').read_text(), 'original')

    def test_interrupted_transform_is_preserved_not_reapplied(self):
        with tempfile.TemporaryDirectory() as t:
            c = Path(t) / 'case'
            c.mkdir()
            (c / 'assumed_phy_pg_access.json').write_text('receipt')
            (c / 'die.v').write_text('original')
            archive = prepare(c)
            self.assertTrue(c.is_dir())
            self.assertEqual(list(c.iterdir()), [])
            self.assertEqual((archive / 'assumed_phy_pg_access.json').read_text(), 'receipt')
            self.assertEqual((archive / 'die.v').read_text(), 'original')

    def test_physical_checkpoint_cannot_be_archived(self):
        with tempfile.TemporaryDirectory() as t:
            c = Path(t) / 'case'
            c.mkdir()
            (c / 'assumed_phy_pg_access.json').write_text('receipt')
            (c / '1_place.odb').write_text('checkpoint')
            with self.assertRaisesRegex(ValueError, 'resume die_chain'):
                prepare(c)
            self.assertEqual((c / '1_place.odb').read_text(), 'checkpoint')
            self.assertTrue((c / 'assumed_phy_pg_access.json').exists())


if __name__ == '__main__':
    unittest.main()
