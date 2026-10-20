import hashlib
import tempfile
import unittest
from pathlib import Path

import kv_pvw_residual_roles as V

CTL_TEXT = '''module ot_qwen_tp8_pv_wide_ctl_tb(output reg[59:0] cmd,output reg fault,output reg busy,output reg[15:0] out_age);
 always @(posedge clk or negedge local_rst_n)if(!local_rst_n)cmd<=0;
  else begin
   cmd<=0;
   cmd[0]<=rn[0];cmd[8:1]<=x;cmd[31]<=y;
  end
 always @(posedge clk or negedge local_rst_n)
  if(!local_rst_n)begin fault<=0;busy<=0;out_age<=0;out_epoch<=0;end
  else begin
   fault<=flt;busy<=state!=IDLE;out_epoch<=ep;
   out_age<=k_oa+nq;
  end
 always @* if(state!=IDLE&&cv_r[0]!=out_slot)cbad=1;
 always @(posedge clk) if(x) ; else if((start_r&&state!=IDLE)||(state!=IDLE&&cbad))begin state<=IDLE;flt<=1;end
endmodule
'''
FRAME_TEXT = '''module qkd_pvw_die_tb();
 wire[35:0] w_DL1,w_B;
 qkd_rlys_36 u_DL1_r0 (.ck(k), .a({w_DL1[34:0], x}), .b(w_DL1));
 qkd_rlys_36 u_B_r0 (.ck(k), .a(x), .b(w_B[35:0]));
 consumer c(.a(w_B));
endmodule
'''
DIE = '''module die();
wire [35:0] src;
wire [35:0] n_pvw_0__w_DL1;
wire [35:0] n_pvw_0__w_B;
wire [59:0] c0;
wire [59:0] c1;
wire b0;
wire b1;
wire f0;
wire f1;
wire [15:0] a0;
wire [15:0] a1;
prod p(.y(src));
qkd_rlys_36 pvw_0__u_DL1_r0(.a(src),.b(n_pvw_0__w_DL1));
qkd_rlys_36 pvw_0__u_B_r0(.a(src),.b(n_pvw_0__w_B));
consumer c(.a(n_pvw_0__w_B));
ot_qwen_tp8_pv_wide_ctl_tb pvw_0__u_ctl(.cmd(c0),.busy(b0),.out_age(a0),.fault(f0));
ot_qwen_tp8_pv_wide_ctl_tb pvw_1__u_ctl(.cmd(c1),.busy(b1),.out_age(a1),.fault(f1));
fsink fs(.a(f0),.b(f1));
cmdsink cs(.a(c0[31:0]),.b(c1[31:0]));
endmodule
'''


class PVWResidualTests(unittest.TestCase):
    def setup(self, d, die=DIE, frame=FRAME_TEXT, ctl=CTL_TEXT):
        root = Path(d)
        for rel, text in ((V.FRAME, frame), (V.CTL, ctl)):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
        (root / 'die.v').write_text(die)
        pins = {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in (V.FRAME, V.CTL)}
        return root, pins

    def run_(self, root, pins):
        return V.derive(root / 'die.v', root, dict(pads={}, instances={}), pins)

    def test_positive_duplicate_cargo_and_ctl_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root, pins = self.setup(d)
            doc = self.run_(root, pins)
            c = doc['pvw_residual_contract']
            # the frame shift line reads w_DL1[34:0] itself: only the terminal bit 35 is generator-unused
            self.assertEqual(c['classes'], dict(delay_terminal_cargo=1, reserved_zero_command=56, self_checked_status=34))
            self.assertEqual(doc['instances']['pvw_0__u_DL1_r0']['ports']['b'], [[35, 35]])
            self.assertEqual(doc['instances']['pvw_0__u_ctl']['ports'], dict(cmd=[[32, 59]], busy=[[0, 0]], out_age=[[0, 15]]))
            self.assertNotIn('pvw_0__u_B_r0', doc['instances'])   # read branch, never declared

    def test_origin_not_consumed_elsewhere_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root, pins = self.setup(d, die=DIE.replace('consumer c(.a(n_pvw_0__w_B));\n', ''))
            doc = self.run_(root, pins)
            self.assertNotIn('pvw_0__u_DL1_r0', doc['instances'])
            self.assertEqual(doc['pvw_residual_contract']['refused']['origin not consumed by any other branch'], 36)

    def test_die_reader_and_frame_reference_block_bits(self):
        with tempfile.TemporaryDirectory() as d:
            die = DIE.replace('endmodule', 'reader r(.a(n_pvw_0__w_DL1[35]));\nendmodule')
            frame = FRAME_TEXT.replace('.a({w_DL1[34:0], x})', '.a(x)').replace('consumer c(.a(w_B));', 'consumer c(.a(w_B));\n tap t(.a(w_DL1[3]));')
            root, pins = self.setup(d, die=die, frame=frame)
            doc = self.run_(root, pins)
            self.assertEqual(doc['instances']['pvw_0__u_DL1_r0']['ports']['b'], [[0, 2], [4, 34]])

    def test_source_sha_change_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root, pins = self.setup(d)
            (root / V.FRAME).write_text(FRAME_TEXT + '\n// edited\n')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                self.run_(root, pins)

    def test_unread_fault_voids_status_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root, pins = self.setup(d, die=DIE.replace('fsink fs(.a(f0),.b(f1));\n', 'fsink fs(.b(f1));\n'))
            with self.assertRaisesRegex(ValueError, 'fault has no die reader'):
                self.run_(root, pins)

    def test_command_write_above_31_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root, pins = self.setup(d, ctl=CTL_TEXT.replace('cmd[31]<=y;', 'cmd[31]<=y;cmd[40]<=z;'))
            with self.assertRaisesRegex(ValueError, 'above 31'):
                self.run_(root, pins)


if __name__ == '__main__':
    unittest.main()
