`timescale 1ns/1ps
// QTIMING_FIX exactness bench (DS-V4.1 ROM q-pair element, 2026-10-03).
// ref = the pinned ot_v41_rom_elem_q_w10 (unchanged source); dut = ot_v41_rom_elem_q_qt_w10 with QTIMING_FIX = 1.
// Both at the routed parameters (NB 2, MTP 1, EARLY 1, FAST 1, PP 1).  Every cycle (both clock phases) the bench
// requires: every output bit identical (valid or not), the gated clock identical, and the walker / FIFO / issue state
// identical.  Built with +define+QT_CHECK the dut also checks each duplicated match copy and the clock-gate enable
// against the original expressions every cycle.  Stimulus: directed phases (sparse / all-8 / empty families, q
// advance, MTP restarts, 8-bit pair wrap, wrong pair/b/position, bubbles, mid-op reset) and a long random section
// (random configurations, random x data and timing, random go while the gate is closed / draining / open, x noise
// while idle, random resets).
module tb_dsrom_qtiming_exact;
 integer SEED = 1;
 parameter integer NRAND = 400;
 reg clk=0, rst_n=0, cfg_v=0, go=0, xs_v=0;
 reg [4:0] cfg_a=0; reg [47:0] cfg_d=0;
 reg [7:0] xs_p=0; reg [2:0] xs_b=0, xs_pos=0; reg [1:0] xs_sv=2'b11;
 reg [255:0] xs_q0=0, xs_q1=0; reg [9:0] xs_e0=10'd127, xs_e1=10'd127;
 always #0.5 clk=~clk;
 wire [1:0] av,bv,ae,be; wire [63:0] ad,bd; wire [31:0] ar,br;
 wire [9:0] asg,bsg,an,bn; wire [5:0] ap,bp; wire ab,bb,af,bf;
 ot_v41_rom_elem_q_w10 #(.NB(2), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .INSTANCE("r")) ref_dut (
  .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go),
  .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1),
  .xs_pos(xs_pos), .pv(av), .pval(ad), .prow(ar), .pseg(asg), .pnseg(an), .perr(ae), .ppos(ap), .busy(ab), .fault(af));
 ot_v41_rom_elem_q_qt_w10 #(.NB(2), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .QTIMING_FIX(1), .INSTANCE("d")) dut (
  .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go),
  .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1),
  .xs_pos(xs_pos), .pv(bv), .pval(bd), .prow(br), .pseg(bsg), .pnseg(bn), .perr(be), .ppos(bp), .busy(bb), .fault(bf));
 integer cyc=0, hits=0, issues=0, rows=0, nonzero=0, qadv=0, restarts=0, wraps=0, classes=0, rejected=0;
 integer gated_edges=0, closed_cycles=0, go_closed=0, go_drain=0, go_open=0, resets=0, gopen_ref=0;
 // the gated clock: identical at every half cycle
 always @(clk) if ($time > 0) begin
   #0.1;
   if (ref_dut.u_e.gclk !== dut.u_e.gclk) $fatal(1, "gated clock differs at %t", $time);
 end
 always @(posedge ref_dut.u_e.gclk) gated_edges = gated_edges + 1;
 always @(negedge clk) begin
   if (rst_n) cyc = cyc + 1;
   if ({av,ad,ar,asg,an,ae,ap,ab,af} !== {bv,bd,br,bsg,bn,be,bp,bb,bf}) $fatal(1, "output mismatch cycle=%0d", cyc);
   if (rst_n) begin
     if (!ref_dut.u_e.cg_en) closed_cycles = closed_cycles + 1;
     if ({ref_dut.u_e.hit_q,ref_dut.u_e.issue,ref_dut.u_e.n_run,ref_dut.u_e.n_q,ref_dut.u_e.n_b,ref_dut.u_e.n_c,
          ref_dut.u_e.n_j,ref_dut.u_e.n_pos,ref_dut.u_e.nA,ref_dut.u_e.nB,ref_dut.u_e.f_cnt,ref_dut.u_e.f_wr,
          ref_dut.u_e.f_rd,ref_dut.u_e.w_run,ref_dut.u_e.w_q,ref_dut.u_e.w_b,ref_dut.u_e.w_c,ref_dut.u_e.w_j,
          ref_dut.u_e.w_pos,ref_dut.u_e.a_ctr,ref_dut.u_e.fw_v,ref_dut.u_e.drain,ref_dut.u_e.cg_en} !==
         {dut.u_e.hit_q,dut.u_e.issue,dut.u_e.n_run,dut.u_e.n_q,dut.u_e.n_b,dut.u_e.n_c,
          dut.u_e.n_j,dut.u_e.n_pos,dut.u_e.nA,dut.u_e.nB,dut.u_e.f_cnt,dut.u_e.f_wr,
          dut.u_e.f_rd,dut.u_e.w_run,dut.u_e.w_q,dut.u_e.w_b,dut.u_e.w_c,dut.u_e.w_j,
          dut.u_e.w_pos,dut.u_e.a_ctr,dut.u_e.fw_v,dut.u_e.drain,dut.u_e.cg_en}) $fatal(1, "state divergence cycle=%0d", cyc);
     if (ref_dut.u_e.fw_v && {ref_dut.u_e.fw_q0,ref_dut.u_e.fw_q1,ref_dut.u_e.fw_e0,ref_dut.u_e.fw_e1} !==
                             {dut.u_e.fw_q0,dut.u_e.fw_q1,dut.u_e.fw_e0,dut.u_e.fw_e1}) $fatal(1, "capture data cycle=%0d", cyc);
     for (integer k=0;k<4;k=k+1)
       if ({ref_dut.u_e.f_q0[k],ref_dut.u_e.f_q1[k],ref_dut.u_e.f_e0[k],ref_dut.u_e.f_e1[k]} !==
           {dut.u_e.f_q0[k],dut.u_e.f_q1[k],dut.u_e.f_e0[k],dut.u_e.f_e1[k]}) $fatal(1, "fifo data cycle=%0d", cyc);
     for (integer m=0;m<2;m=m+1) if (av[m]) begin rows=rows+1; if (ad[32*m+:32]!=0) nonzero=nonzero+1; end
     if (ref_dut.u_e.hit_q) begin
       hits=hits+1; classes=classes | (1 << ref_dut.u_e.n_c);
       if (({1'b0,ref_dut.u_e.c_u0[ref_dut.u_e.n_c]} + {3'd0,ref_dut.u_e.n_q,ref_dut.u_e.n_j})>255) wraps=wraps+1;
     end
     if (ref_dut.u_e.issue) issues=issues+1;
     if (ref_dut.u_e.n_step && ref_dut.u_e.n_nx[12] && ref_dut.u_e.n_nx[11:9]!=ref_dut.u_e.n_q) qadv=qadv+1;
     if (ref_dut.u_e.n_rst) restarts=restarts+1;
     if (ref_dut.u_e.xs_v_e && !ref_dut.u_e.hit_q && ref_dut.u_e.n_run) rejected=rejected+1;
     if (go) begin
       if (ref_dut.u_e.walk_busy) go_open=go_open+1;
       else if (ref_dut.u_e.drain != 0) go_drain=go_drain+1;
       else go_closed=go_closed+1;
     end
   end
 end
 task automatic tick(input integer n); repeat(n) @(posedge clk); endtask
 task automatic cfg(input integer a,input [47:0] d);
   @(negedge clk); #0.01; cfg_v=1; cfg_a=5'(a); cfg_d=d;
 endtask
 task automatic rnd_x;
   for (integer i=0;i<8;i=i+1) begin xs_q0[32*i+:32]=$urandom; xs_q1[32*i+:32]=$urandom; end
   xs_e0=10'd100+10'($urandom%50); xs_e1=10'd100+10'($urandom%50);
 endtask
 // mode 0 sparse FP4 two sub-blocks (8-bit wrap), 1 all eight FP8 classes, 2 empty Q family, 3 random
 task automatic configure(input integer mode);
   integer nu,base,fp4,lo,hi,valid,plast,qlast; reg [47:0] d;
   plast = (mode==0) ? 2 : (mode==3 ? $urandom%3 : 0);
   qlast = 0;
   for(integer c=0;c<8;c=c+1) begin
     fp4 = (mode==3) ? $urandom%2 : (mode!=1);
     lo = (mode==3) ? $urandom%2 : 1; hi = (mode==3) ? $urandom%2 : 1;
     d=48'(c+1) | (48'(1+$urandom%3)<<16) | (48'd1<<21) | (48'(fp4)<<26) | (48'(lo)<<27) | (48'(hi)<<28)
       | (48'($urandom%8192)<<29);
     cfg(c,d); cfg(17+c, (mode==3 && $urandom%4==0) ? 48'h8000 : 48'(c+101));
     if (mode==0) nu=(c==0)?9:((c==3)?3:((c==7)?2:0));
     else if (mode==3) nu=($urandom%3==0) ? 0 : 1+$urandom%12;
     else nu=1;
     valid = (nu!=0);
     base=(mode==3) ? $urandom%256 : ((c==0)?252:(32*c));
     if (nu > 8 && qlast < 1) qlast = 1;
     d=48'(valid) | (48'(base)<<1) | (48'(nu)<<9) | (48'(c)<<16) | (48'(c)<<19) | (48'(mode==2)<<22);
     cfg(8+c,d);
   end
   if (mode==0) qlast=1;
   cfg(16, 48'(qlast) | (48'(plast)<<3) | (48'(2*($urandom%64))<<6));
   @(negedge clk); #0.01; cfg_v=0; tick(4);
 endtask
 // a beat for the walker's current need; kind 1/2/3 corrupt pair/b/position, 4 = invalid, 5 = random junk
 task automatic beat(input integer kind, input integer gap);
   @(negedge clk); #0.01;
   rnd_x;
   xs_v=(kind!=4); xs_p=ref_dut.u_e.n_pair; xs_b=ref_dut.u_e.n_b; xs_pos=ref_dut.u_e.n_pos;
   xs_sv = ($urandom%8==0) ? 2'($urandom) : 2'b11;
   case(kind)
     1: xs_p=xs_p+8'd1;
     2: xs_b=xs_b+3'd1;
     3: xs_pos=xs_pos+3'd1;
     5: begin xs_p=$urandom; xs_b=$urandom; xs_pos=$urandom%3; end
   endcase
   tick(1); @(negedge clk); #0.01; xs_v=0; rnd_x;
   tick(gap);
 endtask
 task automatic idle_noise(input integer n);
   for (integer i=0;i<n;i=i+1) begin
     @(negedge clk); #0.01; xs_v=($urandom%4==0); xs_p=$urandom; xs_b=$urandom; xs_pos=$urandom%3; rnd_x;
   end
   @(negedge clk); #0.01; xs_v=0;
 endtask
 task automatic phase(input integer mode, input integer rnd_timing);
   integer sent, k, g;
   configure(mode);
   @(negedge clk); #0.01; go=1; tick(1);
   @(negedge clk); #0.01; go=0; tick(rnd_timing ? $urandom%6 : 4);
   sent=0;
   while(ref_dut.u_e.n_run && sent<3000) begin
     g = rnd_timing ? 5+$urandom%12 : 12;
     if (rnd_timing) begin
       k = $urandom%10;
       if (k==0) beat(1+$urandom%5, 1+$urandom%4);
     end else if (sent%9==0) begin beat(1,12); beat(2,12); beat(3,12); beat(4,12); end
     beat(0, g); sent=sent+1;
   end
   if(sent==3000) $fatal(1,"walker failed to finish");
 endtask
 initial begin
   if (!$value$plusargs("seed=%d", SEED)) SEED = 1;
   void'($urandom(SEED));
   tick(4); @(negedge clk); #0.01; rst_n=1;
   // directed
   phase(0,0); tick(700); phase(1,0); tick(700); phase(2,0); tick(700); phase(0,0); tick(700);
   configure(0); @(negedge clk); #0.01; go=1; tick(1);
   @(negedge clk); #0.01; go=0; tick(4); beat(0,3);
   @(negedge clk); #0.01; rst_n=0; resets=resets+1; tick(4);
   @(negedge clk); #0.01; rst_n=1; phase(1,0); tick(300);
   // random: go lands with the gate closed (idle > DRAIN), mid-drain, or immediately after the walkers stop;
   // occasional back-to-back go, x noise while idle, and random resets
   for (integer r=0;r<NRAND;r=r+1) begin
     phase((r%5==0) ? $urandom%3 : 3, 1);
     case ($urandom%4)
       0: idle_noise(130 + $urandom%200);
       1: idle_noise($urandom%127);
       2: tick($urandom%3);
       3: begin tick(120 + $urandom%15); end
     endcase
     if ($urandom%25==0) begin
       @(negedge clk); #0.01; rst_n=0; resets=resets+1; tick(1+$urandom%3);
       @(negedge clk); #0.01; rst_n=1;
     end
     if ($urandom%15==0) begin                                 // go with no walk (empty family) / double go
       @(negedge clk); #0.01; go=1; tick(1+$urandom%2); @(negedge clk); #0.01; go=0; tick($urandom%140);
     end
   end
   tick(400);
   if(hits<2000 || issues<2000 || rows<200 || nonzero<100 || classes!=255 || wraps==0 || qadv==0 || restarts<4 ||
      rejected<50 || go_closed<20 || go_drain<20 || closed_cycles<1000 || resets<3)
     $fatal(1,"coverage incomplete h=%0d i=%0d r=%0d w=%0d q=%0d rst=%0d rej=%0d gc=%0d gd=%0d go=%0d cc=%0d rs=%0d",
            hits,issues,rows,wraps,qadv,restarts,rejected,go_closed,go_drain,go_open,closed_cycles,resets);
   $display("PASS seed=%0d cycles=%0d gated_edges=%0d closed_cycles=%0d hits=%0d issues=%0d rows=%0d nonzero=%0d classes=%0d wraps=%0d qadv=%0d restarts=%0d rejected=%0d go_closed=%0d go_drain=%0d go_open=%0d resets=%0d",
       SEED,cyc,gated_edges,closed_cycles,hits,issues,rows,nonzero,classes,wraps,qadv,restarts,rejected,go_closed,go_drain,go_open,resets);
   $finish;
 end
endmodule

// Address-hashed ROM fixture (both instances see the same words); synchronous read/hold like the behavioral ROM.
module ot_rom_4096x274_m8 #(parameter INSTANCE="")(
 input wire clk,ce_in,input wire [11:0] addr_in,output reg [273:0] rd_out);
 function automatic [273:0] word(input [11:0] a);
   reg [31:0] h; integer i;
   begin
     h = {20'd0, a} * 32'h9E3779B1 + 32'h7F4A7C15;
     for (i=0;i<9;i=i+1) begin word[32*i+:32] = h; h = h * 32'h85EBCA6B + 32'hC2B2AE35 + i; end
     word[273:256] = h[17:0];
     word[135:128] = 8'd120 + {5'd0, a[2:0]}; word[271:264] = 8'd124 + {5'd0, a[3:1]};
     word[263:256] = 8'd122 + {5'd0, a[4:2]};
   end
 endfunction
 always @(posedge clk) if(ce_in) rd_out <= word(addr_in);
endmodule
module ot_rom_8192x274_m8 #(parameter INSTANCE="")(
 input wire clk,ce_in,input wire [12:0] addr_in,output reg [273:0] rd_out);
 always @(posedge clk) if(ce_in) rd_out <= {2'b0,8'd127,{16{8'h22}},8'd127,{16{8'h22}}};
endmodule
