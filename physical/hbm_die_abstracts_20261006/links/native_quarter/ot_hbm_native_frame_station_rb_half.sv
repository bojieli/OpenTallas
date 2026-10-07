`timescale 1ns/1ps
// HALF-RATE shell around ot_hbm_native_frame_station_rb (additive, drop-in ports). The unchanged station core runs on a
// clock-gated half-rate clock (latch + AND ICG; the core's budget doubles to 2 fast cycles). The fast-clock shell
// converts the single-cycle pulse protocol to level/sticky form at the pins:
//  * held inputs (in_v, in_data/owner/frame, release_held): sampled by the core at its edge (the sender holds valid
//    until it learns the one-fast-cycle ready pulse, long after the core sample);
//  * ready inputs (out_r[t], release_r): the transfer is detected in the FAST domain (own valid pin value of that
//    cycle AND the captured ready) and held sticky until the core edge samples it, then cleared; the core's learned
//    term (delayed own valid AND ready) is unchanged;
//  * readyless ACK pulses: valid captured sticky with the ACK frame held until sampled (one ACK per branch per
//    transaction, so no overwrite);
//  * pulsed outputs (in_r, release_v when release_held=0): the core's two-fast-cycle level is passed in the second
//    half only, giving the one-fast-cycle pulse the neighbours expect; held outputs (out_v, release_v when held) pass
//    through a fast launch flop; status outputs are fast flops;
//  * forwarded clock inverters hang on the FAST clock (w_clk0..3); the core's are removed (FCLK=0).
// Cost: every handshake and every core step takes two fast cycles (latency/throughput ~2x on this station).
module ot_hbm_native_frame_station_rb_half #(parameter integer ENABLE=0,NO=3)(
 input wire clk_sm,por_n,release_held,
 input wire in_v,output wire in_r,input wire [2062:0] in_data,
 input wire [191:0] in_owner,input wire [72:0] in_frame,
 output wire [NO-1:0] out_v,input wire [NO-1:0] out_r,
 output wire [NO*2063-1:0] out_data,output wire [NO*192-1:0] out_owner,
 output wire [NO*73-1:0] out_frame,
 input wire [NO-1:0] ACK_v,input wire [NO*192-1:0] ACK_owner,
 input wire [NO*73-1:0] ACK_frame,
 output wire release_v,input wire release_r,
 output wire [191:0] release_owner,output wire [72:0] release_frame,
 output wire fclk_o,drained,paused,fault
);
 generate if(!ENABLE)begin:disabled
  assign in_r=0;assign out_v=0;assign out_data=0;assign out_owner=0;assign out_frame=0;
  assign release_v=0;assign release_owner=0;assign release_frame=0;
  assign fclk_o=0;assign drained=1;assign paused=0;assign fault=0;
 end else begin:hs
  // phase + clock gate
  reg ph;
  always @(posedge clk_sm or negedge por_n)if(!por_n)ph<=1'b0;else ph<=~ph;
  wire gclk;
  ot_hbm_st_icg u_icg(.clk(clk_sm),.en(ph),.gclk(gclk));
  // forwarded clock on the fast clock
  wire c1,c2,c3;
  ot_fwd_clk_inv w_clk0(.a(clk_sm),.y(c1));
  ot_fwd_clk_inv w_clk1(.a(c1),.y(c2));
  ot_fwd_clk_inv w_clk2(.a(c2),.y(c3));
  ot_fwd_clk_inv w_clk3(.a(c3),.y(fclk_o));
  // core
  wire c_in_r,c_rv,c_fault,c_drained,c_paused;wire [NO-1:0] c_ov;
  wire [NO-1:0] hit_s,hit_core;wire rhit_core;wire [NO-1:0] ack_core;
  wire [NO*192-1:0] ack_o_core;wire [NO*73-1:0] ack_f_core;
  ot_hbm_native_frame_station_rb #(.ENABLE(1),.NO(NO),.REL_REG(0),.SAFE(0),.FCLK(0)) u_core(
   .clk_sm(gclk),.por_n(por_n),.release_held(release_held),.in_v(in_v),.in_r(c_in_r),
   .in_data(in_data),.in_owner(in_owner),.in_frame(in_frame),
   .out_v(c_ov),.out_r(hit_core),.out_data(out_data),.out_owner(out_owner),.out_frame(out_frame),
   .ACK_v(ack_core),.ACK_owner(ack_o_core),.ACK_frame(ack_f_core),
   .release_v(c_rv),.release_r(rhit_core),.release_owner(release_owner),.release_frame(release_frame),
   .fclk_o(),.drained(c_drained),.paused(c_paused),.fault(c_fault));
  // ---- fast launch flops (outputs) ----
  reg [NO-1:0] ack_s;reg [NO-1:0] taken;reg rtaken;wire [NO-1:0] hit_n;wire rhit_n;
  reg [NO-1:0] ov_o,ov_od;reg rv_o,rv_od,in_r_o,fault_o,drained_o,paused_o;
  always @(posedge clk_sm or negedge por_n)
   if(!por_n)begin ov_o<=0;ov_od<=0;rv_o<=0;rv_od<=0;in_r_o<=0;fault_o<=0;drained_o<=1;paused_o<=0;end
   else begin
    ov_o<=c_ov&~(hit_n|taken);ov_od<=ov_o;
    rv_o<=release_held?(c_rv&&!(rhit_n||rtaken)):(!ph&&c_rv);rv_od<=rv_o;
    in_r_o<=!ph&&c_in_r;
    fault_o<=c_fault;drained_o<=c_drained&&!(|hit_s)&&!(|ack_s);paused_o<=c_paused;
   end
  assign out_v=ov_o;assign release_v=rv_o;assign in_r=in_r_o;
  assign fault=fault_o;assign drained=drained_o;assign paused=paused_o;
  // ---- ready inputs: fast-domain transfer detection, sticky until the core samples it ----
  reg [NO-1:0] or_f;reg rr_f;
  reg [NO-1:0] hit_q;reg rhit_q;reg [NO-1:0] hit_st;reg rhit_st;
  always @(posedge clk_sm or negedge por_n)
   if(!por_n)begin or_f<=0;rr_f<=0;hit_st<=0;rhit_st<=0;taken<=0;rtaken<=0;end
   else begin
    or_f<=out_r;rr_f<=release_r;
    taken<=(taken|hit_n)&c_ov;rtaken<=(rtaken|rhit_n)&c_rv;
    hit_st<=hit_n|(hit_st&{NO{!ph}});
    rhit_st<=rhit_n|(rhit_st&!ph);
   end
  assign hit_n=ov_od&or_f;assign rhit_n=rv_od&rr_f;
  assign hit_s=hit_st;assign hit_core=hit_st;
  // release_held=0 is the readyless inter-station seat (ready is constant by contract): the core learns the pulse one
  // core cycle later exactly as with a constant-1 ready; a sticky ready would arrive after the pulse window and force a retry.
  assign rhit_core=release_held?rhit_st:1'b1;
  // ---- readyless ACK pulses: sticky valid + held frame ----
  reg [NO-1:0] ackv_f;reg [NO*192-1:0] acko_f;reg [NO*73-1:0] ackf_f;
  reg [NO*192-1:0] acko_h;reg [NO*73-1:0] ackf_h;
  always @(posedge clk_sm or negedge por_n)
   if(!por_n)begin ackv_f<=0;ack_s<=0;end
   else begin ackv_f<=ACK_v;ack_s<=ackv_f|(ack_s&{NO{!ph}});end
  always @(posedge clk_sm)begin
   acko_f<=ACK_owner;ackf_f<=ACK_frame;
   for(integer t=0;t<NO;t=t+1)if(ackv_f[t])begin acko_h[t*192+:192]<=acko_f[t*192+:192];ackf_h[t*73+:73]<=ackf_f[t*73+:73];end
  end
  assign ack_core=ack_s;assign ack_o_core=acko_h;assign ack_f_core=ackf_h;
 end endgenerate
endmodule

(* keep_hierarchy="yes" *)
module ot_hbm_st_icg(input wire clk,en,output wire gclk);
 reg en_l;
 always @* if(!clk)en_l=en;
 assign gclk=clk&en_l;
endmodule
