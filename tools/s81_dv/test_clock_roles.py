import copy
import unittest
from clock_roles import contract_clock_nets

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
if __name__=='__main__':unittest.main()
