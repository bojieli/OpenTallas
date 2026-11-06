import unittest
from kit_rsync import add_reset_outs

class BoundResetOut(unittest.TestCase):
    def test_last_bound_reset_is_canonical_and_idempotent(self):
        for vector in ('','[0:0] '):
            text=f'''module top (
    input wire clk,
    input wire arst_n,
    output wire {vector}rst_o_0 // bound-only reset
);
child u (
    .clk(clk),
    .arst_n(arst_n),
    .rst_o_0(rst_o_0)
);
endmodule
'''
            args=[('rst_o_0',1.,2.)]
            first,nd,nc=add_reset_outs(text.splitlines(True),args,conn=True)
            self.assertEqual((nd,nc),(1,1))
            second,_,_=add_reset_outs(first,args,conn=True)
            self.assertEqual(first,second)
            s=''.join(first)
            self.assertEqual(s.count('.rst_o_0(rst_o_0)'),1)
            self.assertEqual(s.count('output wire rst_o_0'),1)
            self.assertNotIn('.clk(clk),\n);',s)

if __name__=='__main__':unittest.main()
