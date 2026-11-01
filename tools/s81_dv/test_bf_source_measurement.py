import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from layer_prog import xs_bf as B
import lower_xs


class CandidateMeasurement(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        names=['rtl/v41rom/ot_v41_bf_front_core_roots.sv',
               'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_roots.sv',
               'rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv',
               'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv',
               'rtl/v41die/ot_s81_cfg7_seq_bfp.sv',
               'rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h9_l4_lp_plan_kit.sv']
        hashes={}
        for name in names:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(name+' source\n')
            hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
        self.schedule=self.root/'schedule.json';self.schedule.write_text('exact return schedule\n')
        self.key=B.shape_key('col_h9',2,'asb_x')
        self.rec=dict(key=self.key,ok=True,asbuilt_source_qualification=dict(status='PASS_STATIC_REPLAY',clock_ps=833,
                      payload_control_caught=True,one_edge_control_caught=True,source_sha256=hashes,
                      native_family_hold=True,
                      schedule_sha256=hashlib.sha256(self.schedule.read_bytes()).hexdigest()))
        env=patch.dict(os.environ,OT_S81_SELECTED_SOURCE_ROOT=str(self.root));env.start();self.addCleanup(env.stop)
        schedule=patch.object(lower_xs,'source_frame_schedule',return_value=self.schedule);schedule.start();self.addCleanup(schedule.stop)

    def test_explicit_candidate_reaches_real_measurement_selection(self):
        p=self.root/'candidate.json';p.write_text(json.dumps({self.key:self.rec}))
        with patch.dict(os.environ,OT_XS_BF_MEAS=str(p)):
            rec,scope=B.meas_for(B.load_meas(),'col_h9',2,'asb_x')
        self.assertEqual(rec,self.rec);self.assertEqual(scope,'measured_bf_active_idle_q')
        self.assertEqual(B.meas_for({self.key:self.rec},'col_h9',2,'asb_x',op='attn.cmp.wk'),(None,None))

    def test_source_change_is_not_accepted_as_old_timing(self):
        p=self.root/'rtl/v41rom/ot_v41_bf_front_core_roots.sv';p.write_text('changed BF pipeline\n')
        with self.assertRaisesRegex(ValueError,'source changed'):
            B.meas_for({self.key:self.rec},'col_h9',2,'asb_x')

    def test_schedule_and_fault_controls_are_required(self):
        self.schedule.write_text('one more return edge\n')
        with self.assertRaisesRegex(ValueError,'schedule changed'):
            B.meas_for({self.key:self.rec},'col_h9',2,'asb_x')
        bad=copy.deepcopy(self.rec);bad['asbuilt_source_qualification']['one_edge_control_caught']=False
        with self.assertRaisesRegex(ValueError,'fault controls'):
            B.meas_for({self.key:bad},'col_h9',2,'asb_x')

    def test_return_topology_reads_selected_snapshot_not_compiler_checkout(self):
        self.schedule.write_text(json.dumps(dict(source_sha256=self.rec['asbuilt_source_qualification']['source_sha256'],
                                                topology=dict(master='col_h9',nodes=[]))))
        with patch.object(B,'ROOT',self.root/'different_compiler_checkout'):
            self.assertEqual(B.frame_topology('col_h9','asb_x'),dict(master='col_h9',nodes=[]))


if __name__=='__main__':unittest.main()
