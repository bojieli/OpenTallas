"""Every bit of each optional two-stage relay equals the original relay delayed by exactly one edge."""
import subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
RTL=ROOT/'rtl/dsrom_sys/s81_static_net'

BENCH=r'''
module tb;
reg ck=0;always #5 ck=~ck;
reg rs=0;reg[65:0] ri=0;reg[535:0] pi=0;
wire[65:0] rold,rnew;wire[535:0] pold,pnew;
reg[65:1] rdata;reg rv;
reg[530:0] phi;reg[2:0] plo;reg[1:0] pv;
dsfd_rstg oldr(ck,ri,rold,rs);
dsfd_rstg_2stage newr(ck,ri,rnew,rs);
ot_s81_sstn_payload536 oldp(ck,rs,pi,pold);
ot_s81_sstn_payload536_2stage newp(ck,rs,pi,pnew);
always @(posedge ck) begin rdata<=rold[65:1];phi<=pold[535:5];plo<=pold[3:1];end
always @(posedge ck or negedge rs) begin
 if(!rs) begin rv<=0;pv<=0;end else begin rv<=rold[0];pv<={pold[4],pold[0]};end
end
integer j,k;reg[31:0] x=32'h01234567;
initial begin
 repeat(6) @(negedge ck);
 for(k=0;k<12000;k=k+1) begin
  x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);
  rs=(k%137!=0 && k%137!=1);
  for(j=0;j<66;j=j+1) begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);ri[j]=x[0];end
  for(j=0;j<536;j=j+1) begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);pi[j]=x[0];end
  @(negedge ck);
  if(rnew!=={rdata,rv}) $fatal(1,"RSTG_LATENCY_LOCKSTEP_FAIL cycle%0d",k);
  if(pnew!=={phi,pv[1],plo,pv[0]}) $fatal(1,"PAYLOAD_LATENCY_LOCKSTEP_FAIL cycle%0d",k);
 end
 $display("RELAY2_LOCKSTEP_PASS words12000 bits602 cycles_added1");$finish;
end
endmodule
'''

@pytest.mark.parametrize('mutant',['none','wrong_depth','wrong_data'])
def test_latency_aligned_lockstep_and_mutants(tmp_path,mutant):
    rst=(RTL/'dsfd_rstg_2stage.sv').read_text();payload=(RTL/'ot_s81_sstn_payload536_2stage.sv').read_text()
    if mutant=='wrong_depth':rst=rst.replace('assign o = {launch_data, launch_valid};','assign o = {capture_data, capture_valid};')
    if mutant=='wrong_data':payload=payload.replace('assign o = {launch_hi, launch_valid[1], launch_lo, launch_valid[0]};','assign o = {launch_hi, launch_valid[1], launch_lo, launch_valid[0]} ^ (536\'b1 << 23);')
    (tmp_path/'new.sv').write_text(rst+payload);(tmp_path/'bench.sv').write_text(BENCH)
    exe=tmp_path/'sim'
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(RTL/'gen/dsfd_rstg.sv'),str(RTL/'ot_s81_sstn_payload536.sv'),str(tmp_path/'new.sv'),str(tmp_path/'bench.sv')],check=True,capture_output=True)
    p=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
    if mutant=='none':assert p.returncode==0 and 'RELAY2_LOCKSTEP_PASS' in p.stdout,p.stdout+p.stderr
    else:assert p.returncode!=0 and 'LOCKSTEP_FAIL' in p.stdout,p.stdout+p.stderr
