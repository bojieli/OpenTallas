"""Actual PW encoding/native admission checks; fixtures never qualify hardware."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from program import encode_program, emit_native, validate_launches

class ProgramTest(unittest.TestCase):
    def setUp(self):
        from test_compile_calendar import CompileTest
        self.fixture=CompileTest(); self.fixture.setUp()
        self.program=copy.deepcopy(self.fixture.program)
        self.binding=copy.deepcopy(self.fixture.binding)
        self.contract=copy.deepcopy(self.fixture.contract)
        self.root=self.fixture.root
        self.binding['context_launch_cycles']=[0]
        self.contract['native_clock_epoch']=dict(physical_phase_qualified=True,phase_modulus_stream=4,evidence=self.fixture.evidence)
        for owner in self.binding['jobs'].values():
            owner.update(command_abi='opentallas.s81.cmd84.v1',integration_ready=True,
                         timing_boundary='sequencer_cmd_pin_to_done_pin',clock_domain='stream',arg=0xabc123)
    def tearDown(self): self.fixture.tearDown()
    def emit(self): return emit_native(self.program,self.binding,self.contract,7,1,self.root)
    def blocked(self):
        r=self.emit();self.assertFalse(r['dispatch_eligible']);self.assertEqual(r['writes'],[]);return r
    def test_actual76bit_roundtrip_all128rows(self):
        rows=[dict(engine=i%13,arg=(0x654321+i)&0xffffff,issue=i,done=i+3)for i in range(126)]
        rows += [dict(engine=14,arg=0,issue=129,done=0),dict(engine=15,arg=0,issue=130,done=0)]
        r=encode_program(rows,127,3)
        self.assertEqual(len(r['writes']),386);self.assertFalse(r['qualified']);self.assertEqual(r['seal_to_arm_stream_cycles'],129)
        for i,row in enumerate(rows):
            triplet=r['writes'][1+3*i:4+3*i]
            packed=sum((w['data']&0x3ffffff)<<(26*j)for j,w in enumerate(triplet))
            self.assertEqual(packed,row['arg']|(row['engine']<<24)|(row['issue']<<28)|(row['done']<<52))
            self.assertEqual([w['address']for w in triplet],[i]*3)
            self.assertTrue(all(w['word']<1<<35 for w in triplet))
    def test_source_pinned_fixture_encodes_but_not_qualifies(self):
        r=self.emit();self.assertTrue(r['dispatch_eligible'],r);self.assertFalse(r['qualified'])
        self.assertEqual(r['rows'][-1]['issue'],25)
        # every engine row: done = issue + 1 + measured pin-to-pin latency
        for row in r['rows'][:-1]:self.assertEqual(row['done'],row['issue']+1+row['pin_to_pin'])
    def test_done_row_off_by_one_rejected(self):
        # MIX4 off-by-one class (done = issue + pin_to_pin) is refused by encode and emit
        good=[dict(engine=10,arg=1,issue=656,done=1429,pin_to_pin=772),dict(engine=15,arg=0,issue=1433,done=0)]
        encode_program(good,0,3)
        with self.assertRaisesRegex(ValueError,'issue \\+ 1'):
            encode_program([dict(good[0],done=1428),good[1]],0,3)
        self.program['ops'][1]['end']-=1;self.blocked()
    def test_missing_physical_epoch(self):
        del self.contract['native_clock_epoch'];self.blocked()
    def test_unqualified_physical_epoch(self):
        self.contract['native_clock_epoch']['physical_phase_qualified']=False;self.blocked()
    def test_wrong_epoch_modulus(self):
        self.contract['native_clock_epoch']['phase_modulus_stream']=3;self.blocked()
    def test_internal_done_is_not_pin_completion(self):
        self.binding['jobs']['su']['timing_boundary']='internal_core_done';self.blocked()
    def test_serial_endpoint_needs_actual_adapter(self):
        self.binding['jobs']['su']['clock_domain']='serial';self.blocked()
    def test_missing_endpoint_integration(self):
        self.binding['jobs']['su']['integration_ready']=False;self.blocked()
    def test_wrong_command_abi(self):
        self.binding['jobs']['su']['command_abi']='legacy';self.blocked()
    def test_opaque_boolean_arg_rejected(self):
        self.binding['jobs']['su']['arg']=True;self.blocked()
    def test_absent_native_operand_binding(self):
        self.binding['jobs'].pop('field');self.blocked()
    def test_unbound_constant(self):
        self.binding['tensors']['epsilon']=dict(source='resident_constant');self.blocked()
    def test_unbound_external_boundary(self):
        self.binding['tensors']['activation']=dict(source='external_input');self.blocked()
    def test_stale_evidence(self):
        (self.root/'native.sv').write_text('changed');self.blocked()
    def test_empty_program_cannot_dispatch(self):
        self.program['ops']=[];self.blocked()
    def test_missing_context_launch_calendar(self):
        del self.binding['context_launch_cycles'];self.blocked()
    def test_explicit_context_launches_and_overwrite(self):
        rows=[dict(engine=0,arg=1,issue=0,done=3),dict(engine=0,arg=2,issue=4,done=7),dict(engine=15,arg=0,issue=8,done=0)]
        self.assertEqual(validate_launches(rows,[0,12,24]),[0,12,24])
        for launches in [None,[],[0,4],[0,1],[0,0],[0,8,8],[0,4,8],[False]]:
            with self.subTest(launches=launches),self.assertRaises(ValueError):validate_launches(rows,launches)
    def test_actual59_programs_reject_missing_native_owners(self):
        import json
        from program import ROOT
        paths=sorted((ROOT/'results/rtl/s81_ctrl_20261008/programs').glob('S*.json'))
        self.assertEqual(len(paths),59)
        for path in paths:
            program=json.loads(path.read_text())
            r=emit_native(program,dict(jobs={},tensors={}),self.contract,0,1,self.root)
            self.assertFalse(r['dispatch_eligible'],path.name);self.assertEqual(r['writes'],[])
    def test_encoding_rejects_semantic_mutants(self):
        good=[dict(engine=0,arg=1,issue=2,done=6),dict(engine=15,arg=0,issue=8,done=0)]
        for rows in [[],good[:1],good+[good[0]],
                     [dict(good[0],engine=13),good[1]],
                     [dict(good[0],done=2),good[1]],
                     [dict(good[0],arg=1<<24),good[1]],
                     [good[0],dict(good[1],issue=6)],
                     good+[dict(engine=14,arg=0,issue=8,done=0)],
                     [dict(good[0],arg=True),good[1]]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError): encode_program(rows,7,1)

if __name__=='__main__':unittest.main()
