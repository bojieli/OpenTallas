"""Source packing, literal mutable-state inventory and selected context guards."""
import hashlib
import re
from pathlib import Path
import tempfile
import unittest
import qwen_rom_fulldie_instruction_r1 as P
from uarch_model_qwen_instruction_transport_r1 import price

class InstructionTests(unittest.TestCase):
    def test_default_off(self):
        with self.assertRaisesRegex(ValueError,'default off'):P.selected_model()

    def test_private_variant_preserves_original_and_link_hotspot(self):
        p=Path(P.original.__file__);sha=hashlib.sha256(p.read_bytes()).hexdigest()
        m0=P.original.build(tree_mode='banded')
        v,m=P.selected_model(True)
        self.assertEqual(P.original.CORRIDOR_BITS,637)
        self.assertEqual(v.CORRIDOR_BITS,451)
        self.assertAlmostEqual(v.REGION_PG['hub'],.48/18)
        self.assertEqual(v.REGION_PG['strip'],.24)
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),sha)
        self.assertEqual(m['die'],m0['die'])
        for c in ['link_spine','link_channel','tree_spine']:
            self.assertEqual([b for b in m['buses'] if b[1]==c],[b for b in m0['buses'] if b[1]==c])

    def test_literal_source_packing_and_state_matches_model(self):
        source=(P.ROOT/'rtl/hdc/ot_qwen_me_array_w12.sv').read_text()
        self.assertIn('3 * NW + 13 * AW + 13',source)
        ordered=re.search(r'wire \[IBW-1:0\] ib = \{(.*?)\};',source,re.S)[1]
        self.assertEqual(re.findall(r'i_\w+',ordered),['i_nout','i_tiles','i_k','i_wsrc','i_wbase','i_ts','i_ks','i_js',
          'i_xbase','i_xks','i_xjs','i_xcs','i_jsh','i_split','i_wcs','i_round','i_obase','i_ots','i_ojs',
          'i_mmode','i_oen','i_amax','i_rmax','i_mbase'])
        s=(P.ROOT/'rtl/qwen_sys/ot_qwen_w12_instruction_transport_r1.sv').read_text()
        self.assertIn('reg [215:0] q0,q1;',s);self.assertIn('reg [431:0] assembly;',s);self.assertIn('reg [71:0] control;',s)
        self.assertEqual(price()['state']['protected_bits_per_station'],2*216+432+72)

    def test_no_retire_or_drain_inference_from_ready(self):
        s=(P.ROOT/'rtl/qwen_sys/ot_qwen_w12_instruction_transport_r1.sv').read_text()
        self.assertIn('warm && phase==0 && all_copy_drained && !fault',s)
        self.assertIn('consumer_retire && phase==3 && issued',s)
        self.assertNotIn('if(warm_request) control',s)
        r=price();self.assertEqual(r['boundary']['link_spine_hotspot_relief_credited'],0)
        self.assertTrue(r['physical']['full_die_IR_required'])

    def test_actual_tile_wrapper_parameter_and_port_passthrough(self):
        s=(P.ROOT/'rtl/hdc/ot_qwen_rom_tile_w12.sv').read_text()
        head=s[s.index('module ot_qwen_rom_tile_logic_w12'):s.index('    localparam integer IBW')]
        head=re.sub(r'//[^\n]*','',head)
        ps=re.findall(r'parameter integer\s+(\w+)',head)
        ports=re.findall(r'(?:input|output)\s+wire\s*(?:\[[^]]+\]\s*)?(\w+)',head)
        wrapper=(P.ROOT/'rtl/qwen_sys/ot_qwen_w12_instruction_tile_adapter_r1.sv').read_text()
        call=wrapper[wrapper.index('ot_qwen_rom_tile_logic_w12 #('):]
        for p in ps:self.assertIn(f'.{p}({p})',call)
        for p in ports:
            value={'ib_go':'launch_go','ib':'packed_ib','fault':'tile_fault'}.get(p,p)
            self.assertIn(f'.{p}({value})',call)
        self.assertIn('NW!=18 || AW!=24',wrapper)

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'old_failure').write_text('preserve')
            with self.assertRaisesRegex(ValueError,'existing evidence'):P.prepare(p,True)
            self.assertEqual((p/'old_failure').read_text(),'preserve')

    def test_preparation_full_power_source_projection(self):
        # Exercise the real preparation API, with heavy file emitters mocked;
        # powered_lef's actual tuple contract must still be accepted.
        from unittest.mock import patch
        m=P.original.build(tree_mode='banded');v,_=P.selected_model(True)
        def emit(model,work,*args,**kw):
            work.mkdir();(work/'old').write_text('fixture')
        with tempfile.TemporaryDirectory() as d,patch.object(P,'selected_model',return_value=(v,m)),\
          patch.object(v,'case_grt',side_effect=emit),patch.object(v,'case_real',side_effect=emit),\
          patch.object(P.PG,'powered_lef',return_value=('PIN VDD\nPIN VSS\n',0)),\
          patch.object(P.PG,'write_pdn',return_value=[]):
            r=P.prepare(Path(d)/'new',True)
            self.assertFalse(r['run_admitted']);self.assertFalse(r['system_caller_installed'])
            self.assertIn('pdngen',(Path(d)/'new/real_pg/run_pg.tcl').read_text())

if __name__=='__main__':unittest.main()
