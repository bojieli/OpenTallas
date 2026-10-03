import hashlib
from pathlib import Path
import unittest
import qwen_rom_fulldie_b3 as B

class B3Tests(unittest.TestCase):
    def test_defaultoff_and_frozen_original(self):
        p=Path(B.F.__file__);h=hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):B.selected()
        v,m,_=B.selected(True)
        self.assertEqual(B.F.VCH,174.096);self.assertEqual(B.F.CORRIDOR_BITS,637)
        self.assertEqual(h,hashlib.sha256(p.read_bytes()).hexdigest())
    def test_width_and_area(self):
        r=B.price();self.assertEqual(r['channel']['after_aligned_um'],260.064)
        self.assertEqual(r['F2']['after'],388);self.assertLess(r['after_die']['mm2'],858)
        self.assertAlmostEqual(r['area_delta_mm2'],2.820,places=3)
    def test_split_payloads_and_endpoints(self):
        v,m,maps=B.selected(True);by={i.name:i for i in m['insts']}
        self.assertEqual(len(by),len(m['insts']))
        self.assertEqual([x['old_bus_bits'] for x in maps],[[0,1055],[1056,2111]])
        for bid,_,bits,eps in m['buses']:
            for name,port in eps:self.assertIn(name,by)
            if bid.startswith('lnkv_0_'):self.assertEqual(bits,1056)
        south=[b for b in m['buses'] if b[0].startswith('lnkv_0_') and b[3][0][0]=='hub_el']
        self.assertEqual({b[3][0][1] for b in south},{'lsw','lse'})
    def test_opposite_faces_and_no_pin_overlap(self):
        v,m,_=B.selected(True);masters=v.masters(m,1);widths=v.port_widths(m,1)
        h=masters['qfd_hub'];self.assertEqual(h.ports['lsw'][2],'W');self.assertEqual(h.ports['lse'][2],'E')
        ps=v.pin_rects(h,1,{p:widths.get((h.name,p),0) for p in h.order})
        rows={}
        for name,layer,rect in ps:
            key=(layer,rect)
            self.assertNotIn(key,rows,f'{name} overlaps {rows.get(key)}');rows[key]=name
    def test_state_scope_and_PG_not_free(self):
        r=B.price();self.assertEqual(r['PG']['rounded_per_net_coverage']['strip'],.24)
        self.assertFalse(r['PG']['actual_IR_pass']);self.assertFalse(r['qualification']['SSFF'])
        self.assertTrue(r['lower_link_widths_unchanged'])
        self.assertEqual(r['additional_link_pipeline_cycles'],72)

if __name__=='__main__':unittest.main()
