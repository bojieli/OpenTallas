import copy
import unittest
from clock_roles import contract_clock_nets, whole_spare_frame_clock_outputs

class ClockRoleTests(unittest.TestCase):
    def setUp(self):
        self.insts=[('launch','u_a',None,{}),('frame','u_b',None,{})]
        self.bits={'u_a':{'clk':[('root',0)],'fwd':[('laneclk',0)],'data':[('payload',0)]},
                   'u_b':{'xk':[('laneclk',0)],'x':[('payload',0)]}}
        self.masters={'a':{'clk':'clk','ports':{'o':{'ck':'fwd'}}},'b':{'ports':{'i':{'ck_in':'xk'}}}}
        self.dirs={'launch':{'clk':'input','fwd':'output','data':'output'},'frame':{'xk':'input','x':'input'}}
    def run_it(self, known={'root'}):
        return contract_clock_nets(self.insts,self.bits,self.masters,{'launch':'a','frame':'b'},self.dirs,known)
    def test_direct_clock_contract_not_data(self):
        nets,sinks=self.run_it();self.assertIn('laneclk',nets);self.assertNotIn('payload',nets);self.assertEqual(sinks,[('u_b','xk')])
    def test_wrong_declared_data_input_refuses(self):
        self.masters['b']['ports']['i']['ck_in']='x'
        with self.assertRaisesRegex(ValueError,'missing clock source'):self.run_it()
    def test_missing_clock_source_refuses(self):
        self.masters['a']['ports']={}
        with self.assertRaisesRegex(ValueError,'missing clock source'):self.run_it()
    def test_unreached_source_refuses(self):
        with self.assertRaisesRegex(ValueError,'unreached declared clock source'):self.run_it(set())
    def test_wrong_direction_refuses(self):
        self.masters['a']['ports']['o']['ck']='clk'
        with self.assertRaisesRegex(ValueError,'expected connected output'):self.run_it()
    def test_constant_unused_clock_bit_does_not_hide_missing_source(self):
        self.bits['u_b']['xk'] += [('CONST',0),('unknown',1)]
        with self.assertRaisesRegex(ValueError,'missing clock source'):self.run_it()
class WholeSpareFrameClockTests(unittest.TestCase):
    def setUp(self):
        self.module='col_h9_l4_lp';self.inst='u_f_end'
        self.insts=[(self.module,self.inst,None,{})]
        self.bits={self.inst:{'ck':[('root',0)],'xk':[('laneclk',0)]}}
        self.masters={'frame':{'clk':'ck','ports':{'o':{'ck':'xok'},'i':{'ck_in':'xk'}}}}
        self.mapping={self.module:'frame'}
        self.dirs={self.module:{'ck':'input','xk':'input','xok':'output'}}
        self.widths={self.module:{'xok':4}}
        self.pads={'instances':{self.inst:{'master':self.module,
            'reason':'selected72 frame X-chain end: source-checked u_xo0..3',
            'ports':{'xok':[[0,3]]}}}}
        self.guard={'frame_instances':['f_end']+[f'f_other_{i}' for i in range(71)],
            'frame_source_proofs':[{'path':f'rtl/dsrom_sys/s81_dv/frame_lp/col_h{h}_l4_lp_rf3r.sv',
                'ref':'1'*40,'sha256':'2'*64} for h in (9,10)]}
    def unused(self):
        return whole_spare_frame_clock_outputs(self.insts,self.bits,self.masters,self.mapping,
            self.dirs,self.widths,self.pads,self.guard)
    def run_it(self,known={'root','laneclk'}):
        return contract_clock_nets(self.insts,self.bits,self.masters,self.mapping,
            self.dirs,known,spare_frame_context=(self.widths,self.pads,self.guard))
    def test_exact_whole_absent_source_guarded_output_only(self):
        self.assertEqual(self.unused(),{(self.inst,'xok')})
        _,sinks=self.run_it();self.assertEqual(sinks,[(self.inst,'xk')])
    def test_missing_guard_still_refuses(self):
        self.guard={}
        self.assertEqual(self.unused(),set())
        with self.assertRaisesRegex(ValueError,'expected connected output'):self.run_it()
    def test_partial_spare_still_refuses(self):
        self.pads['instances'][self.inst]['ports']['xok']=[[0,2]]
        self.assertEqual(self.unused(),set())
        with self.assertRaisesRegex(ValueError,'expected connected output'):self.run_it()
    def test_wrong_instance_spare_still_refuses(self):
        self.pads['instances']['other']=self.pads['instances'].pop(self.inst)
        self.assertEqual(self.unused(),set())
        with self.assertRaisesRegex(ValueError,'expected connected output'):self.run_it()
    def test_input_direction_never_skipped(self):
        self.dirs[self.module]['xok']='input'
        self.assertEqual(self.unused(),set())
        with self.assertRaisesRegex(ValueError,'expected connected output'):self.run_it()
    def test_missing_input_never_skipped(self):
        del self.bits[self.inst]['xk']
        with self.assertRaisesRegex(ValueError,'expected connected input'):self.run_it()
    def test_active_output_keeps_source_reach_check(self):
        self.bits[self.inst]['xok']=[('outclk',b) for b in range(4)]
        self.assertEqual(self.unused(),set())
        with self.assertRaisesRegex(ValueError,'unreached declared clock source'):self.run_it({'laneclk'})
    def test_missing_declared_root_input_never_skipped(self):
        del self.bits[self.inst]['ck']
        with self.assertRaisesRegex(ValueError,'expected connected input'):self.run_it()
    def test_no_declared_root_never_skipped(self):
        del self.masters['frame']['clk']
        with self.assertRaisesRegex(ValueError,'no declared input clock'):self.run_it()
    def test_partial_connected_output_not_classified_spare(self):
        self.bits[self.inst]['xok']=[('outclk',0)]
        self.assertEqual(self.unused(),set())
        with self.assertRaisesRegex(ValueError,'unreached declared clock source'):self.run_it({'laneclk'})
if __name__=='__main__':unittest.main()
