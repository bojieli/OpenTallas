"""Compiler mechanism tests; synthetic evidence here is NOT native qualification."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('static_su_calendar',Path(__file__).parents[1]/'static_su_calendar.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)

class CalendarTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        events=dict(reads=[dict(cycle=1,slot=0,row=0),dict(cycle=2,slot=0,row=16),dict(cycle=2,slot=1,row=32)],
                    responses=[dict(cycle=16,slot=0,row=0),dict(cycle=17,slot=0,row=16),dict(cycle=17,slot=1,row=32)],
                    writes=[dict(cycle=30,commit_cycle=41,slot=0,row=64,mask=65535)])
        pins=C.inventory()['operations']['RB']['sources']
        self.e=Path(self.tmp.name)/'mechanism-fixture.json'
        self.e.write_text(json.dumps(dict(arithmetic='native-rtl',passed=True,sources=pins,op='RB',events=events)))
        self.job=dict(op='RB',sources=pins,evidence=dict(path=str(self.e),sha256=hashlib.sha256(self.e.read_bytes()).hexdigest()),
                      start=0,done=42,count=1,id=7,tag=42,gain_set=0,fp4=False,events=events)
        self.p=dict(cycles=44,jobs=[self.job])
    def test_softmax_tail_full8192_values_are256_bf16_rows(self):
        self.assertEqual(C.row_counts('SO',1),(5,8192//16,8192//32))
    def test_moe_opcode_preserves_cp14_persistent_contract(self):
        self.assertEqual(C.OPS['MOE'],15)
        self.assertNotIn('CP',C.OPS)
    def test_explicit_edges_and_halt(self):
        words=C.compile_program(self.p)
        self.assertEqual(words[2]&3,3)
        self.assertEqual((words[30]>>256)&65535,1)
        self.assertEqual((words[42]>>768)&511,1+(42<<1))
        self.assertEqual(words[43],1<<788)
    def test_missing_full_shape_read_rejected(self):
        self.job['count']=2
        with self.assertRaisesRegex(ValueError,'full-shape'): C.compile_program(self.p)
    def test_stale_arithmetic_rejected(self):
        self.job['sources']=dict(self.job['sources']);self.job['sources'][next(iter(self.job['sources']))]='0'*64
        with self.assertRaisesRegex(ValueError,'source binding'): C.compile_program(self.p)
    def test_completion_cannot_precede_commit(self):
        self.job['done']=40
        with self.assertRaisesRegex(ValueError,'before commit'): C.compile_program(self.p)
    def test_missing_native_evidence_rejected(self):
        self.e.write_text('{}')
        with self.assertRaisesRegex(ValueError,'timing evidence'): C.compile_program(self.p)
    def test_unimplemented_pool_not_aliased_to_quant(self):
        self.job['op']='CP'
        with self.assertRaisesRegex(ValueError,'unsupported'): C.compile_program(self.p)
    def test_mapped_capacity_is_finite(self):
        self.p['program_depth']=64
        self.p['cycles']=65
        with self.assertRaisesRegex(ValueError,'capacity'): C.compile_program(self.p)
    def test_actual_vm_colour_rule(self):
        self.job['events']['reads'][2]['slot']=2
        self.job['events']['responses'][2]['slot']=2
        self.e.write_text(json.dumps(dict(arithmetic='native-rtl',passed=True,sources=self.job['sources'],op='RB',events=self.job['events'])))
        self.job['evidence']['sha256']=hashlib.sha256(self.e.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'row colour'): C.compile_program(self.p)
    def test_lane_collision_rejected(self):
        self.job['events']['reads'][2]['slot']=0
        self.job['events']['responses'][2]['slot']=0
        self.e.write_text(json.dumps(dict(arithmetic='native-rtl',passed=True,sources=self.job['sources'],op='RB',events=self.job['events'])))
        self.job['evidence']['sha256']=hashlib.sha256(self.e.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'conflicting'): C.compile_program(self.p)

if __name__=='__main__':unittest.main()
