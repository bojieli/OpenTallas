"""Source wire widths and deliberately corrupted owner/credit identities."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_kv_identity_binding import *

class IdentityTests(unittest.TestCase):
    def test_all36_layers_and_four_endpoint_ranks_do_not_alias(self):
        seen=set()
        for rank in range(4):
            for layer in range(36):
                o=Owner(0,rank,layer,23)
                f=identity(o,3,589824,7,2,15);word=pack(f)
                self.assertNotIn(word,seen);seen.add(word)
                self.assertEqual(validate(word,rank>>1,o),f)
                self.assertLess(word,2**192)
    def test_literal_reverse_wire_and_retained_fields(self):
        o=Owner(5,3,35,23);f=identity(o,2,12345,7,3,15);word=pack(f)
        packet=reverse_credit(word,4095,31,1)
        self.assertLess(packet,2**404)
        self.assertEqual((packet>>18)&((1<<192)-1),word)
        self.assertEqual((packet>>6)&4095,4095)
        self.assertEqual((packet>>1)&31,31)
        self.assertEqual((packet>>210)&1,1)
        self.assertEqual(packet>>211,0)
    def test_bad_endpoint_owner_and_stale_generation_rejected(self):
        o=Owner(5,3,35,23);f=identity(o,2,12345,7,2,15);word=pack(f)
        with self.assertRaises(ValueError):validate(word,0,o)
        with self.assertRaises(ValueError):validate(word,1,Owner(5,3,35,24))
        for name in ('die','producer','caller','irs_serial'):
            bad=dict(f);bad[name]^=1
            with self.assertRaises(ValueError):validate(pack(bad),1,o)
    def test_actual_layer_local_pc_survives_provider_fields(self):
        o=Owner(5,3,35,23)
        for pc in (0,255,256,4095):
            word=pack(identity(o,2,12345,7,1,15,pc=pc))
            self.assertEqual(validate(word,1,o,expected_pc=pc)['caller']&255,227)
            with self.assertRaises(ValueError):validate(word,1,o,expected_pc=(pc+1)%4096)
    def test_source_widths_are_literal(self):
        root=Path(__file__).resolve().parents[1]
        pkg=(root/'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv').read_text()
        self.assertIn('identity_t; //192',pkg)
        bench=(root/'rtl/test/model_ready_hbm_r14/tb_hbm_finite_stage.sv').read_text()
        self.assertIn("193'b0,reverse_we,reverse_selected.id,reverse_selected.physical_tag,reverse_selected.beat,1'b0",bench)
        self.assertEqual(sum(bits for name,bits in FIELDS),192)
if __name__=='__main__':unittest.main()
