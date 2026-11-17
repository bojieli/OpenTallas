"""Component composition retains replay evidence and refuses misaligned BF inputs."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
import bf_component_composition as C

class CompositionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        sources = {}
        for name in C.KERNELS:
            p = self.root/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(name)
            sources[name] = C.digest(p)
        self.base = dict(ok=True,key='col_h9_asb_x|E2|bseg1024',
            fits={'13':dict(go_edge=10,first_issue_edge=15,last_issue_edge=78,
                            descriptor=dict(off=4))},desc={'13':17},
            pv={'e13w.r':[184],'e13e.r':[184]},pv_all={},lat_issue_to_pv={},leaf_ret_corr={},
            asbuilt_source_qualification=dict(status='PASS_STATIC_REPLAY',clock_ps=833,
                native_family_hold=True,payload_control_caught=True,one_edge_control_caught=True,
                source_sha256=sources))
        before={p:[['cf.'+p,10]] for p in C.INPUTS}
        after={p:[[label,edge+3] for label,edge in vals] for p,vals in before.items()}
        self.inputs=dict(old={'u_r2.u_e13':before},current={'u_r2.u_e13':after})
        self.replay=self.root/'replay.json'
        self.replay.write_text(json.dumps({self.base['key']:self.base}))
        self.schedule=self.root/'schedule.json'
        self.schedule.write_text(json.dumps(dict(bound_plan=dict(frame_instance='u_f_0L02',seam_extra_stages={'u_s12':7}))))
        self.trace=self.root/'inputs.json'
        self.trace.write_text(json.dumps([dict(class_='test',inputs=self.inputs,current_seam_extra={'u_s12':7})]))
        self.record,_=C.translate(self.base,self.inputs)
        self.record['asbuilt_source_qualification']=dict(status='COMPONENT_COMPOSITION',
            source_sha256=sources,schedule_sha256=C.digest(self.schedule),component_composition=dict(
                frame='u_f_0L02',replay_file='replay.json',replay_file_sha256=C.digest(self.replay),
                inputs=self.inputs,input_shifts={'13':3},input_trace_file='inputs.json',input_trace_file_sha256=C.digest(self.trace),source_trace_class='test'))

    def qualify(self,rec=None,frame='u_f_0L02'):
        return C.qualify(rec or self.record,self.root,self.root,self.schedule,frame)

    def test_uniform_shift_preserves_original_replay(self):
        self.assertEqual(self.qualify(),'component_composition_bf_idle_q')
        self.assertEqual(self.record['pv']['e13w.r'],[187])
        self.assertEqual(self.base['pv']['e13w.r'],[184])
        self.assertEqual(self.record['fits']['13']['descriptor'],self.base['fits']['13']['descriptor'])

    def test_x_one_edge_skew_caught(self):
        self.inputs['current']['u_r2.u_e13']['x1'][0][1]+=1
        with self.assertRaisesRegex(ValueError,'one translation'):C.translate(self.base,self.inputs)

    def test_producer_identity_change_caught(self):
        self.inputs['current']['u_r2.u_e13']['x1'][0][0]='other.x'
        with self.assertRaisesRegex(ValueError,'producer changed'):C.translate(self.base,self.inputs)

    def test_guessed_output_shift_caught(self):
        rec=copy.deepcopy(self.record);rec['pv']['e13w.r'][0]+=1
        with self.assertRaisesRegex(ValueError,'prediction'):self.qualify(rec)

    def test_self_consistent_but_untraced_shift_caught(self):
        rec=copy.deepcopy(self.record)
        for vals in rec['asbuilt_source_qualification']['component_composition']['inputs']['current']['u_r2.u_e13'].values():
            vals[0][1]+=1
        with self.assertRaisesRegex(ValueError,'source trace'):self.qualify(rec)

    def test_wrong_frame_caught(self):
        with self.assertRaisesRegex(ValueError,'another frame'):self.qualify(frame='u_f_0R02')

    def test_kernel_change_caught(self):
        (self.root/C.KERNELS[0]).write_text('changed arithmetic')
        with self.assertRaisesRegex(ValueError,'kernel changed'):self.qualify()

    def test_extra_front_has_no_invented_partial(self):
        other = copy.deepcopy(self.inputs)
        other['old']['u_r0.u_e1'] = copy.deepcopy(other['old']['u_r2.u_e13'])
        other['current']['u_r0.u_e1'] = copy.deepcopy(other['current']['u_r2.u_e13'])
        rec, shifts = C.translate(self.base, other)
        self.assertEqual(shifts, {'13': 3})
        self.assertNotIn('e1w.r', rec['pv'])

    def test_actual_instance_lookup_precedes_shape(self):
        path = Path(__file__).with_name('xs_bf.py')
        node = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'meas_for')
        scope = dict(shape_key=lambda *a:'shape',
                     qualify_asbuilt_measurement=lambda rec,*a:rec['marker'])
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),scope)
        records = {'shape':dict(marker='old'),
                   'u_f_0L02::shape':dict(marker='current_L',asbuilt_source_qualification={}),
                   'u_f_0R02::shape':dict(marker='current_R',asbuilt_source_qualification={})}
        for frame, expected in [('u_f_0L02','current_L'),('u_f_0R02','current_R')]:
            rec, how = scope['meas_for'](records,'col_h9',2,'asb_x',frame_instance=frame)
            self.assertEqual((rec['marker'],how),(expected,expected))

    def test_replay_change_caught(self):
        self.replay.write_text('{}')
        with self.assertRaisesRegex(ValueError,'replay changed'):self.qualify()

if __name__=='__main__':unittest.main()
