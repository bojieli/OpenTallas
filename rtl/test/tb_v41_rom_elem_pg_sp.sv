`timescale 1ns/1ps
// Power-aware exactness bench: the S81 pair element core (ot_v41_rom_elem_w10 BF16 0, NB 2, MTP, EARLY, FAST, PP) always on
// (ref, the unmodified RTL) against the same element inside ot_v41_rom_elem_pg_w10 #(PG = 1) whose domain is a
// Yosys-flattened netlist that loses EVERY stored bit (registers, memories, clock-gate latch, ROM output latches)
// when the header-switch model reports it unpowered (tools/rom_stage_pg_sim.py).  A decode sequence of tokens
// arrives on a static schedule; the domain sleeps between tokens, the scheduler pre-wakes it, the wrapper
// restores the retained configuration; configurations written while it sleeps reach only the shadow.
// Every public output is compared on every cycle.
// SPINE variant (2026-10-04): the DUT is ot_v41_rom_elem_pg_sp_w10 #(SPINE = 1): the domain's clock is the gated
// stage clock spine, the always-on side runs on aon_clk (same source as clk).  The bench also checks that the spine
// is stopped whenever the domain is unpowered (no domain clock edge while every ring segment is off) and counts the
// cycles it is stopped.
module tb_v41_rom_elem_pg_sp;
 parameter integer P = 16000;          // token period at this stage (cycles), static schedule
 parameter integer NTOK = 12;
 parameter integer NSUB = 4;
 parameter integer SW_D = 8;           // header-ring segment wake (enable -> ack), cycles
`ifdef PG_MUTANT_SHORT_LEAD
 localparam integer LEAD = 8;
`else
 localparam integer LEAD = 200;
`endif
 reg clk=0, rst_n=0, cfg_v=0, go=0, go_bf=0, xs_v=0;
 reg [4:0] cfg_a=0; reg [47:0] cfg_d=0;
 reg [7:0] xs_p=0; reg [2:0] xs_b=0, xs_pos=0;
 reg [255:0] q0=0, q1=0;
 reg sched_v=0; reg [23:0] sched_gap=0;
 always #0.5 clk=~clk;
 wire [1:0] av,bv,ae,be; wire [63:0] ad,bd; wire [31:0] ar,br;
 wire [9:0] asg,bsg,an,bn; wire [5:0] ap,bp; wire ab,bb,af,bf;
 wire [NSUB-1:0] sw_en; reg [NSUB-1:0] sw_ack=0;
 wire pg_ready, pg_late, pg_fault;
 ot_v41_rom_elem_w10_ref #(.NB(2), .BF16(0), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .FRONT_PAR(0),
  .INSTANCE("ref")) ref_dut (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go),
  .go_bf(go_bf), .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_pos(xs_pos), .xs_sv(2'b11), .xs_q0(q0), .xs_e0(10'd127),
  .xs_q1(q1), .xs_e1(10'd126), .xb_v(1'b0), .xb_b(3'd0), .xb_pos(3'd0), .xb_sv(4'd0), .xb_u(32'd0), .xb_d(1024'd0),
  .pv(av), .pval(ad), .prow(ar), .pseg(asg), .pnseg(an), .perr(ae), .ppos(ap), .busy(ab), .fault(af));
 ot_v41_rom_elem_pg_sp_w10 #(.NB(2), .BF16(0), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .FRONT_PAR(0),
  .INSTANCE("dut"), .PG(1), .NSUB(NSUB), .SPINE(1)
`ifdef PG_DOM_CG
  , .DOM_CG(1)
`endif
  ) dut (.clk(clk), .aon_clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d),
  .go(go), .go_bf(go_bf), .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_pos(xs_pos), .xs_sv(2'b11), .xs_q0(q0),
  .xs_e0(10'd127), .xs_q1(q1), .xs_e1(10'd126), .xb_v(1'b0), .xb_b(3'd0), .xb_pos(3'd0), .xb_sv(4'd0),
  .xb_u(32'd0), .xb_d(1024'd0), .pv(bv), .pval(bd), .prow(br), .pseg(bsg), .pnseg(bn), .perr(be), .ppos(bp),
  .busy(bb), .fault(bf),
  .pg_en(1'b1), .sched_v(sched_v), .sched_gap(sched_gap), .pg_lead(24'(LEAD)), .pg_bet(24'd64), .pg_idle(8'd160),
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
 reg pwr_off = 0;                       // the domain is unpowered: tools/rom_stage_pg_sim.py corrupts on its rise
 always @(posedge clk) pwr_off <= ~|sw_ack;
 // an unpowered domain drives undefined outputs: only the isolation clamps may keep them off the AO side
 always @(posedge pwr_off) begin
   force dut.e_pv = 'x; force dut.e_pval = 'x; force dut.e_prow = 'x; force dut.e_pseg = 'x; force dut.e_pnseg = 'x;
   force dut.e_perr = 'x; force dut.e_ppos = 'x; force dut.e_busy = 'x; force dut.e_fault = 'x;
 end
 always @(negedge pwr_off) begin
   release dut.e_pv; release dut.e_pval; release dut.e_prow; release dut.e_pseg; release dut.e_pnseg;
   release dut.e_perr; release dut.e_ppos; release dut.e_busy; release dut.e_fault;
 end

`ifdef PG_MUTANT_NO_RESTORE
 initial begin #3; force dut.g_pg.u_ao.rhit = 1'b0; end
`endif
`ifdef PG_MUTANT_NO_ISO
 initial begin #3; force dut.g_pg.u_ao.iso_n = 1'b1; end
`endif

 // spine: no domain clock edge while the domain is unpowered; count the stopped cycles
 integer spine_off=0, spine_bad=0;
 // at a rising edge the spine gate's latch holds the enable it captured in the low phase before it (whether this
 // edge passes), and sw_ack still holds the ring state before the edge's updates (whether the domain is powered)
 always @(posedge clk) if (rst_n) begin
   if (!dut.g_pg.u_ao.g_spine.u_spine_cg.u_icg.en_l) spine_off = spine_off + 1;
   if (~|sw_ack && dut.g_pg.u_ao.g_spine.u_spine_cg.u_icg.en_l) spine_bad = spine_bad + 1;
 end
 integer cyc=0, rows=0, nonzero=0, sleeps=0, wakes=0, off_cyc=0, on_cyc=0, restores=0;
 integer wake_t0=-1, wake_max=0, wake_min=1<<30, restore_max=0, pg_t=-1;
 always @(negedge clk) if (rst_n) begin
   cyc=cyc+1;
   if ({av,ab,af} !== {bv,bb,bf}) begin
     $display("DEBUG restores=%0d valid=%b dirty=%b ready=%b drain=%h w_run=%b i1_v=%b n_run=%b bn_run=%b go_e=%b qlast=%h ref_qlast=%h",
       restores, dut.g_pg.u_ao.valid, dut.g_pg.u_ao.dirty, pg_ready, dut.u_elem.drain, dut.u_elem.w_run, dut.u_elem.i1_v,
       dut.u_elem.n_run, dut.u_elem.bn_run, dut.u_elem.go_e, dut.u_elem.qlast, ref_dut.qlast);
   end
 if ({av,ab,af} !== {bv,bb,bf}) $fatal(1,"FATAL public control mismatch cycle=%0d ref=%b dut=%b",cyc,{av,ab,af},{bv,bb,bf});
   for (integer m=0;m<2;m=m+1) if (av[m]) begin
     if ({ad[32*m+:32],ar[16*m+:16],asg[5*m+:5],an[5*m+:5],ae[m],ap[3*m+:3]} !==
         {bd[32*m+:32],br[16*m+:16],bsg[5*m+:5],bn[5*m+:5],be[m],bp[3*m+:3]})
       $fatal(1,"FATAL partial mismatch cycle=%0d macro=%0d ref=%h dut=%h",cyc,m,ad[32*m+:32],bd[32*m+:32]);
     rows=rows+1; if (ad[32*m+:32]!=0) nonzero=nonzero+1;
   end
   if (pg_late || pg_fault) $fatal(1,"FATAL schedule miss or ring fault cycle=%0d late=%0d fault=%0d",cyc,pg_late,pg_fault);
   if (~|sw_ack) off_cyc=off_cyc+1; else on_cyc=on_cyc+1;
   if (dut.g_pg.u_ao.u_sched.req_on && wake_t0 < 0 && ~|sw_ack && !dut.g_pg.u_ao.pwr_good) wake_t0=cyc;
   if (dut.g_pg.u_ao.pwr_good && pg_t < 0 && wake_t0 >= 0) pg_t=cyc;
   if (dut.g_pg.u_ao.rst_wr) restores=restores+1;
   if (pg_ready && wake_t0 >= 0) begin
     wakes=wakes+1;
     if (cyc-wake_t0 > wake_max) wake_max=cyc-wake_t0;
     if (cyc-wake_t0 < wake_min) wake_min=cyc-wake_t0;
     if (cyc-pg_t > restore_max) restore_max=cyc-pg_t;
     wake_t0=-1; pg_t=-1;
   end
 end
 always @(posedge pwr_off) if (rst_n) sleeps=sleeps+1;
 integer aborts=0;
 reg abort_seen=0;
 always @(negedge clk) if (rst_n && dut.g_pg.u_ao.u_sched.req_on && dut.g_pg.u_ao.u_sched.u_pg.st >= 5) begin
   if (!abort_seen) begin aborts=aborts+1; $display("ABORT wake request during power-down cycle=%0d state=%0d", cyc, dut.g_pg.u_ao.u_sched.u_pg.st); end
   abort_seen=1;
 end else abort_seen=0;
 // debug: +DUMP_FROM=<cycle> +DUMP_TO=<cycle> dumps the wrapper and the gated domain
 integer dump_from=-1, dump_to=-1;
 initial begin
   if ($value$plusargs("DUMP_FROM=%d", dump_from)) begin
     if (!$value$plusargs("DUMP_TO=%d", dump_to)) dump_to = dump_from + 100;
     $dumpfile("pg_debug.vcd"); $dumpvars(0, dut); $dumpoff;
   end
 end
 always @(negedge clk) begin
   if (dump_from >= 0 && cyc == dump_from) $dumpon;
   if (dump_from >= 0 && cyc == dump_to) $dumpoff;
 end

 // deterministic content-dependent ROM: finite FP4 / FP8 codes (bytes masked 0x77), exponent varies with address
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
   @(negedge clk); #0.01; cfg_v=1; cfg_a=5'(a); cfg_d=d;
 endtask
 task automatic configure(input integer mode);
   integer nu,base; reg [47:0] d;
   for(integer c=0;c<8;c=c+1) begin
     d=48'(c+1) | (48'd1<<21) | (48'(mode!=1)<<26) | (48'd1<<27) | (48'd1<<28);
     cfg(c,d); cfg(17+c,48'(c+101));
     // class 7 (segment 7) idle: ot_v41_rom_elem_w10 writes entry 2NSEG+1+7 (the second macro's segment-7 row)
     // to s_row[NSEG-1] (index NSEG + a[SW-1:0] - 1 wraps), so s_row[2NSEG-1] is never written: undefined in RTL
     nu=(mode==0) ? ((c==0)?9:((c==3)?3:((c==6)?2:0))) : ((c==7)?0:1);
     base=(c==0)?252:(32*c);
     d=48'(nu!=0) | (48'(base)<<1) | (48'(nu)<<9) | (48'(c)<<16) | (48'(c)<<19) | (48'(mode==2)<<22);
     cfg(8+c,d);
   end
   cfg(16,48'(mode==0) | (48'(mode==0 ? 2 : 0)<<3));
   @(negedge clk); #0.01; cfg_v=0;
 endtask
 integer nbeat=0;
 task automatic beat(input integer kind);
   @(negedge clk); #0.01;
   xs_v=(kind!=4); xs_p=ref_dut.n_pair; xs_b=ref_dut.n_b; xs_pos=ref_dut.n_pos;
   q0=xword(nbeat,1); q1=xword(nbeat,2); nbeat=nbeat+1;
   case(kind) 1: xs_p=xs_p+8'd1; 2: xs_b=xs_b+3'd1; 3: xs_pos=xs_pos+3'd1; endcase
   tick(1); @(negedge clk); #0.01; xs_v=0;
   tick(12);
 endtask
 integer modes [0:NTOK-1];
 integer short_off [0:NTOK-1];
 integer t_next, tok, sent, cur_mode;
 task automatic wait_until(input integer t); while (cyc < t) @(negedge clk); endtask
 initial begin
   modes[0]=0; modes[1]=0; modes[2]=1; modes[3]=1; modes[4]=0; modes[5]=1; modes[6]=1; modes[7]=1; modes[8]=0; modes[9]=0;
   modes[10]=0; modes[11]=1;
   // wake mid-sequence: after tokens 6 and 9 the next arrival is announced only once the element has drained, at a
   // gap that makes the pre-wake request land while the controller is still powering the domain down
   for (integer i=0;i<NTOK;i=i+1) short_off[i]=-1;
   // short_off = the power-down state the next arrival's pre-wake request must land in (5 S_DN_CLK, 6 S_DN_ISO,
   // 7 S_DN_SW): the bench announces the arrival (gap = lead + bet, so the request is immediate) in the cycle
   // before the controller enters that state
   short_off[0]=5; short_off[6]=6; short_off[9]=7;
   tick(4); @(negedge clk); #0.01; rst_n=1;
   t_next = 3000; cur_mode = -1;
   @(negedge clk); #0.01; sched_v=1; sched_gap=24'(t_next-cyc-1); @(negedge clk); #0.01; sched_v=0;
   for (tok=0; tok<NTOK; tok=tok+1) begin
     if (modes[tok] != cur_mode) begin
       // reconfigure in the idle gap: the domain is asleep (except before the first token), shadow only
       wait_until(t_next - P/2 > cyc ? t_next - P/2 : cyc);
       if (tok > 0 && pg_ready) $fatal(1,"FATAL domain awake during the idle reconfiguration tok=%0d",tok);
       configure(modes[tok]); cur_mode = modes[tok];
     end
     wait_until(t_next - 1);
     if (ab) $fatal(1,"FATAL period too short tok=%0d",tok);
     @(negedge clk); #0.01; go=1; sched_v=(tok < NTOK-1) && short_off[tok] < 0; sched_gap=24'(P-1);
     $display("TOKEN %0d mode=%0d go_cycle=%0d dut_ready=%0d", tok, modes[tok], cyc, pg_ready);
     @(negedge clk); #0.01; go=0; sched_v=0; tick(4);
     sent=0;
     while(ref_dut.n_run && sent<1000) begin
       if(sent%9==0) begin beat(1); beat(2); beat(3); beat(4); end
       beat(0); sent=sent+1;
     end
     if(sent==1000) $fatal(1,"FATAL walker failed to finish");
     if (short_off[tok] >= 0) begin
       while (short_off[tok] == 5 ? !(dut.g_pg.u_ao.u_sched.u_pg.st == 4 && !dut.g_pg.u_ao.u_sched.req_on)
                                  : dut.g_pg.u_ao.u_sched.u_pg.st != short_off[tok] - 1) @(negedge clk);
       #0.01; sched_v=1; sched_gap=24'(LEAD + 64); t_next = cyc + LEAD + 64 + 1;
       @(negedge clk); #0.01; sched_v=0;
       $display("SHORT gap after token %0d: next go at %0d", tok, t_next);
     end else t_next = t_next + P;
     if (tok == NTOK-1) tick(800);
   end
   if (ab||bb||af||bf) $fatal(1,"FATAL final drain");
   if (rows<100 || nonzero<50 || sleeps<NTOK || wakes<NTOK || restores<NTOK*25 || aborts<3)
     $fatal(1,"FATAL coverage rows=%0d nonzero=%0d sleeps=%0d wakes=%0d restores=%0d aborts=%0d",rows,nonzero,sleeps,wakes,restores,aborts);
   if (spine_bad != 0) $fatal(1,"FATAL spine ran while the domain was unpowered: %0d cycles", spine_bad);
   if (spine_off + 2*NTOK < off_cyc) $fatal(1,"FATAL spine stopped %0d cycles < unpowered %0d cycles", spine_off, off_cyc);
   $display("SPINE stopped_cycles=%0d unpowered_cycles=%0d", spine_off, off_cyc);
   $display("WAKE min=%0d max=%0d cycles (req_on -> ready); restore max=%0d cycles; lead=%0d", wake_min, wake_max, restore_max, LEAD);
   $display("PASS cycles=%0d rows=%0d nonzero=%0d sleeps=%0d wakes=%0d restores=%0d aborts=%0d off_cycles=%0d on_cycles=%0d",
            cyc,rows,nonzero,sleeps,wakes,restores,aborts,off_cyc,on_cyc);
   $finish;
 end
endmodule

module ot_rom_4096x274_m8 #(parameter INSTANCE="")(input wire clk,ce_in,input wire [11:0] addr_in,output reg [273:0] rd_out);
 always @(posedge clk) if(ce_in) rd_out <= tb_v41_rom_elem_pg_sp.romword({1'b0,addr_in});
endmodule
module ot_rom_4096x274_m8_pgx #(parameter INSTANCE="")(input wire clk,ce_in,input wire [11:0] addr_in,output reg [273:0] rd_out);
 always @(posedge clk) if(ce_in) rd_out <= tb_v41_rom_elem_pg_sp.romword({1'b0,addr_in});
 always @(posedge tb_v41_rom_elem_pg_sp.pwr_off) rd_out = {9{$urandom}};   // the macro's output latch is in the domain
endmodule
module ICGx1_pgx (input wire CLK, input wire ENA, input wire SE, output wire GCLK);
 reg en_l;
 always @* if (!CLK) en_l = ENA | SE;
 always @(posedge tb_v41_rom_elem_pg_sp.pwr_off) en_l = $urandom;
 assign GCLK = CLK & en_l;
endmodule
// the platform ICG cell (ot_hdc_cg under SYNTHESIS) for the always-on side and the reference
module ICGx1_ASAP7_75t_R (input wire CLK, input wire ENA, input wire SE, output wire GCLK);
 reg en_l;
 always @* if (!CLK) en_l = ENA | SE;
 assign GCLK = CLK & en_l;
endmodule
