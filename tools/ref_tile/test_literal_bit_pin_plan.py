import copy,json,tempfile,unittest
from pathlib import Path
import ref_tile as RT
from pre_route_gate import Gate, PortMap, check_pins

class LiteralPinPlan(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'dut.sv').write_text('module dut #(parameter N=4, BASE=4)(input wire clk, input wire [BASE+N-1:BASE] d, output wire [0:0] one); assign one=^d; endmodule')
        names=['clk','d[4]','d[5]','d[6]','d[7]','one'];faces=['S','N','N','W','W','S'];layers=['M4','M5','M5','M6','M6','M4']
        self.io='\n'.join(f'ot_assigned_pin_exact {{{n}}} {l} {f} {i+1}.000000' for i,(n,l,f) in enumerate(zip(names,layers,faces)))+'\n'
        (self.root/'pins.tcl').write_text(self.io)
        self.s={'name':'dut','top':'dut','sources':['dut.sv'],'clock_port':'clk','pins':{'S':['clk','one'],'N':['d[4]','d[5]'],'W':['d[6]','d[7]']},'io_tcl':'pins.tcl','m6_pin_grant':{'schema':'opentallas.m6_pin_grant.v1','master':'dut','granted_by':'test die lead','reason':'exact local contacts','source_commit':'1'*40,'source_spec_sha256':'2'*64,'ports':[{'name':n,'face':'W','span_um':[i+.9,i+1.1],'max_depth_um':.384,'max_area_um2':.024576}for i,n in [(3,'d[6]'),(4,'d[7]')]]}}
    def tearDown(self):self.tmp.cleanup()
    def valid(self,s=None,ports=None):return RT.validate_literal_pin_plan(s or self.s,ports,self.root)
    def test_actual_nonzero_bounds_and_complete_split(self):
        self.assertEqual(6,len(self.valid()))
        p=PortMap({'clk':(1,False),'d':(4,True),'one':(1,True)},{'d':[4,7],'one':[0,0]})
        self.assertEqual(6,len(self.valid(ports=p)))
    def test_synthesized_symbolic_width_requires_evaluated_bounds(self):
        p=PortMap({'clk':(1,False),'d':(None,True),'one':(1,True)}, {'d':[4,7],'one':[0,0]})
        self.assertEqual(6,len(self.valid(ports=p)))
        for bounds in [{}, {'d':None}, {'d':[7,4]}, {'d':['4',7]}]:
            with self.subTest(bounds=bounds),self.assertRaises(RT.SpecError):
                self.valid(ports=PortMap(dict(p),bounds))

    def test_scalar_zero_alias_and_range_stay_forbidden(self):
        for n in ['one[0]','d[7:4]','d[3]','d[8]']:
            s=copy.deepcopy(self.s);s['pins']['S'][1]=n
            with self.subTest(n=n),self.assertRaises(RT.SpecError):self.valid(s)
    def test_missing_duplicate_and_mixed_base_bit_fail(self):
        for op in ['missing','duplicate','base']:
            s=copy.deepcopy(self.s)
            if op=='missing':s['pins']['W'].pop()
            elif op=='duplicate':s['pins']['N'].append('d[6]')
            else:s['pins']['N'].append('d')
            with self.subTest(op=op),self.assertRaises(RT.SpecError):self.valid(s)
    def test_parameter_override_and_measured_shape_cannot_shrink(self):
        s=copy.deepcopy(self.s);s['params']={'N':2}
        with self.assertRaises(RT.SpecError):self.valid(s)
        p=PortMap({'clk':(1,False),'d':(4,True),'one':(1,True)},{'d':[0,3],'one':[0,0]})
        with self.assertRaises(RT.SpecError):self.valid(ports=p)
    def test_exact_source_and_grant_are_required(self):
        for field in ['io_tcl','m6_pin_grant']:
            s=copy.deepcopy(self.s);s.pop(field)
            with self.subTest(field=field),self.assertRaises(RT.SpecError):self.valid(s)
    def test_io_face_missing_duplicate_and_ungranted_m6_fail(self):
        for bad in [self.io.replace('M6 W 4.000000','M6 E 4.000000'),self.io.replace('ot_assigned_pin_exact {d[7]} M6 W 5.000000\n',''),self.io+'ot_assigned_pin_exact {clk} M4 S 1.000000\n',self.io.replace('{clk} M4','{clk} M6')]:
            (self.root/'pins.tcl').write_text(bad)
            with self.subTest(io=bad),self.assertRaises(RT.SpecError):self.valid()
    def test_synthesized_gate_uses_actual_index_bounds(self):
        import pre_route_gate as PG
        old=PG.ROOT;PG.ROOT=self.root
        try:
            for bounds,fail in [([4,7],False),([0,3],True)]:
                g=Gate();p=PortMap({'clk':(1,False),'d':(4,True),'one':(1,True)},{'d':bounds,'one':[0,0]})
                check_pins(g,self.s,p,where='synthesized netlist')
                self.assertEqual(fail,any(i['severity']=='FAIL'for i in g.items))
        finally:PG.ROOT=old

if __name__=='__main__':unittest.main()
