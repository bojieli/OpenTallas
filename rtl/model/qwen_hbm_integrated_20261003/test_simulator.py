"""Enclosing pin protocol/source-binding tests, not a numerical RTL verdict."""
import io
import json
from pathlib import Path
import subprocess
import unittest

from tools.gpu_sys.canonical_qwen_simulator import EnclosingPins, TransportError, PORTBOOK


class PinTests(unittest.TestCase):
    def pins(self, responses=''):
        writer = io.StringIO()
        pins = EnclosingPins(io.StringIO('ot_gpu_qwen_hbm_integrated ENABLE=1 SM=64 W2=128\n'+responses), writer)
        return pins, writer

    def test_refuses_other_binary(self):
        for line in ('wrong\n', 'ot_gpu_qwen_hbm_integrated ENABLE=0 SM=64 W2=128\n', ''):
            with self.assertRaises(TransportError):
                EnclosingPins(io.StringIO(line), io.StringIO())

    def test_width_output_clock_refusal(self):
        p, w = self.pins()
        for name, value in [('stream_clk', 1), ('kv_fault', 0), ('kv_cmd_op', 8), ('kv_cmd_op', -1), ('kv_cmd_op', True)]:
            with self.assertRaises(TransportError): p.set(name, value)
        self.assertEqual(w.getvalue(), 'HELLO\n')

    def test_instance_slice(self):
        p, w = self.pins((format(5 << (192*33), 'x')+'\n')*2+'OK\n')
        p.component('w2', 33).set_client(0, 'c_req_tag', 7)
        # one W2 contains 6 original customer tags; do not truncate tag32.
        self.assertIn('GET w2_c_req_tag', w.getvalue())
        value = int(w.getvalue().splitlines()[-1].split()[-1], 16)
        self.assertEqual((value >> (33*192)) & 0xffffffff, 7)

    def test_tick_brackets_all_edges(self):
        p, w = self.pins('OK\nOK\nOK\n')
        events = []
        class Hook:
            def before_edge(self): events.append(('before', p.edges))
            def after_edge(self): events.append(('after', p.edges))
        p.add_edge_hook(Hook());p.tick()
        self.assertEqual(events, [('before',0),('after',1)])
        self.assertEqual(w.getvalue(), 'HELLO\nEVAL\nEDGE\nEVAL\n')
        with self.assertRaises(TransportError):p.add_edge_hook(Hook())

    def test_hook_failure_no_edge(self):
        p, w = self.pins()
        class Hook:
            def before_edge(self):raise RuntimeError('grant failed')
            def after_edge(self):raise AssertionError('must not run')
        p.add_edge_hook(Hook())
        with self.assertRaisesRegex(RuntimeError,'grant failed'):p.tick()
        self.assertTrue(p.stopped)
        with self.assertRaises(TransportError):p.tick()
        self.assertNotIn('EDGE',w.getvalue())

    def test_recursive_clock_refused(self):
        p, w = self.pins()
        class Hook:
            def before_edge(self):p.tick()
            def after_edge(self):pass
        p.add_edge_hook(Hook())
        with self.assertRaises(TransportError):p.tick()
        self.assertTrue(p.stopped)

    def test_exact_generation_and_sourcepins(self):
        root=PORTBOOK.parents[3]
        packet=PORTBOOK.parent
        paths=['ot_gpu_qwen_joined_kv.sv','ot_gpu_qwen_hbm_integrated.sv','sources.f','ports.json','pin_driver.cpp']
        old={n:(packet/n).read_bytes() for n in paths}
        subprocess.run(['python3',str(packet/'generate.py')],check=True)
        self.assertEqual(old,{n:(packet/n).read_bytes() for n in paths})
        import hashlib
        for source,want in json.loads(PORTBOOK.read_text())['source_sha256'].items():
            self.assertEqual(hashlib.sha256((root/source).read_bytes()).hexdigest(),want,source)



    def test_existing_engine_dependency_closure(self):
        import re
        root=PORTBOOK.parents[3]
        sources=(PORTBOOK.parent/'sources.f').read_text().splitlines()
        text='\n'.join((root/p).read_text() for p in sources)
        declarations=set(re.findall(r'\bmodule\s+(ot_\w+)',text))
        uses=set(re.findall(r'^\s*(ot_\w+)\s+(?:#\s*\(|\w+\s*\()',text,re.M))
        # These undefined names intentionally reject invalid LAT/CUTS at
        # elaboration. They are guarded parameter traps, not missing engines.
        traps={f'ot_hdc_fp32_{op}_lat_CUTS_must_match_LAT' for op in ('add','mul')}
        for trap in traps:
            self.assertRegex(text, r'generate if \(CUTS >= 0 &&[^\n]+ != LAT\) begin : g_bad_cuts\s+'
                             +re.escape(trap)+r' u_trap \(\);\s+end endgenerate')
        self.assertEqual(uses-declarations-traps,set())
        self.assertIn('ot_w2_nc6_correction_control',uses)
        self.assertIn('ot_gpu_qwen_native_consumer_drain',uses)

    def test_single_controller_actual_source_join(self):
        packet=PORTBOOK.parent
        joined=(packet/'ot_gpu_qwen_joined_kv.sv').read_text()
        self.assertEqual(joined.count('ot_gpu_qwen_kv_lifecycle_controller #'),1)
        self.assertEqual(joined.count('ot_gpu_qwen_native_consumer_drain #'),1)
        self.assertNotIn('ot_gpu_qwen_kv_reader_services #',joined)
        self.assertNotIn('ot_gpu_qwen_kv_native_lifecycle #',joined)
        self.assertIn('.consumer_identity(c_consumer_identity)',joined)
        self.assertIn('.drain_done_allcopies(c_drain_done_allcopies)',joined)
        self.assertIn('.native_complete_tuple(native_complete_tuple)',joined)
        s=(packet/'ot_gpu_qwen_hbm_integrated.sv').read_text()
        self.assertIn('.service_wdata(sm_scratch_wdata)',s)
        self.assertIn('.scratch_wdata(sm_scratch_wdata[i*512 +: 512])',s)
        self.assertIn('input wire [671:0] kv_cohort_rsp_tuple',s)
        sources=(packet/'sources.f').read_text().splitlines()
        self.assertEqual(sources[0],'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv')

    def test_no_hook_enrollment_with_boot_debt(self):
        p,w=self.pins('1\n1\n')
        p.edges=3
        class Hook:
            def before_edge(self):pass
            def after_edge(self):pass
        with self.assertRaisesRegex(TransportError,'local debt'):p.add_edge_hook(Hook())
        self.assertEqual(p.hooks,[])

    def test_actual_w2_guarded_source_connections(self):
        s=(PORTBOOK.parent/'ot_gpu_qwen_hbm_integrated.sv').read_text()
        self.assertIn('.c_req_v(guarded_c_req_v[i*6 +: 6])',s)
        self.assertIn('.c_rsp_rdy(guarded_c_rsp_rdy[i*6 +: 6])',s)
        self.assertIn('.c_wr_done_rdy(guarded_c_wr_done_rdy[i*6 +: 6])',s)
        self.assertIn('.bus_PC(selected_PC)',s)
        self.assertIn('sector_grant_identity[45:39]',s)
        self.assertNotRegex(s,r'\.(provider_fenced|reverse_fenced|reset_fenced|drain_done_allcopies)\(\s*(?:1|8)\'')
        self.assertIn('i<64',s);self.assertIn('i<128',s)

if __name__=='__main__':unittest.main()
