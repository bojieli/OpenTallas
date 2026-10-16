`timescale 1ps/1fs
`default_nettype none
// Atomic four-tap join behind the existing native 16-lane score boundary.
// 128 credits per tap reserve every in-flight word, independent of tap skew.
// MEM=1 (FILL-9 2026-10-10, root cause of the flop build: 4 x 128 x 153 b = 78 kbit of flops behind four 128:1
// read muxes): each tap queue is an ot_fifo_sram_fwft on one ot_sram_1r1w_128x256_m1_r2c2 macro with a 2-entry
// registered head buffer (macro rd_out captured directly); the overflow check uses a per-tap occupancy counter.
// FE=1 (fe-push-hgi-1010, feasibility 2026-10-10: in->reg 20 levels, one combinational `fire` to 609+ enables,
// local rs1/rs2 sync -> SS async recovery -141):
//   * reset: the rst port drives only an ot_rst_relay (5 regions: tap queues 0..3, join core);
//   * taps: pin flops (valid reset, payload not) in front of each queue: +1 cycle a word, credits unchanged
//     (a word in the pin flop still holds its upstream credit; the queue never holds more than CRED);
//   * fire: one copy a tap queue plus one for the core, each from its own kept registers (credits != 0, fault),
//     so no single net reaches every queue / output enable; all copies are equal by construction;
//   * fault: the overflow and lane-order compares are registered (fault rises one cycle later; fault-free
//     behaviour is unchanged);
//   * output payload sd is captured every cycle (valid-qualified by sv, as every native s consumer samples it):
//     no 609-flop enable.
module hfd_idx_t4_join #(parameter integer AW=7, CRED=128, MEM=0, FE=0) (
 input wire ck, rst,
 input wire [615:0] taps,
 output reg [3:0] tap_credit,
 output wire [609:0] s,
 input wire sc,
 output reg fault
);
 wire [4:0] rnr;
 generate if (FE != 0) begin : g_rr
   ot_rst_relay #(.REGIONS(5)) u_rr (.clk(ck), .rst_n_in(rst), .rst_n(rnr));
 end else begin : g_rl
   reg rs1, rs2;
   always @(posedge ck or negedge rst)
     if (!rst) {rs2,rs1} <= 2'b00; else {rs2,rs1} <= {rs1,1'b1};
   assign rnr = {5{rs2}};
 end endgenerate
 wire rn = rnr[4];
 wire [3:0] ne;
 wire [152:0] head [0:3];
 wire [AW:0] occupancy [0:3];
 reg [8:0] credits;
 reg scq;
 reg sv;
 reg [608:0] sd;
 wire last_ok=(head[0][0]==head[1][0]) &&
              (head[0][0]==head[2][0]) && (head[0][0]==head[3][0]);
 // per-consumer fire copies (FE=1): [t] tap queue t, [4] join core
 (* keep = "true", dont_touch = "true" *) reg [4:0] cnz_k;   // credits != 0
 (* keep = "true", dont_touch = "true" *) reg [4:0] flt_k;   // copy of fault
 wire [4:0] fire_c;
 wire fire_raw=(&ne) && credits!=0 && !fault && last_ok;
 genvar t;
 generate for(t=0;t<5;t=t+1) begin: gf
   if (FE != 0) begin : r
`ifdef MUT_FE_CNZ
     // mutant: tap queue 0's fire copy ignores its credit copy (must FAIL the credit-stall bench)
     assign fire_c[t]=(&ne) && (t==0 ? 1'b1 : cnz_k[t]) && !flt_k[t] && last_ok;
`else
     assign fire_c[t]=(&ne) && cnz_k[t] && !flt_k[t] && last_ok;
`endif
   end else begin : c
     assign fire_c[t]=fire_raw;
   end
 end endgenerate
 wire fire=fire_c[4];
 wire [3:0] push;
 wire [152:0] pdata [0:3];
 wire [3:0] ovf_now;
 generate for(t=0;t<4;t=t+1) begin: gt
   wire rq = rnr[t];
   if (FE != 0) begin : pf
     reg pv; reg [152:0] pd;
     always @(posedge ck or negedge rq) if(!rq) pv<=1'b0; else pv<=taps[t*154];
     always @(posedge ck) pd<=taps[t*154+1 +:153];
     assign push[t]=pv; assign pdata[t]=pd;
   end else begin : np
     assign push[t]=taps[t*154]; assign pdata[t]=taps[t*154+1 +:153];
   end
   if (MEM == 0) begin : fl
     hfd_idx_fifo #(.W(153),.AW(AW)) queue (
       .ck(ck),.rst_n(rq),.we(push[t]),.wd(pdata[t]),
       .re(fire_c[t]),.rd(head[t]),.ne(ne[t]),.cnt(occupancy[t]));
   end else begin : sr
     wire ovf_, hv_; wire [152:0] hd_;
     reg [AW:0] occ;
     wire [AW:0] occ_n = occ + {{AW{1'b0}}, push[t]} - {{AW{1'b0}}, fire_c[t]};
     ot_fifo_sram_fwft #(.W(153),.DEPTH(1<<AW),.MACRO(2)) queue (
       .clk(ck),.rst_n(rq),.push(push[t]),.wdata(pdata[t]),
       .pop(fire_c[t]),.hv(hv_),.head(hd_),.ovf(ovf_));
     assign ne[t]=hv_; assign head[t]=hd_;
     always @(posedge ck or negedge rq)
       if(!rq) occ<={(AW+1){1'b0}}; else occ<=occ_n;
     assign occupancy[t]=occ;
   end
   assign ovf_now[t]=push[t] && occupancy[t]==(1<<AW) && !fire_c[t];
 end endgenerate
 // next credits / fault (shared D logic; the FE copies register it per consumer)
 reg [8:0] credits_n;
 reg fault_n;
 reg [3:0] ovf_q;
 reg mis_q;
 always @* begin
   credits_n=credits; fault_n=fault;
   case({fire,scq})
     2'b10: credits_n=credits-1'b1;
     2'b01: begin
       if(credits>=CRED) fault_n=1'b1;
       else credits_n=credits+1'b1;
     end
     default: ;
   endcase
   if (FE != 0) begin
     if(mis_q || (|ovf_q)) fault_n=1'b1;
   end else begin
     if((&ne) && !last_ok) fault_n=1'b1;
     if(|ovf_now) fault_n=1'b1;
   end
 end
 always @(posedge ck or negedge rn) begin
   if(!rn) begin
     credits<=9'(CRED); scq<=0; sv<=0; tap_credit<=0; fault<=0; ovf_q<=0; mis_q<=0;
   end else begin
     scq<=sc;
     sv<=fire;
     tap_credit<={4{fire}};
     credits<=credits_n;
     fault<=fault_n;
     ovf_q<=ovf_now;
     mis_q<=(&ne) && !last_ok;
   end
 end
 generate if (FE != 0) begin : g_fk
   always @(posedge ck or negedge rn)
     if(!rn) begin cnz_k<={5{(CRED!=0)}}; flt_k<=5'b0; end
     else begin cnz_k<={5{credits_n!=9'd0}}; flt_k<={5{fault_n}}; end
 end endgenerate
 generate if (FE != 0) begin : g_sdu
   // valid-qualified payload: captured every cycle, meaningful when sv
   always @(posedge ck) begin
     sd[0]<=head[0][0];
     for(integer v=0;v<4;v=v+1) begin
       sd[1+4*v +:4]<=head[v][1 +:4];
       sd[17+4*v +:4]<=head[v][5 +:4];
       sd[33+64*v +:64]<=head[v][9 +:64];
       sd[289+80*v +:80]<=head[v][73 +:80];
     end
   end
 end else begin : g_sde
   always @(posedge ck) if(fire) begin
     sd[0]<=head[0][0];
     for(integer v=0;v<4;v=v+1) begin
       sd[1+4*v +:4]<=head[v][1 +:4];
       sd[17+4*v +:4]<=head[v][5 +:4];
       sd[33+64*v +:64]<=head[v][9 +:64];
       sd[289+80*v +:80]<=head[v][73 +:80];
     end
   end
 end endgenerate
 assign s={sd,sv};
endmodule
`default_nettype wire
