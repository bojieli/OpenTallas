import unittest
import kv_fault_rewire as R


class RewriteTests(unittest.TestCase):
    def inputs(self):
        text="""module die();
wire clk,rst,f,old_hf;
wire [35:0] old0,spare;
qkd_rlysh0_36 first (.ck(clk),.en(rst),.a(36'b0),.b(old0));
qkd_landsh_36 last (.ck(clk),.rs(rst),.a(36'b0),.b(spare),.fault(f));
qkd_ctrl_kc kc_WS (.ck(clk),.rsi(rst));
qkd_kvs_attn kvs_attn (.ck(clk),.rst_n(rst),.ufh(old_hf));
endmodule
"""
        nets={'clk':(1,0),'rst':(1,0),'f':(1,0),'old_hf':(1,0),'old0':(36,0),'spare':(36,0)}
        insts=[('qkd_rlysh0_36','first',{},dict(ck='clk',en='rst',a="36'b0",b='old0')),
               ('qkd_landsh_36','last',{},dict(ck='clk',rs='rst',a="36'b0",b='spare',fault='f')),
               ('qkd_ctrl_kc','kc_WS',{},dict(ck='clk',rsi='rst')),
               ('qkd_kvs_attn','kvs_attn',{},dict(ck='clk',rst_n='rst',ufh='old_hf'))]
        node=lambda id,a,b,kind:dict(id=id,a=a,b=b,kind=kind,clock='clk',reset='rst',placement=dict(x=0,y=0))
        plan=dict(sources=[dict(id='kf',instance='kc_WS',port='kf',signal=None),dict(id='existing_ufh',signal=['old_hf',0])],
                  transports=[dict(id='t0',payload_bit=35,stations=['first','last'],source='kf')],
                  nodes=[node('fold','t0','existing_ufh','join'),node('final','fold','final','sticky')],sink='final')
        return text,nets,insts,plan

    def test_functional_bit_is_renamed_and_carried_across_every_retied_hop(self):
        text,nets,insts,plan=self.inputs();out,occupied,pl=R.rewrite(text,nets,insts,plan)
        self.assertIn('.kf(n_kv_fault_source_kc_WS)',out)
        self.assertIn('.a({n_kv_fault_source_kc_WS,',out)
        self.assertIn('.a({n_kv_fault_t0_s0,',out)
        self.assertIn('.b({n_kv_fault_t0_s1,spare[34]',out)
        self.assertIn('.ufh(n_kv_fault_final)',out)
        self.assertIn('.a(n_kv_fault_t0_s1), .b(old_hf[0])',out)
        self.assertEqual(len(occupied),4)
        self.assertEqual(len(pl),2)

    def test_double_allocation_is_rejected(self):
        text,nets,insts,plan=self.inputs();plan['transports'].append(dict(plan['transports'][0],id='t1'))
        with self.assertRaisesRegex(ValueError,'allocated twice'):R.rewrite(text,nets,insts,plan)

    def test_existing_source_connection_cannot_be_silently_replaced(self):
        text,nets,insts,plan=self.inputs();insts[2][3]['kf']='f'
        with self.assertRaisesRegex(ValueError,'already connected'):R.rewrite(text,nets,insts,plan)

    def test_nonduplicate_pipe_input_is_rejected(self):
        text,nets,insts,plan=self.inputs();plan['nodes'][0]['kind']='pipe'
        with self.assertRaisesRegex(ValueError,'duplicated real input'):R.rewrite(text,nets,insts,plan)


if __name__=='__main__':unittest.main()
