import tempfile
import unittest
from pathlib import Path
from hier_source_overlay import overlay

class Overlay(unittest.TestCase):
    def test_top_and_hierarchy_share_source(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); (p / 'fix').mkdir()
            src = p / 'fix' / 'pc.sv'; src.write_text('module pc; endmodule\n')
            top = p / 'Vtop__hierMkArgs.f'; lib = p / 'Vpc__hierMkArgs.f'
            for a in (top, lib): a.write_text('/old/pc.sv\n--top-module top\n')
            changes = overlay([top, lib], [src])
            self.assertEqual(len(changes), 2)
            for a in (top, lib): self.assertEqual(a.read_text(), str(src) + '\n--top-module top\n')
            self.assertEqual(overlay([top, lib], [src]), [])

    def test_rejects_shared_argument_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); src = p / 'pc.sv'; src.write_text('new')
            old = p / 'original.f'; old.write_text('/old/pc.sv\n')
            link = p / 'link.f'; link.symlink_to(old)
            with self.assertRaises(ValueError): overlay([link], [src])
            self.assertEqual(old.read_text(), '/old/pc.sv\n')

if __name__ == '__main__': unittest.main()
