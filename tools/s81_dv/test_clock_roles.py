import copy
import hashlib
import tempfile
from pathlib import Path
import unittest
from clock_roles import contract_clock_nets, whole_spare_frame_clock_outputs, validate_spare_frame_source_guard

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
class SpareFrameSourceGuardTests(unittest.TestCase):
    def fixture(self, directory):
        directory=Path(directory);die=directory/'die.v';die.write_text('module dv_die; endmodule\n')
        ref='1'*40;paths={};pinned={};proofs=[]
        for h in (9,10):
            module=f'col_h{h}_l4_lp';rel=f'rtl/dsrom_sys/s81_dv/frame_lp/col_h{h}_l4_lp_rf3r.sv'
            lines=[]
            for k in range(4):
                x=','.join(f'x[{b}]' for b in range(276*(k+1)-1,276*k-1,-1))
                xo=','.join(f'xo[{b}]' for b in range(276*(k+1)-1,276*k-1,-1))
                lines.append(f'  forward u_xo{k} (.ck(xk[{k}]), .ck_o(xok[{k}]), .i({{{x}}}), .o({{{xo}}}));')
            source='module '+module+';\n'+'\n'.join(lines)+'\nendmodule\n'
            path=directory/(module+'.sv');path.write_text(source);paths[module]=path;pinned[(ref,rel)]=source
            proofs.append({'path':rel,'ref':ref,'sha256':hashlib.sha256(source.encode()).hexdigest()})
        insts=[('col_h9_l4_lp',f'u_f_{n}',None,{})for n in range(72)]
        guard={'frame_instances':[f'f_{n}'for n in range(72)],'frame_source_proofs':proofs}
        strict={'verdict':'PASS','die_sha256':hashlib.sha256(die.read_bytes()).hexdigest()}
        return guard,paths,insts,die,strict,pinned
    def run_fixture(self, fixture):
        guard,paths,insts,die,strict,pinned=fixture
        validate_spare_frame_source_guard(guard,paths,insts,die,strict,lambda ref,path:pinned.get((ref,path)))
    def test_actualstyle_forwarding_fixture_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:self.run_fixture(self.fixture(directory))
    def test_changed_source_identity_or_forwarding_refuses(self):
        cases=('die_sha','selected_source','ref_bytes','wrong72','clock_input','clock_output','data_bit')
        for case in cases:
            with self.subTest(case=case),tempfile.TemporaryDirectory() as directory:
                fixture=self.fixture(directory);guard,paths,insts,die,strict,pinned=fixture
                proof=guard['frame_source_proofs'][0];path=paths['col_h9_l4_lp'];key=(proof['ref'],proof['path'])
                if case=='die_sha':die.write_text('module altered_die; endmodule\n')
                elif case=='selected_source':path.write_text(path.read_text()+'// changed selected source\n')
                elif case=='ref_bytes':pinned[key]+='// changed Git ref bytes\n'
                elif case=='wrong72':guard['frame_instances'].pop()
                else:
                    old,new={'clock_input':('.ck(xk[0])','.ck(xk[1])'),
                        'clock_output':('.ck_o(xok[0])','.ck_o(xok[1])'),
                        'data_bit':('x[275]','x[274]')}[case]
                    changed=path.read_text().replace(old,new,1);path.write_text(changed)
                    pinned[key]=changed;proof['sha256']=hashlib.sha256(changed.encode()).hexdigest()
                with self.assertRaises(ValueError):self.run_fixture(fixture)
if __name__=='__main__':unittest.main()
