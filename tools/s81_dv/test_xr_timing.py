import tempfile
import unittest
from pathlib import Path
from xr_timing import QUALIFIED, XR_PATH, XRT_PATH, XRT_MODEL, inject_cycles, check_run_source

class TimingTest(unittest.TestCase):
    def contract(self): return dict(xr_source_sha256=next(iter(QUALIFIED)), v_ctl_inject=7)
    def test_archived_program_retains_six(self): self.assertEqual(inject_cycles({}),6)
    def test_qualified_xr2_has_seven(self): self.assertEqual(inject_cycles({"timing_contract":self.contract()}),7)
    def test_wrong_latency_refused(self):
        c=self.contract();c["v_ctl_inject"]=6
        with self.assertRaises(ValueError): inject_cycles({"timing_contract":c})
    def test_simulator_source_must_match(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sources.sha256";c=self.contract()
            p.write_text(c["xr_source_sha256"]+"  src/"+XR_PATH+"\n");check_run_source(c,d)
            p.write_text("0"*64+"  src/"+XR_PATH+"\n")
            with self.assertRaises(ValueError): check_run_source(c,d)
    def test_matching_source_cannot_admit_wrong_latency_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.contract();c['v_ctl_inject']=6
            (Path(d)/'sources.sha256').write_text(c['xr_source_sha256']+'  src/'+XR_PATH+'\n')
            with self.assertRaises(ValueError): check_run_source(c,d)
    def test_old_xr_pin_cannot_qualify_xrt_kit(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.contract()
            (Path(d)/'sources.sha256').write_text(c['xr_source_sha256']+'  src/'+XR_PATH+'\n'+
                next(iter(XRT_MODEL))+'  src/'+XRT_PATH+'\n')
            with self.assertRaisesRegex(ValueError, 'selected-wrapper contract required'):
                check_run_source(c,d)
    def test_selected_xrt_requires_its_source_and_actual_runtime_proof(self):
        sha=next(iter(XRT_MODEL))
        c=dict(schema='opentallas.s81.selected_transport_timing.v2',v_ctl_inject=7,
               selected_transports={'u_s_0N':dict(master='ot_s81sl_xrt1',family='XRT',
                   source_path=XRT_PATH,source_sha256=sha)},transport_sources={XRT_PATH:sha})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'sources.sha256'
            p.write_text(self.contract()['xr_source_sha256']+'  src/'+XR_PATH+'\n')
            with self.assertRaisesRegex(ValueError,'does not match simulator source'):
                check_run_source(c,d)
            p.write_text(sha+'  src/'+XRT_PATH+'\n')
            with self.assertRaisesRegex(ValueError,'runtime proof remains PENDING'):
                check_run_source(c,d)
            # the native entry replay on the HOST/control cut is the proof (its own verdict carries it)
            self.assertEqual(check_run_source(c,d,'self-entry'),'self-entry')
            # a cited proof must be a PASS_CUT_COMPONENT entry replay over the same transport source
            import json
            e=Path(d)/'entry_replay.json'
            e.write_text(json.dumps(dict(schema='opentallas.s81_tokfunc.entry_replay.v1',verdict='FAIL',
                                         xrt_transport_sources={XRT_PATH:sha})))
            with self.assertRaisesRegex(ValueError,'not a PASS_CUT_COMPONENT'):
                check_run_source(c,d,str(e))
            e.write_text(json.dumps(dict(schema='opentallas.s81_tokfunc.entry_replay.v1',verdict='PASS_CUT_COMPONENT',
                                         xrt_transport_sources={XRT_PATH:'0'*64})))
            with self.assertRaisesRegex(ValueError,'covers other transport source'):
                check_run_source(c,d,str(e))
            e.write_text(json.dumps(dict(schema='opentallas.s81_tokfunc.entry_replay.v1',verdict='PASS_CUT_COMPONENT',
                                         xrt_transport_sources={XRT_PATH:sha})))
            self.assertTrue(check_run_source(c,d,str(e)).startswith('ENTRY '))

if __name__ == "__main__": unittest.main()
