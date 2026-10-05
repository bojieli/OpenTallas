`timescale 1ns/1ps
// SPINE variant (2026-10-04): `dut` is ot_v41_rom_elem_q_pg_sp_w10 (SPINE = 1, gated stage clock spine; aon_clk = clk,
// the always-on island's branch of the same clock).  Otherwise identical to tb_signoff_rom_elem_pg_sp.
// Gate-level activity bench of the power-gated S81 element (tools/rom_stage_pg_power.py through
// tools/signoff_analysis.py activity, Icarus engine): `dut` is ot_v41_rom_elem_q_pg_w10 (the routed netlist, PG = 1),
// `ref_e` the RTL element ot_v41_rom_elem_q_w10 (always on) that paces the x beats and checks every output.
// One decode timeline, cycle-numbered from time 0 like the harness (one count per falling edge):
//   configuration written while the domain is off (shadow only) -> pre-wake -> token A (PG on)  [window ACTIVE]
//   -> sleep                                                                             [window PG_IDLE]
//   -> pre-wake -> token B (PG on) -> pg_en = 0: the domain stays on, element clock-gated   [window CG_IDLE]
//   -> token C (PG off).
// The bench prints "MARK <name> <cycle>" at every phase boundary and fails on any output mismatch.
module tb_signoff_rom_elem_pg_sp (input wire clk);
 localparam integer NSUB = 4;
 localparam integer SW_D = 8;            // header-ring segment enable -> ack (cycles); see the record for the basis
 localparam integer LEAD = 200;
 localparam integer P = 16000;
 reg rst_n=0, cfg_v=0, go=0, xs_v=0, pg_en=1;
 reg [4:0] cfg_a=0; reg [47:0] cfg_d=0;
 reg [7:0] xs_p=0; reg [2:0] xs_b=0, xs_pos=0;
 reg [255:0] q0=0, q1=0;
 reg sched_v=0; reg [23:0] sched_gap=0;
 wire [1:0] av,bv,ae,be; wire [63:0] ad,bd; wire [31:0] ar,br;
 wire [9:0] asg,bsg,an,bn; wire [5:0] ap,bp; wire ab,bb,af,bf;
 wire [NSUB-1:0] sw_en; reg [NSUB-1:0] sw_ack=0;
 wire pg_ready, pg_late, pg_fault;
 ot_v41_rom_elem_q_w10 #(.NB(2), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .INSTANCE("ref")) ref_e (.clk(clk), .rst_n(rst_n),
  .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_pos(xs_pos),
  .xs_sv(2'b11), .xs_q0(q0), .xs_e0(10'd127), .xs_q1(q1), .xs_e1(10'd126),
  .pv(av), .pval(ad), .prow(ar), .pseg(asg), .pnseg(an), .perr(ae), .ppos(ap), .busy(ab), .fault(af));
 ot_v41_rom_elem_q_pg_sp_w10 #(.NB(2), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .PG(1), .NSUB(NSUB), .SPINE(1)) dut (.clk(clk), .aon_clk(clk), .rst_n(rst_n),
  .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_pos(xs_pos),
  .xs_sv(2'b11), .xs_q0(q0), .xs_e0(10'd127), .xs_q1(q1), .xs_e1(10'd126),
  .pv(bv), .pval(bd), .prow(br), .pseg(bsg), .pnseg(bn), .perr(be), .ppos(bp), .busy(bb), .fault(bf),
  .pg_en(pg_en), .sched_v(sched_v), .sched_gap(sched_gap), .pg_lead(24'(LEAD)), .pg_bet(24'd64), .pg_idle(8'd160),
  .pg_step(16'd16), .pg_rst(8'd4), .pg_ack_to(16'd200), .sw_en(sw_en), .sw_ack(sw_ack), .pg_ready(pg_ready),
  .pg_late(pg_late), .pg_fault(pg_fault));

 // header-switch ring model: a segment's ack follows its enable after SW_D cycles on, 2 off
 genvar gs;
 for (gs = 0; gs < NSUB; gs = gs + 1) begin : g_sw
   integer c = 0;
   always @(posedge clk) begin
     if (sw_en[gs] != sw_ack[gs]) begin
       c = c + 1;
       if (c >= (sw_en[gs] ? SW_D : 2)) begin sw_ack[gs] <= sw_en[gs]; c = 0; end
     end else c = 0;
   end
 end

 integer cyc=0, rows=0, nonzero=0;
 always @(negedge clk) begin
   cyc=cyc+1;
   if (rst_n) begin
     if ({av,ab,af} !== {bv,bb,bf}) $fatal(1,"FATAL control mismatch cycle=%0d ref=%b dut=%b",cyc,{av,ab,af},{bv,bb,bf});
     for (integer m=0;m<2;m=m+1) if (av[m]) begin
       if ({ad[32*m+:32],ar[16*m+:16],asg[5*m+:5],an[5*m+:5],ae[m],ap[3*m+:3]} !==
           {bd[32*m+:32],br[16*m+:16],bsg[5*m+:5],bn[5*m+:5],be[m],bp[3*m+:3]})
         $fatal(1,"FATAL partial mismatch cycle=%0d macro=%0d ref=%h dut=%h",cyc,m,ad[32*m+:32],bd[32*m+:32]);
       rows=rows+1; if (ad[32*m+:32]!=0) nonzero=nonzero+1;
     end
     if (pg_late || pg_fault) $fatal(1,"FATAL schedule miss or ring fault cycle=%0d",cyc);
   end
 end

 // deterministic content-dependent ROM words (finite FP4 / FP8 codes), the same function as tb_v41_rom_elem_pg
 function automatic [273:0] romword(input [12:0] a);
   reg [127:0] w0, w1; reg [31:0] h;
   h = {19'd0, a} * 32'h9E3779B1 + 32'h7F4A7C15;
   w0 = {4{h ^ 32'h5bd1e995}} & {16{8'h77}};
   h = h * 32'h85EBCA6B + 32'd1;
   w1 = {4{h}} & {16{8'h77}};
   romword = {2'b0, 8'd120 + 8'(a[2:0]), w1, 8'd123 + 8'(a[4:3]), w0};
 endfunction
 function automatic [255:0] xword(input integer n, input integer s);
   reg [31:0] h; reg [255:0] w;
   h = n * 32'h27D4EB2F + s;
   for (integer i=0;i<8;i=i+1) begin h = h * 32'h165667B1 + 32'd7; w[32*i+:32] = h; end
   xword = w & {32{8'h77}};
 endfunction

 task automatic tick(input integer n); repeat(n) @(posedge clk); endtask
 task automatic cfg(input integer a,input [47:0] d);
   @(negedge clk); cfg_v=1; cfg_a=5'(a); cfg_d=d;
 endtask
 task automatic configure(input integer mode);
   integer nu,base; reg [47:0] d;
   for(integer c=0;c<8;c=c+1) begin
     d=48'(c+1) | (48'd1<<21) | (48'(mode!=1)<<26) | (48'd1<<27) | (48'd1<<28);
     cfg(c,d); cfg(17+c,48'(c+101));
     // class 7 idle: the element's second-macro segment-7 row register is never written (see the record)
     nu=(mode==0) ? ((c==0)?9:((c==3)?3:((c==6)?2:0))) : ((c==7)?0:1);
     base=(c==0)?252:(32*c);
     d=48'(nu!=0) | (48'(base)<<1) | (48'(nu)<<9) | (48'(c)<<16) | (48'(c)<<19);
     cfg(8+c,d);
   end
   cfg(16,48'(mode==0) | (48'(mode==0 ? 2 : 0)<<3));
   @(negedge clk); cfg_v=0;
 endtask
 integer nbeat=0;
 task automatic beat(input integer kind);
   @(negedge clk);
   xs_v=(kind!=4); xs_p=ref_e.u_e.n_pair; xs_b=ref_e.u_e.n_b; xs_pos=ref_e.u_e.n_pos;
   q0=xword(nbeat,1); q1=xword(nbeat,2); nbeat=nbeat+1;
   case(kind) 1: xs_p=xs_p+8'd1; 2: xs_b=xs_b+3'd1; 3: xs_pos=xs_pos+3'd1; endcase
   tick(1); @(negedge clk); xs_v=0;
   tick(12);
 endtask
 task automatic wait_until(input integer t); while (cyc < t) @(negedge clk); endtask
 task automatic token(input integer t_go, input integer gap, input [8*8-1:0] name);
   integer sent;
   wait_until(t_go - 1);
   @(negedge clk); go=1; sched_v=(gap > 0); sched_gap=24'(gap > 0 ? gap - 1 : 0);
   $display("MARK go_%0s %0d ready=%0d", name, cyc, pg_ready);
   @(negedge clk); go=0; sched_v=0; tick(4);
   sent=0;
   while(ref_e.u_e.n_run && sent<1000) begin
     beat(0); sent=sent+1;
   end
   while (ab || (|av)) @(negedge clk);
   $display("MARK end_%0s %0d", name, cyc);
 endtask
 integer tA, tB, tC;
 initial begin
   tick(4); @(negedge clk); rst_n=1;
   configure(1);                                     // the domain is off: shadow only
   tA = 3000; tB = tA + P; tC = tB + P;
   @(negedge clk); sched_v=1; sched_gap=24'(tA-cyc-1); @(negedge clk); sched_v=0;
   token(tA, P, "A");
   $display("MARK pg_idle_from %0d", cyc + 400);
   token(tB, 0, "B");
   @(negedge clk); pg_en=0;                          // gating off: the domain wakes and stays on, element ICG idle
   while (!pg_ready) @(negedge clk);
   $display("MARK cg_idle_from %0d", cyc + 400);
   token(tC, 0, "C");
   tick(200);
   if (rows < 30 || nonzero < 10) $fatal(1,"FATAL coverage rows=%0d nonzero=%0d", rows, nonzero);
   $display("PASS cycles=%0d rows=%0d nonzero=%0d", cyc, rows, nonzero);
   $finish;
 end
endmodule

module ot_rom_4096x274_m8 #(parameter INSTANCE="")(input wire clk,ce_in,input wire [11:0] addr_in,output reg [273:0] rd_out);
 always @(posedge clk) if(ce_in) rd_out <= tb_signoff_rom_elem_pg_sp.romword({1'b0,addr_in});
endmodule
