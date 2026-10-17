`timescale 1ns/1ps
module tb_seq_hf;
 reg ck=0;always #5 ck=~ck;
 reg rn=0;reg[84:0]cmd=0;reg[127:0]cv=0;reg[1151:0]ca=0;reg[511:0]cm=0;
 reg[31:0]rv=0;reg[447:0]rr=0;reg[3:0]xa=0;
 wire[117:0]gold,dut,compat;integer t,n,checks=0,seen=0,seed=1;
 dsfd_vm_seq_tile_ref3 ref3(.ck(ck),.rst(rn),.c_cmd(cmd),.c_done(gold[117:109]),.c_st(gold[108:107]),
 .o_cv(cv),.o_ca(ca),.o_cm(cm),.o_rv(rv),.o_rr(rr),
 .t_inp_su(gold[106]),.t_inp_hc(gold[105]),.nf_v(gold[104]),.nf_d(gold[103:20]),
 .larm_v(gold[19]),.larm_g(gold[18:15]),.larm_base(gold[14:1]),
 .pqx_chk(8'd0),.read_fault(8'd0),.edge_f(3'd0),.x_hdr(9'd0),
 .x_al({(xa[3]|xa[2]),xa[1:0]}),.w_flt(1'b0),.m_flt(40'd0),.l_flt(3'd0),.r_flt(1'b0),.vm_fault(gold[0]));
 dsfd_vm_seq_tile compat3(.ck(ck),.rst(rn),.c_cmd(cmd),.c_done(compat[117:109]),.c_st(compat[108:107]),
 .o_cv(cv),.o_ca(ca),.o_cm(cm),.o_rv(rv),.o_rr(rr),
 .t_inp_su(compat[106]),.t_inp_hc(compat[105]),.nf_v(compat[104]),.nf_d(compat[103:20]),
 .larm_v(compat[19]),.larm_g(compat[18:15]),.larm_base(compat[14:1]),
 .pqx_chk(8'd0),.read_fault(8'd0),.edge_f(3'd0),.x_hdr(9'd0),
 .x_al({(xa[3]|xa[2]),xa[1:0]}),.w_flt(1'b0),.m_flt(40'd0),.l_flt(3'd0),.r_flt(1'b0),.vm_fault(compat[0]));
 dsfd_vm_seq_tile #(.X_AL_WIDTH(4)) u_dut(.ck(ck),.rst(rn),.c_cmd(cmd),.c_done(dut[117:109]),.c_st(dut[108:107]),
 .o_cv(cv),.o_ca(ca),.o_cm(cm),.o_rv(rv),.o_rr(rr),
 .t_inp_su(dut[106]),.t_inp_hc(dut[105]),.nf_v(dut[104]),.nf_d(dut[103:20]),
 .larm_v(dut[19]),.larm_g(dut[18:15]),.larm_base(dut[14:1]),
 .pqx_chk(8'd0),.read_fault(8'd0),.edge_f(3'd0),.x_hdr(9'd0),
 .x_al(xa),.w_flt(1'b0),.m_flt(40'd0),.l_flt(3'd0),.r_flt(1'b0),.vm_fault(dut[0]));

 task tick;
 begin @(posedge ck);#1;
   if(gold!==compat)$fatal(1,"SEQ_HF default3 differs t%0d n%0d",t,n);
   if(gold!==dut)$fatal(1,"SEQ_HF mismatch t%0d n%0d gold%h dut%h",t,n,gold,dut);
   checks=checks+1;if(dut[0])seen=seen+1;
 end endtask
 initial begin
  if($value$plusargs("seed=%d",seed))begin end
  // Four independent fault pins, each at eight offsets; complete reset and all outputs compared every edge.
  for(t=0;t<32;t=t+1)begin
   for(n=0;n<40;n=n+1)begin
    @(negedge ck);rn=(n>=4);xa=0;
    if(n>=12+(t%8)&&n<15+(t%8))xa=4'b1<<(t/8);
    tick;
   end
  end
  // Declared native command/completion ports exercise identical sequencer behavior too.
  for(t=32;t<36;t=t+1)begin
   for(n=0;n<200;n=n+1)begin
    @(negedge ck);rn=(n>=4);xa=0;cmd=0;cv=0;rv=0;
    if(n>8)begin
     cmd[84]=(n%17==0);cmd[6:0]=$random(seed);cmd[30:7]=$random(seed);
     cmd[51:31]=$random(seed);cmd[72:52]=$random(seed);cmd[83:73]=$random(seed);
     cv={4{$random(seed)}};rv=$random(seed);
     ca={36{$random(seed)}};cm={16{$random(seed)}};rr={14{$random(seed)}};
    end
    tick;
   end
  end
  if(seen<32)$fatal(1,"fault witnesses absent %0d",seen);
  $display("SEQ_HF PASS checks=%0d fault_edges=%0d",checks,seen);$finish;
 end
endmodule
