`timescale 1ns/1ps
// Two real head cores, two real off-die peer lanes. TEST HBC boot dates only;
// calibration measures nominal peer-frame->HBC-input age, then all three HBC
// records follow compiled dates500/504/510 with no readiness-driven timing.
module tb_s81hd_host_ctl_boot;
 reg ck=0,rn=0,start=0;always #0.4165 ck=~ck;
 wire[511:0]host_tx0,host_tx1,peer_tx0,peer_tx1;
 reg[1:0]pv=0;reg[552:0]pd0=0,pd1=0;
 wire[1:0]prv;wire[552:0]prd0,prd1;wire[3:0]pf0,pf1;
 wire[276:0]hostlane_tx;wire[275:0]hostlane_rx;
 ot_s81hd_mesh_lane p0(.ck(ck),.rst_n(rn),.chb(1'b1),.rx({2'b10,host_tx0}),.tx(peer_tx0),.tx_v(pv[0]),.tx_d(pd0),.rx_v(prv[0]),.rx_d(prd0),.flt(pf0));
 ot_s81hd_mesh_lane p1(.ck(ck),.rst_n(rn),.chb(1'b1),.rx({2'b10,host_tx1}),.tx(peer_tx1),.tx_v(pv[1]),.tx_d(pd1),.rx_v(prv[1]),.rx_d(prd1),.flt(pf1));
 ot_s81hd_host_ep_core #(.LOCAL_STAGE(1),.LOCAL_RANK(0),.PHASE_BOUND(1),.CLOCK_RESET_ID(64'h5381C7C0DE1021),
  .BOOT_HEADER_EDGE(48'd500),.BOOT_COMMIT_EDGE(48'd510))host(.ck(ck),.rst_n(rn),.start_i(start),
  .coll_i0({2'b10,peer_tx0}),.coll_i1({2'b10,peer_tx1}),.coll_o0(host_tx0),.coll_o1(host_tx1),.h_tx_i(hostlane_tx),.h_rx_o(hostlane_rx));
 wire[1103:0]ring;wire cf;wire[44:0]unitbus;wire[564:0]stream;wire[63:0]ma,mb,mn;
 ot_s81hd_ctl_core ctl(.ck(ck),.rst_n(rn),.start_i(start),.lep_fault_i(1'b0),.lw_i(11'd0),
  .lepk_i0(1104'd0),.lepk_o0(ring),.lepf_o0(cf),.unit_o0(unitbus),.ctrl_i0(32'd0),.x_o(stream),.b_i(565'd0),
  .h_tx_o(hostlane_tx),.h_rx_i(hostlane_rx),.a_tx_o(ma),.b7_tx_o(mb),.n_tx_o(mn),.a_rx_i(64'd0),.b7_rx_i(64'd0),.n_rx_i(64'd0));
 reg[559:0]records[0:15];integer c=0,cal_launch=-1,age=-1,received=0,csr_sent=0,ctx_cycle=-1,csr_cycle=-1;
 reg[63:0]data;reg[7:0]addr;string vec;
 localparam[511:0]TRACER=512'hABCD123456789FED;
 function automatic[552:0]hf(input[511:0]payload);hf={1'b1,24'd0,payload,12'd0,4'd7};endfunction
 function automatic[552:0]csr(input[7:0]a,input[63:0]d);
  reg[552:0]f;begin f=0;f[552]=1;f[3:0]=6;f[23:16]=a;f[87:24]=d;csr=f;end
 endfunction
 integer i;
 initial begin
  if(!$value$plusargs("VEC=%s",vec))$fatal(1,"VEC required");$readmemh({vec,"/m0.memh"},records);
  // Relocate TEST profile boot dates by480; payload CRC stays unchanged because
  // only the HBC LOAD/COMMIT envelope dates change. No production dates inferred.
  records[0][559:512]=500;records[0][289:242]=504;
  records[1][559:512]=504;records[2][559:512]=510;records[2][289:242]=510;
 end
 always@(negedge ck)begin
  c++;
  rn=(c>=8);pv=0;
  if(rn)begin
   if(host.u_hbc.boot_edge==60)begin pv[0]=1;pd0=hf(TRACER);cal_launch=int'(host.u_hbc.boot_edge);end
   if(host.from_prev[0]&&host.from_prev[532:21]==TRACER)begin
    if(cal_launch<0)$fatal(1,"unexpected tracer");age=int'(host.u_hbc.boot_edge)-cal_launch;
    $display("HEAD_HOST_AGE peer_frame_to_HBC_input=%0d edges boot%0d",age,host.u_hbc.boot_edge);
   end
   if(age>0)for(i=0;i<3;i++)begin
    if(int'(host.u_hbc.boot_edge)==int'(records[i][559:512])-age)begin pv[0]=1;pd0=hf(records[i][511:0]);end
   end
   if(host.from_prev[0]&&host.from_prev[532:21]!=TRACER)received++;
   if(host.ctxv&&ctx_cycle<0)ctx_cycle=c;
   if(host.u_hbc.boot_edge>=580&&host.u_hbc.boot_edge<=604&&host.u_hbc.boot_edge[1:0]==0)begin
    case(host.u_hbc.boot_edge)
     580:begin addr=0;data=9;end
     584:begin addr=1;data=0;end
     588:begin addr=4;data=17'h1abcd;end
     592:begin addr=9;data={32'd0,16'd10000,16'd20000};end
     596:begin addr=10;data=999;end
     600:begin addr=3;data=4;end
     default:begin addr=8;data=1;end
    endcase
    pv[1]=1;pd1=csr(addr,data);csr_sent++;
   end
   if(ctl.u_logic.c_iss_off==10000&&csr_cycle<0)csr_cycle=c;
   if(host.u_hbc.boot_edge==750)start=1;
   if(c>100&&((|pf0)||(|pf1)))$fatal(1,"peer physical fault %h/%h",pf0,pf1);
   if(c>100&&((|host.host_fault)||cf))$fatal(1,"host/ctl fault at%0d: host%h ctl%b hbc%h/%h",c,host.host_fault,cf,host.hbc_stage_fault,host.hbc_fault);
   if(host.u_hbc.boot_edge==850)begin
    if(age<=0||received!=3||!host.ctxv||csr_sent!=7||ctl.u_logic.c_plen!=9||ctl.u_logic.c_glen!=0||
      ctl.u_logic.c_rbase!=17'h1abcd||ctl.u_logic.c_iss_off!=10000||ctl.u_logic.c_iss_per!=20000||ctl.u_logic.c_merge_dl!=999||!ctl.u_logic.c_run||!start)
      $fatal(1,"two-core boot/config mismatch ctx%b received%0d csr%0d off%0d per%0d",host.ctxv,received,csr_sent,ctl.u_logic.c_iss_off,ctl.u_logic.c_iss_per);
    $display("HEAD_HOST_CTL_BOOT PASS realHBC3records realCSR7 context_cycle%0d first_issue_CSR_cycle%0d peer_HBC_age%0d START850_before_first_issue",ctx_cycle,csr_cycle,age);$finish;
   end
  end
  if(c>2000)$fatal(1,"no test-profile progress age%0d boot%0d",age,host.u_hbc.boot_edge);
 end
endmodule
