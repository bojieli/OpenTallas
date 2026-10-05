`timescale 1ns/1ps
// Full arithmetic remains in both instances; only FRONT_PAR differs.
module tb_w10_frontend_main_exact;
 parameter integer FAST=1, PP=1;
 reg clk=0, rst_n=0, cfg_v=0, go=0, go_bf=0, xs_v=0;
 reg [4:0] cfg_a=0; reg [47:0] cfg_d=0;
 reg [7:0] xs_p=0; reg [2:0] xs_b=0, xs_pos=0;
 always #0.5 clk=~clk;
 wire [1:0] av,bv,ae,be; wire [63:0] ad,bd; wire [31:0] ar,br;
 wire [9:0] asg,bsg,an,bn; wire [5:0] ap,bp; wire ab,bb,af,bf;
 ot_v41_rom_elem_w10 #(.NB(2), .BF16(1), .MTP(1), .EARLY(1), .FAST(FAST), .PP(PP),
 .FRONT_PAR(0), .XF(8), .INSTANCE("ref_dut")) ref_dut ( .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_bf(go_bf),
 .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_pos(xs_pos), .xs_sv(2'b11),
 .xs_q0({32{8'h22}}), .xs_e0(10'd127), .xs_q1({32{8'h24}}), .xs_e1(10'd127),
 .xb_v(1'b0), .xb_b(3'd0), .xb_pos(3'd0), .xb_sv(4'd0), .xb_u(32'd0), .xb_d(1024'd0),
 .pv(av), .pval(ad), .prow(ar), .pseg(asg), .pnseg(an), .perr(ae),
 .ppos(ap), .busy(ab), .fault(af));
 ot_v41_rom_elem_w10 #(.NB(2), .BF16(1), .MTP(1), .EARLY(1), .FAST(FAST), .PP(PP),
 .FRONT_PAR(1), .XF(8), .INSTANCE("dut")) dut ( .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_bf(go_bf),
 .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_pos(xs_pos), .xs_sv(2'b11),
 .xs_q0({32{8'h22}}), .xs_e0(10'd127), .xs_q1({32{8'h24}}), .xs_e1(10'd127),
 .xb_v(1'b0), .xb_b(3'd0), .xb_pos(3'd0), .xb_sv(4'd0), .xb_u(32'd0), .xb_d(1024'd0),
 .pv(bv), .pval(bd), .prow(br), .pseg(bsg), .pnseg(bn), .perr(be),
 .ppos(bp), .busy(bb), .fault(bf));
 integer cyc=0, hits=0, issues=0, rows=0, nonzero=0, qadv=0, restarts=0, wraps=0;
 integer classes=0, rejected=0;
 always @(negedge clk) if (rst_n) begin
   cyc=cyc+1;
   if ({av,ab,af} !== {bv,bb,bf}) $fatal(1,"public control cycle=%0d",cyc);
   for (integer m=0;m<2;m=m+1) if (av[m]) begin
     if ({ad[32*m+:32],ar[16*m+:16],asg[5*m+:5],an[5*m+:5],ae[m],ap[3*m+:3]} !==
         {bd[32*m+:32],br[16*m+:16],bsg[5*m+:5],bn[5*m+:5],be[m],bp[3*m+:3]})
       $fatal(1,"partial mismatch cycle=%0d macro=%0d",cyc,m);
     rows=rows+1; if (ad[32*m+:32]!=0) nonzero=nonzero+1;
   end
   if ({ref_dut.hit_q,ref_dut.issue,ref_dut.n_run,ref_dut.n_q,ref_dut.n_b,ref_dut.n_c,
        ref_dut.n_j,ref_dut.n_pos,ref_dut.nA,ref_dut.nB,ref_dut.f_cnt,ref_dut.f_wr,ref_dut.f_rd,
        ref_dut.w_run,ref_dut.w_q,ref_dut.w_b,ref_dut.w_c,ref_dut.w_j,ref_dut.w_pos,
        ref_dut.a_ctr,ref_dut.fw_v,ref_dut.n_rst} !==
       {dut.hit_q,dut.issue,dut.n_run,dut.n_q,dut.n_b,dut.n_c,dut.n_j,dut.n_pos,dut.nA,dut.nB,
        dut.f_cnt,dut.f_wr,dut.f_rd,dut.w_run,dut.w_q,dut.w_b,dut.w_c,dut.w_j,dut.w_pos,
        dut.a_ctr,dut.fw_v,dut.n_rst}) $fatal(1,"frontend divergence cycle=%0d",cyc);
   if(ref_dut.hit_q) begin
     hits=hits+1; classes=classes | (1 << ref_dut.n_c);
     if (({1'b0,ref_dut.c_u0[ref_dut.n_c]} + {3'd0,ref_dut.n_q,ref_dut.n_j})>255) wraps=wraps+1;
   end
   if(ref_dut.issue) issues=issues+1;
   if(ref_dut.n_step && ref_dut.n_nx[12] && ref_dut.n_nx[11:9]!=ref_dut.n_q) qadv=qadv+1;
   if(ref_dut.n_rst) restarts=restarts+1;
   if(ref_dut.xs_v_e && !ref_dut.hit_q && ref_dut.n_run) rejected=rejected+1;
   // Check captured payload and all FIFO entries: equivalence must cover data,
   // not just a match signal (including cycles with no public partial yet).
   if(ref_dut.fw_v && {ref_dut.fw_q0,ref_dut.fw_q1,ref_dut.fw_e0,ref_dut.fw_e1} !==
      {dut.fw_q0,dut.fw_q1,dut.fw_e0,dut.fw_e1}) $fatal(1,"capture data");
   for(integer k=0;k<8;k=k+1)
     if ({ref_dut.f_q0[k],ref_dut.f_q1[k],ref_dut.f_e0[k],ref_dut.f_e1[k]} !==
         {dut.f_q0[k],dut.f_q1[k],dut.f_e0[k],dut.f_e1[k]}) $fatal(1,"fifo data");
 end
 task automatic tick(input integer n); repeat(n) @(posedge clk); endtask
 task automatic cfg(input integer a,input [47:0] d);
   @(negedge clk); #0.01; cfg_v=1; cfg_a=5'(a); cfg_d=d;
 endtask
 task automatic configure(input integer mode);
   integer nu,base; reg [47:0] d;
   for(integer c=0;c<8;c=c+1) begin
     // One segment per class. mode 0: sparse uneven two-subblock FP4;
     // mode 1: all eight FP8 classes; mode 2: empty Q family (BF-only).
     d=48'(c+1) | (48'd1<<21) | (48'(mode!=1)<<26) | (48'd1<<27) | (48'd1<<28);
     cfg(c,d); cfg(17+c,48'(c+101));
     nu=(mode==0) ? ((c==0)?9:((c==3)?3:((c==7)?2:0))) : 1;
     base=(c==0)?252:(32*c);
     d=48'(nu!=0) | (48'(base)<<1) | (48'(nu)<<9) | (48'(c)<<16) | (48'(c)<<19) | (48'(mode==2)<<22);
     cfg(8+c,d);
   end
   cfg(16,48'(mode==0) | (48'(mode==0 ? 2 : 0)<<3));
   @(negedge clk); #0.01; cfg_v=0; tick(4);
 endtask
 task automatic beat(input integer kind);
   @(negedge clk); #0.01;
   xs_v=(kind!=4); xs_p=ref_dut.n_pair; xs_b=ref_dut.n_b; xs_pos=ref_dut.n_pos;
   case(kind)
     1: xs_p=xs_p+8'd1;
     2: xs_b=xs_b+3'd1;
     3: xs_pos=xs_pos+3'd1;
   endcase
   tick(1); @(negedge clk); #0.01; xs_v=0;
   tick(12); // more than chain latency; legal round spacing, no FIFO overflow
 endtask
 task automatic phase(input integer mode);
   integer sent;
   configure(mode);
   @(negedge clk); #0.01; go=1; tick(1);
   @(negedge clk); #0.01; go=0; tick(4);
   sent=0;
   while(ref_dut.n_run && sent<1000) begin
     if(sent%9==0) begin beat(1); beat(2); beat(3); beat(4); end
     beat(0); sent=sent+1;
   end
   if(sent==1000) $fatal(1,"walker failed to finish");
   tick(700);
   if(ab || bb || af || bf) $fatal(1,"phase drain/fault mode=%0d fault=%0d",mode,af);
   $display("PHASE mode=%0d sent=%0d rows=%0d",mode,sent,rows);
 endtask
 initial begin
   tick(4); @(negedge clk); #0.01; rst_n=1;
   phase(0); phase(1); phase(2); phase(0);
   // Interrupted operation reset, then a fresh configured phase.
   configure(0); @(negedge clk); #0.01; go=1; tick(1);
   @(negedge clk); #0.01; go=0; tick(4); beat(0);
   @(negedge clk); #0.01; rst_n=0; tick(4);
   @(negedge clk); #0.01; rst_n=1; phase(1);
   if(hits<600 || issues<600 || rows<20 || nonzero<20 || classes!=255 ||
      wraps==0 || qadv==0 || restarts<4 || rejected<20) $fatal(1,"coverage incomplete h=%0d i=%0d r=%0d w=%0d q=%0d rst=%0d",hits,issues,rows,wraps,qadv,restarts);
   $display("PASS cycles=%0d hits=%0d issues=%0d rows=%0d nonzero=%0d classes=%0d wraps=%0d qadv=%0d restarts=%0d rejected=%0d",
       cyc,hits,issues,rows,nonzero,classes,wraps,qadv,restarts,rejected);
   $finish;
 end
endmodule

// Deterministic nonzero finite FP4/FP8 fixture. Same words in both instances;
// synchronous read/hold protocol matches the behavioral ROM, never synthesis.
module ot_rom_4096x274_m8 #(parameter INSTANCE="")(
 input wire clk,ce_in,input wire [11:0] addr_in,output reg [273:0] rd_out);
 always @(posedge clk) if(ce_in) rd_out <= {2'b0,8'd127,{16{8'h22}},8'd127,{16{8'h22}}};
endmodule
module ot_rom_8192x274_m8 #(parameter INSTANCE="")(
 input wire clk,ce_in,input wire [12:0] addr_in,output reg [273:0] rd_out);
 always @(posedge clk) if(ce_in) rd_out <= {2'b0,8'd127,{16{8'h22}},8'd127,{16{8'h22}}};
endmodule
