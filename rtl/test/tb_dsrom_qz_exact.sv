`timescale 1ns/1ps
// QZ exactness bench (DS-V4.1 ROM q-pair element, 2026-10-04): tb_dsrom_qpipe_exact with dut = ot_v41_rom_elem_q_qz_w10
// (QZ = 1 by default: zero added cycles over QPIPE, so L is unchanged) and a ROM fixture whose two banks of a macro
// return DIFFERENT words for one address (the qpipe fixture returned the same word from both banks, so a wrong bank
// select or capture enable was invisible).  Built with QP_CHECK the dut also asserts its registered gate enable.
// Original description:
// QPIPE exactness bench (DS-V4.1 ROM q-pair element, 2026-10-03).
// ref = the pinned ot_v41_rom_elem_q_w10 (unchanged source); dut = ot_v41_rom_elem_q_qp_w10 with QTIMING_FIX = 1 and
// QPIPE = 1, both at the routed parameters (NB 2, MTP 1, EARLY 1, FAST 1, PP 1).  Every cycle the bench requires every
// dut valid, busy and fault bit, and every data field under its valid, to equal the ref's L cycles earlier, L = QP_XS + QP_CAP + QP_P1, and the
// dut's walker / FIFO / issue / drain state to equal the ref's (QP_XS) cycles earlier; only the L + 1 cycles after a
// reset assertion are exempt (the dut's reset asserts asynchronously, the ref's shifted copy has not reset yet).
// QP_XS = 0: the dut gets go, the configuration and reset one cycle earlier than the ref (the spine issuing them
// early) and the beats at the same time.  Built with +define+QP_CHECK (and QT_CHECK) the dut also checks its
// segment-tree local decisions against the global ones every cycle.  Stimulus as tb_dsrom_qtiming_exact.
module tb_dsrom_qz_exact;
 integer SEED = 1;
 parameter integer NRAND = 400;
 parameter integer QP = 1, XS = 1, CAP = 0, P1 = 1, CSAM = 10;   // QP = 0: the copy's default (no shift)
 parameter integer QZ = 1;                                         // QZ = 0: the qp circuit
 localparam integer QK = QP != 0 ? CAP + P1 : 0;
 localparam integer L = QP != 0 ? XS + QK : 0;
 localparam integer FS = QP != 0 ? XS : 0;    // front-end state shift
 reg clk=0, rst_n=0, cfg_v=0, go=0, xs_v=0;
 reg [4:0] cfg_a=0; reg [47:0] cfg_d=0;
 reg [7:0] xs_p=0; reg [2:0] xs_b=0, xs_pos=0; reg [1:0] xs_sv=2'b11;
 reg [255:0] xs_q0=0, xs_q1=0; reg [9:0] xs_e0=10'd127, xs_e1=10'd127;
 always #0.5 clk=~clk;
 // XS = 0: the ref sees go / configuration / reset one cycle after the dut
 reg r_rst_n=0, r_go=0, r_cfg_v=0; reg [4:0] r_cfg_a=0; reg [47:0] r_cfg_d=0;
 always @(posedge clk) begin r_rst_n <= rst_n; r_go <= go; r_cfg_v <= cfg_v; r_cfg_a <= cfg_a; r_cfg_d <= cfg_d; end
 wire rfx = XS != 0 || QP == 0;
 wire rf_rst_n = rfx ? rst_n : r_rst_n;
 wire rf_go = rfx ? go : r_go;
 wire rf_cfg_v = rfx ? cfg_v : r_cfg_v;
 wire [4:0] rf_cfg_a = rfx ? cfg_a : r_cfg_a;
 wire [47:0] rf_cfg_d = rfx ? cfg_d : r_cfg_d;
 wire [1:0] av,bv,ae,be; wire [63:0] ad,bd; wire [31:0] ar,br;
 wire [9:0] asg,bsg,an,bn; wire [5:0] ap,bp; wire ab,bb,af,bf;
 ot_v41_rom_elem_q_w10 #(.NB(2), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .INSTANCE("r")) ref_dut (
  .clk(clk), .rst_n(rf_rst_n), .cfg_v(rf_cfg_v), .cfg_a(rf_cfg_a), .cfg_d(rf_cfg_d), .go(rf_go),
  .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1),
  .xs_pos(xs_pos), .pv(av), .pval(ad), .prow(ar), .pseg(asg), .pnseg(an), .perr(ae), .ppos(ap), .busy(ab), .fault(af));
 ot_v41_rom_elem_q_qz_w10 #(.QZ(QZ), .NB(2), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .QTIMING_FIX(1), .QPIPE(QP), .QP_XS(XS),
  .QP_CAP(CAP), .QP_P1(P1), .QP_CSAM(CSAM), .INSTANCE("d")) dut (
  .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go),
  .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1),
  .xs_pos(xs_pos), .pv(bv), .pval(bd), .prow(br), .pseg(bsg), .pnseg(bn), .perr(be), .ppos(bp), .busy(bb), .fault(bf));
 integer cyc=0, hits=0, issues=0, rows=0, nonzero=0, qadv=0, restarts=0, wraps=0, classes=0, rejected=0;
 integer gated_edges=0, closed_cycles=0, go_closed=0, go_drain=0, go_open=0, resets=0, compared=0, exempt=0;
 integer tcyc=0, last_assert=-1000;
 localparam integer OW = 2+64+32+10+10+2+6+1+1;
 localparam integer SWD = 1+1+1+3+3+3+3+3+48+48+3+2+2+1+3+3+3+3+3+14+1+8;
 reg [OW-1:0] oh [0:31];
 reg [SWD-1:0] sh [0:31];
 wire [OW-1:0] ro = {av,ad,ar,asg,an,ae,ap,ab,af};
 wire [OW-1:0] dov = {bv,bd,br,bsg,bn,be,bp,bb,bf};
 wire [SWD-1:0] rs = {ref_dut.u_e.hit_q,ref_dut.u_e.issue,ref_dut.u_e.n_run,ref_dut.u_e.n_q,ref_dut.u_e.n_b,ref_dut.u_e.n_c,
          ref_dut.u_e.n_j,ref_dut.u_e.n_pos,ref_dut.u_e.nA,ref_dut.u_e.nB,ref_dut.u_e.f_cnt,ref_dut.u_e.f_wr,
          ref_dut.u_e.f_rd,ref_dut.u_e.w_run,ref_dut.u_e.w_q,ref_dut.u_e.w_b,ref_dut.u_e.w_c,ref_dut.u_e.w_j,
          ref_dut.u_e.w_pos,ref_dut.u_e.a_ctr,ref_dut.u_e.fw_v,ref_dut.u_e.drain};
 wire [SWD-1:0] ds = {dut.u_e.hit_q,dut.u_e.issue,dut.u_e.n_run,dut.u_e.n_q,dut.u_e.n_b,dut.u_e.n_c,
          dut.u_e.n_j,dut.u_e.n_pos,dut.u_e.nA,dut.u_e.nB,dut.u_e.f_cnt,dut.u_e.f_wr,
          dut.u_e.f_rd,dut.u_e.w_run,dut.u_e.w_q,dut.u_e.w_b,dut.u_e.w_c,dut.u_e.w_j,
          dut.u_e.w_pos,dut.u_e.a_ctr,dut.u_e.fw_v,dut.u_e.drain};
 // pv, busy and fault every cycle; each macro's data fields (value, row, segment, segments, error, position)
 // whenever its pv is set.  Data fields under pv = 0 are not part of the interface: the output registers sample
 // the configuration on every gated edge, and the pipelined element's gate is open QK cycles longer.
 function automatic bit oeq(input [OW-1:0] d, input [OW-1:0] r);
   reg [1:0] dv, rv; reg [63:0] dd, rd; reg [31:0] dr, rr; reg [9:0] dsg, rsg, dn, rn; reg [1:0] de, re; reg [5:0] dp, rp;
   reg db, rb, df, rf;
   {dv,dd,dr,dsg,dn,de,dp,db,df} = d; {rv,rd,rr,rsg,rn,re,rp,rb,rf} = r;
   oeq = (dv === rv) && (db === rb) && (df === rf);
   for (int m = 0; m < 2; m++) if (rv[m])
     oeq = oeq && dd[32*m +: 32] === rd[32*m +: 32] && dr[16*m +: 16] === rr[16*m +: 16] && dsg[5*m +: 5] === rsg[5*m +: 5]
               && dn[5*m +: 5] === rn[5*m +: 5] && de[m] === re[m] && dp[3*m +: 3] === rp[3*m +: 3];
 endfunction
 always @(posedge ref_dut.u_e.gclk) gated_edges = gated_edges + 1;
 integer dbg_lo = -1, dbg_hi = -1;
 always @(negedge clk) if (tcyc >= dbg_lo && tcyc <= dbg_hi)
   $display("DBG2 %0d R pv %b busy %b drain %0d cg %b tv %b%b qv %b%b | D pv %b busy %b drain %0d cg %b cgq %b tv %b%b qv %b%b fault %b/%b",
     tcyc, av, ab, ref_dut.u_e.drain, ref_dut.u_e.cg_en, ref_dut.u_e.g_mac[1].t_v, ref_dut.u_e.g_mac[0].t_v,
     ref_dut.u_e.g_mac[1].q_v, ref_dut.u_e.g_mac[0].q_v,
     bv, bb, dut.u_e.drain, dut.u_e.cg_en, dut.u_e.cg_en_q, dut.u_e.g_mac[1].t_v, dut.u_e.g_mac[0].t_v,
     dut.u_e.g_mac[1].q_v, dut.u_e.g_mac[0].q_v, af, bf);
 initial begin void'($value$plusargs("dbglo=%d", dbg_lo)); void'($value$plusargs("dbghi=%d", dbg_hi)); end
 always @(negedge clk) if (tcyc >= dbg_lo && tcyc <= dbg_hi)
   $display("DBG %0d rst %b/%b go %b | R cg %b iss %b wrun %b fcnt %0d haz %b ppb %b actr %h hit %b xv %b | D cg %b iss %b wrun %b fcnt %0d haz %b ppb %b actr %h hit %b xv %b",
     tcyc, rf_rst_n, rst_n, go, ref_dut.u_e.cg_en, ref_dut.u_e.issue, ref_dut.u_e.w_run, ref_dut.u_e.f_cnt, ref_dut.u_e.hazard,
     ref_dut.u_e.pp_block, ref_dut.u_e.a_ctr, ref_dut.u_e.hit_q, ref_dut.u_e.xs_v_e,
     dut.u_e.cg_en_q, dut.u_e.issue, dut.u_e.w_run, dut.u_e.f_cnt, dut.u_e.hazard, dut.u_e.pp_block, dut.u_e.a_ctr, dut.u_e.hit_q, dut.u_e.xs_v_e);
 // walker registers without a reset (a_ctr, w_j, ...) are reloaded by the next go; after a reset the shifted
 // copies may differ until then, so the state comparison resumes 2 cycles after the dut's next go_e
 integer st_ex = 0, st_go = -1;
 always @(negedge rst_n) begin last_assert = tcyc; st_ex = 1; st_go = -1; end
 always @(negedge clk) if (st_ex && rst_n && dut.u_e.go_e && st_go < 0) st_go = tcyc;
 always @(negedge clk) begin
   tcyc = tcyc + 1;
   if (rst_n) cyc = cyc + 1;
   oh[tcyc % 32] = ro; sh[tcyc % 32] = rs;
   if (tcyc > L + 2 && tcyc - last_assert > L + 1) begin
     if (!oeq(dov, oh[(tcyc - L) % 32])) $fatal(1, "output mismatch cycle=%0d (dut %h, ref L=%0d earlier %h)", tcyc, dov, L, oh[(tcyc - L) % 32]);
     if (st_ex && st_go >= 0 && tcyc > st_go + 2) st_ex = 0;
     if (!st_ex && ds !== sh[(tcyc - FS) % 32]) $fatal(1, "state divergence cycle=%0d dut %h ref %h", tcyc, ds, sh[(tcyc - FS) % 32]);
     compared = compared + 1;
   end else exempt = exempt + 1;
   if (rf_rst_n) begin
     if (!ref_dut.u_e.cg_en) closed_cycles = closed_cycles + 1;
     for (integer m=0;m<2;m=m+1) if (av[m]) begin rows=rows+1; if (ad[32*m+:32]!=0) nonzero=nonzero+1; end
     if (ref_dut.u_e.hit_q) begin
       hits=hits+1; classes=classes | (1 << ref_dut.u_e.n_c);
       if (({1'b0,ref_dut.u_e.c_u0[ref_dut.u_e.n_c]} + {3'd0,ref_dut.u_e.n_q,ref_dut.u_e.n_j})>255) wraps=wraps+1;
     end
     if (ref_dut.u_e.issue) issues=issues+1;
     if (ref_dut.u_e.n_step && ref_dut.u_e.n_nx[12] && ref_dut.u_e.n_nx[11:9]!=ref_dut.u_e.n_q) qadv=qadv+1;
     if (ref_dut.u_e.n_rst) restarts=restarts+1;
     if (ref_dut.u_e.xs_v_e && !ref_dut.u_e.hit_q && ref_dut.u_e.n_run) rejected=rejected+1;
     if (rf_go) begin
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
   $display("QZ=%0d", QZ);
   $display("PASS QP=%0d XS=%0d CAP=%0d P1=%0d L=%0d compared=%0d exempt=%0d seed=%0d cycles=%0d gated_edges=%0d closed_cycles=%0d hits=%0d issues=%0d rows=%0d nonzero=%0d classes=%0d wraps=%0d qadv=%0d restarts=%0d rejected=%0d go_closed=%0d go_drain=%0d go_open=%0d resets=%0d",
       QP,XS,CAP,P1,L,compared,exempt,SEED,cyc,gated_edges,closed_cycles,hits,issues,rows,nonzero,classes,wraps,qadv,restarts,rejected,go_closed,go_drain,go_open,resets);
   $finish;
 end
endmodule


// Address-hashed ROM fixture (ref and dut see the same words); synchronous read/hold like the behavioral ROM.  The
// instance name ends in the bank ("_0" / "_1"); bank 1 returns the word with bits 127:0 (codes, never an exponent) inverted.
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
 string inst = INSTANCE;
 bit bk1;
 initial bk1 = inst.len() > 0 && inst.getc(inst.len() - 1) == "1";
 wire [273:0] flip = bk1 ? {146'd0, {128{1'b1}}} : 274'd0;   // bits 127:0 are codes in FP8 and FP4 words
 always @(posedge clk) if(ce_in) rd_out <= word(addr_in) ^ flip;
endmodule
module ot_rom_8192x274_m8 #(parameter INSTANCE="")(
 input wire clk,ce_in,input wire [12:0] addr_in,output reg [273:0] rd_out);
 always @(posedge clk) if(ce_in) rd_out <= {2'b0,8'd127,{16{8'h22}},8'd127,{16{8'h22}}};
endmodule
