import gzip,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_noECC_liberty as m

class ExactArchive(unittest.TestCase):
    def tearDown(self):
        m.library_text.cache_clear();m.cell_bodies.cache_clear()
    def test_actual_r4_families_complete_and_distinct(self):
        for corner in ('ss','ff'):
            cells=m.cell_bodies(corner)
            for cell in ('NOR2xp33_ASAP7_75t_R','NAND2xp33_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R','BUFx4_ASAP7_75t_R'):
                self.assertIn(cell,cells)
        self.assertNotEqual(m.cell_bodies('ss')['NOR2xp33_ASAP7_75t_R'],m.cell_bodies('ff')['NOR2xp33_ASAP7_75t_R'])
    def test_archive_corruption_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'terminal_r4').mkdir()
            raw=gzip.compress(b'time_unit : "1ps"; capacitive_load_unit (1, ff);',mtime=0)
            path=root/'terminal_r4/ao_ss.lib.gz';path.write_bytes(raw+b'changed')
            (root/'terminal_hashes.json').write_text(json.dumps({'terminal_r4/ao_ss.lib.gz':hashlib.sha256(raw).hexdigest()}))
            m.library_text.cache_clear()
            with patch.object(m,'BASE',root),self.assertRaisesRegex(ValueError,'changed'):
                m.library_text('ao_ss.lib')
    def test_non_signoff_corner_rejected(self):
        with self.assertRaisesRegex(ValueError,'SS/FF only'):m.cell_bodies('tt')
if __name__=='__main__':unittest.main()
