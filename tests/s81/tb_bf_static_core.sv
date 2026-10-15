`timescale 1ns/1ps
// Core control component gate only: real CFG, BF ingress FIFO and walkers.
// Numerical columns/native CFG7 production programmes are separate gates.
module tb_bf_static_core;
  reg clk=0; always #5 clk=~clk;
  reg rst=0,cv=0,go=0,bv=0,pi=0;
  reg [4:0] ca=0; reg [47:0] cd=0;
  reg [2:0] bb=0; reg [31:0] bu=0;
  reg [13:0] pa=0; reg [14:0] po=0; reg [3:0] pc=0;
  wire [6:0] issue,fault,iv; wire [13:0] addr[0:6];
  wire [15:0] tag[0:6];
  genvar m;
  for(m=0;m<7;m=m+1) begin:g
    ot_v41_bf_front_core #(.STATIC_PROGRAM(1),.NSEG(8),.NCH(16),.XF(8),.NB(2),
      .BF16(1),.QBF(2),.FAST(1),.PP(1),.QPIPE(1),.QTIMING_FIX(1),
      .QZ(1),.QY(1),.QX(10),.QZE(1),.TCG(1),.CG(1)) dut (
      .clk(clk),.rst_n_pin(rst),.cfg_v_pin(cv),.cfg_a_pin(ca),.cfg_d_pin(cd),
      .go_pin(go),.go_bf_pin(1'b1),
      .xs_v_pin(1'b0),.xs_p_pin(8'd0),.xs_b_pin(3'd0),.xs_sv_pin(2'd0),
      .xs_q0_pin(256'd0),.xs_q1_pin(256'd0),.xs_e0_pin(10'd0),.xs_e1_pin(10'd0),.xs_pos_pin(3'd0),
      // Mutant 1 drops real input beats; its issue calendar must still run.
      .xb_v_pin(bv && m!=1),.xb_pos_pin(3'd0),.xb_b_pin(bb),.xb_sv_pin(4'hf),.xb_u_pin(bu),.xb_d_pin(1024'h1234),
      .prog_issue_pin(pi),.prog_addr_pin(pa ^ (m==2 ? 14'd1:14'd0)),
      .prog_operand_pin(po ^ (m==3 ? 15'd1:15'd0)),
      .prog_segment_pin(3'd0),.prog_half_pin(1'b0),.prog_chain_pin(pc),
      .c_qy_bkf(2'd0),.c_issue(issue[m]),.c_a_ctr(addr[m]),.c_i1_v(iv[m]),.c_i1_t(tag[m]),.fault(fault[m]));
  end
  integer n=0,k,j,b;
  task tick; begin @(negedge clk); end endtask
  task cfg(input [4:0] a,input [47:0] d); begin cv=1;ca=a;cd=d;tick();end endtask
  always @(posedge clk) if(rst) begin
    if(issue !== {7{pi}}) $fatal(1,"calendar slipped");
    for(integer z=1;z<7;z=z+1) begin
      if(issue[z] && addr[z] !== addr[0]) $fatal(1,"fault rescheduled address");
      if(iv[z] !== iv[0]) $fatal(1,"fault shifted column ingress valid");
      if(iv[z] && tag[z] !== tag[0]) $fatal(1,"fault changed column ingress identity");
    end
    if(pi) begin
      if(addr[0] !== pa) $fatal(1,"wrong compiled address %d %d",addr[0],pa);
      n=n+1;
    end
  end
  initial begin
    repeat(3) tick();rst=1;repeat(4)tick();
    // A real 8-unit BF class, one segment per macro, all 8 block rounds.
    for(k=0;k<8;k=k+1) cfg(5'(k), (48'd1<<42)|(48'd1<<28)|(48'd1<<27)|48'(k));
    cfg(5'd8,(48'd1<<22)|(48'd8<<9)|48'd1);
    for(k=1;k<8;k=k+1) cfg(5'(8+k),48'd0);
    cfg(5'd16,48'd0);
    for(k=0;k<8;k=k+1) cfg(5'(17+k),48'(k+10));
    cv=0;repeat(8)tick();go=1;tick();go=0;repeat(8)tick();
    // Inject the checker's recurrence observation only; schedule must ignore it.
    force g[4].dut.hazard_r = 1'b1;
    force g[6].dut.pp_last_v = 1'b1;
    force g[6].dut.pp_last_b = 1'b0;
    for(b=0;b<8;b=b+1) begin
      bb=3'(b);bv=1;bu=32'h03020100;tick();bu=32'h07060504;tick();bv=0;
      repeat(6)tick();
      for(j=0;j<8;j=j+1) begin
        pi=1;pa=14'(8*b+j);po={1'b1,3'd0,3'(b),8'(j)};pc=4'(j);
        // Fault injection in captured identity storage, without changing data.
        g[5].dut.f_identity[g[5].dut.f_rd] = 15'd0;
        tick();
      end
      pi=0;
    end
    repeat(150)tick();
    if(n!=64) $fatal(1,"missing issues %d",n);
    if(fault !== 7'b1111110) $fatal(1,"fault qualification %b",fault);
    $display("PASS BF static core: 64 compiled issues; dropped ingress, wrong address, wrong operand, captured identity, forced recurrence and PP bank faults preserve issue/address/column-ingress timelines");
    $finish;
  end
endmodule
