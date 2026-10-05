import importlib.util
import re
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('provider',ROOT/'tools/dsrom_field_static_provider.py')
P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
INPUT=ROOT/'results/rtl/dsrom_recovery_20261004/immutable_stage_controls'

class StaticProvider(unittest.TestCase):
    def test_full_address_truth_tables_and_replay(self):
        for stage in (37,38):
            with self.subTest(stage=stage):
                b,ph,st=P.load(INPUT/f'stage{stage}')
                rtl=ROOT/f'rtl/v41die/static_controls/ot_v41_stage{stage}_control_rom.sv'
                text=rtl.read_text()
                pc={int(a):int(w,16) for a,w in re.findall(r"10'd(\d+):phase_pair=128'h([0-9a-f]+)",text)}
                sc={int(a):int(w,16) for a,w in re.findall(r"14'd(\d+):stream_word=48'h([0-9a-f]+)",text)}
                self.assertEqual(len(pc),b['phase_count'])
                for a in range(1024):self.assertEqual(pc.get(a,0),ph[2*a]|(ph[2*a+1]<<64))
                for a in range(16384):self.assertEqual(sc.get(a,0),st[a])
                with tempfile.TemporaryDirectory() as d:
                    out=Path(d)/'replay.sv';P.emit_module(INPUT/f'stage{stage}',out)
                    self.assertEqual(out.read_bytes(),rtl.read_bytes())
    def test_proposed_budget_not_physical_credit(self):
        for stage in (37,38):
            m=P.model(INPUT/f'stage{stage}')
            self.assertTrue(m['component_functional_build_admitted'])
            self.assertFalse(m['physical_admitted'])
            self.assertFalse(m['routing_admitted'])
            self.assertEqual(m['provider_state_bits'],0)
            self.assertEqual(m['memory_write_ports'],0)
            self.assertEqual(m['phase_read_bits_per_cycle'],128)
            self.assertEqual(m['stream_read_bits_per_cycle'],48)
            self.assertGreater(m['remaining_cell_budget_um2'],0)
    def test_no_new_engine_delta_outside_provider(self):
        original=(ROOT/'rtl/v41die/ot_v41_spine_pq_addr_w17w10.sv').read_text()
        joined=(ROOT/'rtl/v41die/ot_v41_spine_pq_static_w17w10.sv').read_text()
        self.assertEqual(original[original.index('    // issue condition'):],joined[joined.index('    // issue condition'):])
        self.assertIn('parameter integer STATIC_CONTROLS = 0',joined)
        self.assertIn('initial if (STATIC_CONTROLS == 0)',joined)
    def test_optin_runtime_path_has_no_array_writes(self):
        text=(ROOT/'tools/runtime/dsrom/s81_minimum_qe_static.cpp').read_text()
        block=text[text.index('#ifdef DSROM_S81_STATIC_CONTROL_STAGE',text.index(' bool inputs(')):]
        block=block.split('#else',1)[0]
        self.assertIn('dsrom_s81_static_controls::validate',block)
        self.assertNotIn('rootp',block)
        self.assertIn('returned.stage==DSROM_S81_STATIC_CONTROL_STAGE',block)
    def test_current_baseline_cut_hook_preserves_control(self):
        original=(ROOT/'rtl/v41die/ot_v41_spine_w17w10.sv').read_text()
        new=(ROOT/'rtl/v41die/ot_v41_spine_static_w17w10.sv').read_text()
        original=original[original.index('    // ------------------------------------------------------------------ control'):]
        new=new[new.index('    // ------------------------------------------------------------------ control'):]
        new=new.replace('pw <= control_pq0; rsplit <= control_pq1[15:0];',"pw <= phrom[{i_ph, 1'b0}]; rsplit <= phrom[{i_ph, 1'b1}][15:0];",1)
        new=new.replace('sw <= control_sq;',"sw <= strom[SAW'(sbase) + SAW'(sm_i)];",1)
        new=new.replace('sw <= control_sq;',"sw <= strom[SAW'(sbase) + SAW'(s_last ? 16'd0 : sm_i + 16'd1)];",1)
        self.assertEqual(original,new)
        top=(ROOT/'rtl/v41die/ot_v41_fieldtop_static_w17w10.sv').read_text()
        self.assertIn('`ifdef RT_CUT',top)
        self.assertIn('.STATIC_CONTROLS(STATIC_CONTROLS)',top)

    def test_context_parser_correction_is_whitespace_only(self):
        fixed=(ROOT/'physical/dsrom_static_provider_context/ot_v41_static_provider_context.sv').read_text()
        failed=(ROOT/'results/rtl/dsrom_field_address_lookahead_20261005/static_context_attempt_r1/failed_context.sv').read_text()
        self.assertRegex(failed,r"\d+'d\d+\?")
        self.assertNotRegex(fixed,r"\d+'d\d+\?")
        self.assertEqual(re.sub(r'\s+','',failed),re.sub(r'\s+','',fixed))

    def test_source_image_tamper_refuses(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(INPUT/'stage37',Path(d)/'stage37')
            p=Path(d)/'stage37/spine_stream.hex';p.write_text('0\n'+p.read_text())
            with self.assertRaisesRegex(ValueError,'image pin'):P.load(p.parent)

if __name__=='__main__':unittest.main()
