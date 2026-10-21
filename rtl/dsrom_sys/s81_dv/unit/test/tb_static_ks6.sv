`timescale 1ns/1ps
module tb_static_ks6;
reg ck=0;always #0.5 ck=~ck;
reg rn=0;reg[514:0] host=0;reg[52:0] incoming=0;
wire[52:0] timed;wire selected,armed,done;wire[3:0] fault;
wire[514:0] issued_host=(host[0] && host[8:1]>=8'h17 &&host[8:1]<=8'h19)?515'd0:host;
wire[52:0] issued_ks=selected?timed:incoming;
dsdv_static_ks6 a(.ck(ck),.rst_n(rn),.f_host(host),.f_ks(incoming),.upstream_fault(1'b0),.timed_ks(timed),.selected(selected),.armed(armed),.done(done),.fault(fault));
wire[53:0] kd;wire[76:0] th;wire[275:0] vn,vs;wire[32:0] sj;wire[291:0] hw0,hw1;wire cv;wire[9:0] ca;wire[255:0] cd;
dsdv_seq_host dut(.ck(ck),.rst_n(rn),.tap_k(8'd0),.sink_k(8'd0),.vi_s(276'd0),.vi_n(276'd0),.vo_s(vs),.vo_n(vn),.f_host(issued_host),.t_host(th),.f_lf(4'b0101),.f_ks(issued_ks),.t_kd(kd),.s_j(sj),.s_jd_w(2'd0),.s_jd_e(2'd0),.s_hw_w(hw0),.s_hw_e(hw1),.s_hc_w(9'd0),.s_hc_e(9'd0),.st_rg_w(2'b01),.st_rg_e(2'b01),.cw_v(cv),.cw_a(ca),.cw_d(cd));
integer edge_n=0,seen=0,retired=0,commands=0,mode=0,firstedge;reg[47:0] epoch;reg[511:0] d;reg[75:0] row;integer i,j,delta;
function[52:0] desc(input integer n);begin desc={1'b1,10'd37,21'(1703+97*n),21'(6029+3*n)};end endfunction
always @(posedge ck) begin
 edge_n=edge_n+1;
 if(rn&&timed[52]) begin
  if(mode==0&&(timed!==desc(seen)||edge_n!=firstedge+seen*1259408))$fatal(1,"KS mismatch idx%0d edge%0d expected%0d",seen,edge_n,firstedge+seen*1259408);
  seen=seen+1;
 end
 if(rn&&dut.u_l1.cv[0]) begin
  // cv is a registered pin: this active-region observer sees the
  // value launched after the PREVIOUS edge, before the current NBA.
  if(mode==0 && edge_n-1!=firstedge+commands*1259408+4+8)$fatal(1,"actual firstcommand anchor mismatch edge%0d expected%0d",edge_n,firstedge+commands*1259408+4+8);
  commands=commands+1;
 end
 if(rn&&kd[53])begin
  if(kd[52:32]!==21'(1703+97*retired))$fatal(1,"retirement opaque token mismatch");
  retired=retired+1;
 end
end
task word(input[511:0] x);begin @(negedge ck);host={2'd0,x,1'b1};@(negedge ck);host=0;end endtask
task pw(input integer addr,input[27:0] value);reg[511:0] x;begin x=0;x[7:0]=8'h10;x[102:96]=7'(addr);x[59:32]=value;word(x);end endtask
initial begin
 if(!$value$plusargs("mode=%d",mode))mode=0;
 repeat(8)@(negedge ck);rn=1;repeat(20)@(negedge ck);
 d=0;d[7:0]=8'h11;d[39:32]=3;word(d);
 pw(0,(28'd3<<26)|(28'd3<<9));
 for(i=0;i<3;i=i+1)begin
  row={24'(i==0?13:0),24'(i==0?8:(i==1?16:20)),4'(i==0?0:(i==1?14:15)),24'd0};
  for(j=0;j<3;j=j+1)pw(i,{2'(j),row[26*j+:26]});
 end
 pw(0,(28'd3<<26)|(28'd1<<25)|(28'd3<<9));
 repeat(180)@(negedge ck);
 if(!dut.u_l1.u_iss.sealed)$fatal(1,"actual walker not sealed");
 d=0;d[7:0]=8'h19;d[39:8]=32'h218d375d;d[87:40]=48'd90000;word(d);
 @(negedge ck);d=0;d[7:0]=8'h17;d[39:8]=32'h218d375d;
 // Real explicit epoch and actual issuer phase sampled from this mechanism
 // fixture. Production must provide these from its pinned host programme.
 epoch=a.global_edge;delta=40+((4-(dut.u_l1.u_iss.phase_q&3))&3);d[87:40]=epoch;d[135:88]=epoch+delta;d[183:136]=epoch+delta+4+8;d[193:184]=37;
 d[195:194]=dut.u_l1.u_iss.phase_q;
 if(mode==4)d[87:40]=epoch+1;
 host={2'd0,d,1'b1};firstedge=edge_n+1+delta;
 @(negedge ck);host=0;
 for(i=0;i<6;i=i+1)begin
  @(negedge ck);incoming=desc(i);
  if(mode==1||mode==3)incoming=0;
  if(mode==2&&i==0)incoming[51:42]=38;
  @(negedge ck);incoming=0;
 end
 if(mode==3)begin repeat(40)@(negedge ck);incoming=desc(0);@(negedge ck);incoming=0;end
 if(mode!=0)begin repeat(100)@(negedge ck);if(fault==0)$fatal(1,"negative not caught mode%0d",mode);$display("KS6 NEGATIVE CAUGHT mode=%0d fault=%h",mode,fault);$finish;end else begin
 fork begin wait(done);end begin wait(fault!=0);$fatal(1,"positive adapterfault %h issue=%0d phase=%0d",fault,a.first_issue,a.expected_phase);end join_any disable fork;repeat(40)@(negedge ck);
 if(fault!=0||seen!=6||retired!=6||commands!=6||dut.u_l1.u_iss.fault)$fatal(1,"positive fault%h seen%0d retired%0d issuer%0d code%0d",fault,seen,retired,dut.u_l1.u_iss.fault,dut.u_l1.u_iss.fault_code);
 $display("KS6 HOST_WALKER PASS six real descriptors, exact q4 span, opaque token retirement");$finish;
end
end
initial begin #7600000;$fatal(1,"timeout");end
endmodule
