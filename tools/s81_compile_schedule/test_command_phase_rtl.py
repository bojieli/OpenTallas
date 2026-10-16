"""Actual fixed issuer/controller command-phase seam; arithmetic is out of scope."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from compile_calendar import ROOT, command_issue_phase
sys.path.insert(0,str(ROOT/'tools/s81_static_control'))
from program import encode_program


class RtlPhaseTest(unittest.TestCase):
    def test_real_command_sample_and_wrong_phase_mutant(self):
        sources=['rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv',
                 'rtl/dsrom_sys/s81_hcx/ot_s81_hcx_controller.sv',
                 'rtl/dsrom_sys/s81_hcx/ot_s81_hcx_prefetch.sv']
        clock=dict(stream_period_ps='2500/3',serial_period_ps='10000/9',
                   first_active_stream_edge=1000,context_accept_stream_edge=1250,
                   issuer_to_engine_sample_edges=2,required_counter_phase=2,
                   evidence=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in sources])
        period,phase=command_issue_phase(clock)
        self.assertEqual((period,phase),(4,2))
        for issue,expect in [(phase,0),((phase+2)%period,1)]:
            rows=[dict(engine=11,arg=0,issue=issue,done=20),dict(engine=15,arg=0,issue=24,done=0)]
            encoded=encode_program(rows,0,3)
            writes='\n'.join(f'write_pw(7\'d{w["address"]},28\'h{w["data"]:07x});' for w in encoded['writes'])
            tb=r'''
`timescale 1ns/1ps
module tb;
reg ck=0,sk=0,rst=0;always #5 ck=~ck;always #6.666667 sk=~sk;
integer cyc=0;always @(posedge ck)cyc<=cyc+1;
reg pw=0;reg[6:0]pa=0;reg[27:0]pd=0;wire[12:0]cv;wire[1091:0]cd;
wire fault;wire[3:0]code;
ot_s81_fixed_issue #(.NOPS(2),.NENG(13),.ENG_PRESENT(13'h800)) issuer(
.clk(ck),.rst_n(rst),.pw_v(pw),.pw_a(pa),.pw_d(pd),.prog_len(8'd2),
.job_v(cyc==1250),.job_user(10'd0),.job_pos(21'd0),.job_tok(21'd0),
.cmd_v(cv),.cmd_d(cd),.engine_available(13'h800),.dn_v(13'd0),.dn_tag(104'd0),.fault(fault),.fault_code(code));
ot_s81_hcx_controller #(.FAST_CYC(483)) ctl(.cck(ck),.crst_n(rst),.sk(sk),.srst_n(rst),
.c_cmd({cv[11],cd[84*11+:84]}),.rs_v(8'd0),.leaf_v(6'd0),.leaf_fault(6'd0),.leaf_d(192'd0));
task write_pw(input[6:0]a,input[27:0]d);begin
@(negedge ck);pw=1;pa=a;pd=d;@(negedge ck);pw=0;end endtask
initial begin
while(cyc<1000)@(negedge ck);rst=1;
while(cyc<1010)@(negedge ck);
WRITES
end
always @(posedge ck)if(rst&&cv[11])begin
if(fault)$fatal(1,"issuer fault %d",code);
$display("SAMPLE cycle=%0d phase=%0d",cyc,ctl.phase);
#1;
if(ctl.cfault!==EXPECT)$fatal(1,"wrong phase witness %b expected EXPECT",ctl.cfault);
$display("PHASE_SEAM_PASS expect_fault=EXPECT");$finish;
end
initial begin #14000;$fatal(1,"missing compiled command");end
endmodule
'''.replace('WRITES',writes).replace('EXPECT',f"1'b{expect}")
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);(p/'tb.sv').write_text(tb)
                subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),str(p/'tb.sv')]+[str(ROOT/s) for s in sources],check=True,capture_output=True,text=True)
                out=subprocess.run(['vvp',str(p/'sim')],check=True,capture_output=True,text=True).stdout
                self.assertIn('PHASE_SEAM_PASS',out)
                print(out.strip())


if __name__=='__main__':unittest.main()
