import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w2_fullnc6_run as runner

class CompileAdmissionTests(unittest.TestCase):
    def test_large_host_uses32_and_small_host_uses_available(self):
        self.assertEqual(runner.choose_jobs(124.5),32)
        self.assertEqual(runner.choose_jobs(62.7),32)
        self.assertEqual(runner.choose_jobs(7.8),7)

    def test_no_idle_cpu_refuses_instead_of_launching_busy_job(self):
        with self.assertRaisesRegex(ValueError,'NO_LOCAL_CPU_HEADROOM'):
            runner.choose_jobs(0.8)

    def test_explicit_jobs_require_measured_headroom(self):
        self.assertEqual(runner.choose_jobs(40,32),32)
        with self.assertRaisesRegex(ValueError,'EXCEED_MEASURED'):
            runner.choose_jobs(16,32)

    def test_cpu_sample_honors_affinity_and_measures_tick_deltas(self):
        before={0:(100,20),1:(200,50),2:(300,60)}
        after={0:(200,120),1:(300,75),2:(400,160)}
        self.assertEqual(runner.idle_cpu_equivalents(before,after,{0,1}),1.25)

if __name__=='__main__':unittest.main()


class ConnectedEnrollmentTests(unittest.TestCase):
    def test_missing_source_factory_never_creates_output_or_launches(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as td:
            root=Path(td)
            with patch.object(runner.subprocess,'Popen') as launch:
                with self.assertRaises(ValueError):
                    runner.connected_runtime(root/'missing','not-a-factory',root/'socket',root/'out')
                launch.assert_not_called()
                self.assertFalse((root/'out').exists())

    def test_socket_eof_is_session_closure_not_token_pass(self):
        import io,json,types
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from tools.gpu_sys import canonical_qwen_ranked_simulator as sim
        from tools.gpu_sys import canonical_qwen_transport as transport
        class Pins:
            edges=0;stopped=False;edge_open=False
            book={'pins':{name:{'count':128} for name in
                ('w2_rst_n','w2_c_req_v','w2_p_req_v','w2_c_rsp_v','w2_c_wr_done_v')}}
            def __init__(self,*args):self.hooks=[]
            def add_edge_hook(self,hook):self.hooks.append(hook)
        class Server:
            def __init__(self,*args,**kwargs):self.session=types.SimpleNamespace(stopped=False,sequence=0)
            def serve_once(self):pass
            def close(self):pass
        process=types.SimpleNamespace(pid=123,stdin=io.StringIO(),stdout=io.StringIO(),wait=lambda:0)
        module=types.ModuleType('test_only_actual_factory')
        module.build=lambda pins:dict(authority=object(),native_handlers={},w2_ports={})
        def fake_build(pins):
            payload=types.SimpleNamespace(before_edge=lambda:None,after_edge=lambda:None)
            pins.hooks.append(payload)
            return dict(handlers={},payload=payload)
        with TemporaryDirectory() as td:
            root=Path(td);binary=root/'driver';binary.write_bytes(b'model-test-only')
            with patch.dict(sys.modules,{module.__name__:module}), \
                 patch.object(runner.subprocess,'check_output',side_effect=['','test-commit']), \
                 patch.object(runner.subprocess,'Popen',return_value=process), \
                 patch.object(sim,'RankedEnclosingPins',Pins), \
                 patch.object(sim,'build',side_effect=lambda pins,*args,**kw: fake_build(pins)), \
                 patch.object(transport,'UnixDeliveryServer',Server):
                record=runner.connected_runtime(binary,module.__name__+':build',root/'socket',root/'out')
            self.assertEqual(record['status'],'CONNECTED_SESSION_CLOSED_NOT_TOKEN_VERDICT')
            self.assertFalse(record['physical_or_fulltoken_admission'])
            self.assertEqual(record['backend_accepts'],0)
            self.assertEqual(record,json.loads((root/'out/record.json').read_text()))


class SoleClockHookTests(unittest.TestCase):
    def test_observer_sees_payload_drives_on_the_existing_one_hook(self):
        from types import SimpleNamespace
        events=[]
        payload=SimpleNamespace(before_edge=lambda:events.append('payload-before'),
            after_edge=lambda:events.append('payload-after'))
        observer=SimpleNamespace(before_edge=lambda:events.append('observer-before'),
            after_edge=lambda:events.append('observer-after'))
        pins=SimpleNamespace(edge_open=False,stopped=False,hooks=[payload])
        runner.observe_registered_payload(pins,payload,observer)
        self.assertEqual(len(pins.hooks),1)
        pins.hooks[0].before_edge();events.append('ONE-ACTUAL-EDGE');pins.hooks[0].after_edge()
        self.assertEqual(events,['payload-before','observer-before','ONE-ACTUAL-EDGE',
            'payload-after','observer-after'])
        with self.assertRaises(ValueError):runner.observe_registered_payload(pins,payload,observer)
