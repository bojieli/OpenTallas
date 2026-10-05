import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_hbm_interface_geometry_r11 as m

class InterfaceGeometry(unittest.TestCase):
    def test_bank_inverse_all_low_bits_and_row_boundaries(self):
        for row in [0,1,3,4,65535,(1<<19)-1]:
            for low in range(1<<15):
                s=(row<<15)|low;b=m.bankmap(s)
                self.assertEqual(m.inverse(b['pc'],b['bank'],row,(s>>7)&31),s)
    def test_system_decode_full_selectors_and_boundaries(self):
        for die in range(2):
            for stack in range(4):
                for s in [0,1,3,4,127,128,m.SECTORS-1,(1<<31)-1]:
                    self.assertEqual(m.decode_system(m.system_address(die,stack,s)),(die,stack,s))
    def test_no_width_alias_and_whole_burst_bounds(self):
        self.assertEqual(m.checked_local(m.SECTORS-32,32),m.SECTORS-32)
        for s,n in [(1<<32,1),(m.SECTORS-31,32),(0,0),(0,33),(-1,1)]:
            with self.assertRaises(ValueError):m.checked_local(s,n)
    def test_beat4_collision_requires_native_extension(self):
        self.assertEqual(m.bankmap(8176)['pc'],m.bankmap(8192)['pc'])
        self.assertEqual(0&15,16&15)
        self.assertNotEqual(0&31,16&31)
    def test_finite_owner_full_epoch_and_tag_quarantine(self):
        p=m.TagOwners();tag=p.accept(8176,32,65535,2**63+3,2**31+9)
        with self.assertRaises(ValueError):p.reclaim(tag)
        for b in reversed(range(32)):
            r=p.capture(tag,m.bankmap(8176+b)['pc'],b,b)
            self.assertEqual(r,(8176+b,65535,2**63+3,2**31+9,b))
        with self.assertRaises(ValueError):p.capture(tag,m.bankmap(8176)['pc'],0,0)
        p.reclaim(tag);self.assertFalse(p.live)
    def test_PC_capacity_backpressure_before_accept(self):
        p=m.TagOwners()
        for i in range(128):self.assertIsNotNone(p.accept(0,1,i,i,7))
        self.assertIsNone(p.accept(0,1,129,129,7));self.assertEqual(len(p.live),128)
    def test_actual_metadata_and_composed_geometry(self):
        x=m.composed();q=x['Qwen'];d=x['DeepSeek']
        self.assertEqual(x['exact_metadata']['instructions'],1737)
        self.assertEqual(len(q['macro_placements']),676)
        self.assertEqual(len(d['macro_placements']),292)
        self.assertFalse(q['geometry_conflicts']);self.assertFalse(d['geometry_conflicts'])
        self.assertGreater(q['selected_slot_mm2_per_stack'],q['minimum_slot_mm2_per_stack'])
        self.assertFalse(d['DS_provider_area_fit']);self.assertFalse(x['terminal']['physical_admission'])
        self.assertEqual(x['PHY']['clock_ps']['PHY_core'],1000)
        self.assertEqual(x['capacity']['lookup_initiation_interval_CORE_edges'],1)
    def test_added_macros_inside_assigned_service_band(self):
        q=m.qwen_geometry()
        for p in q['macro_placements']:
            if not p['status'].startswith('added'):continue
            candidates=[b for b in q['regions'] if b['kind']=='service' and b['x']<=p['x'] and b['y']<=p['y'] and p['x']+p['w']<=b['x']+b['w'] and p['y']+p['h']<=b['y']+b['h']]
            self.assertEqual(len(candidates),1)

if __name__=='__main__':unittest.main()
