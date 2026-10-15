`timescale 1ns/1ps
// Physical candidate: one explicit input station plus the original registered
// dispatch edge. The compiler must account for two edges, not one. Independent
// <=120-bit slices keep every queue/control driver regional. No ready or credit.
module ot_qfd_x3_mux_native #(parameter integer MUT=0)(
 input wire ck, rst_n,
 input wire [523:0] q,
 input wire kvn_v, input wire [511:0] kvn_d, input wire [10:0] kvn_tag,
 input wire slot_v, slot_q,
 output wire x3_v, output wire [511:0] x3_d, output wire [10:0] x3_tag,
 output wire fault
);
 localparam integer NS=5;
 // q14 r11 (2026-10-14): reset pin register.  Native pin audit of the CLOSED view qfd_x3_mux_native-p1-2008d1b57
 // (TT +209.56): rst_n capture 249.3 ps > 190 -- the port fanned out to the async resets of all five 120-bit slices
 // spread over the 129.6 um tile.  The port now lands in ONE flop at the pin (async assert, registered deassert one
 // edge later); the slices reset from it.  Release is 1 clk edge later than before: inputs presented on the first
 // edge after the rst_n pin rises are ignored (the die holds reset/idle >= 1 extra edge before the first slot;
 // static schedule: reset release +1 edge).  Data latency (2 edges) is unchanged.  MUT=3: reset bypass mutant.
 (* keep = "true", dont_touch = "true" *) reg rs_q;
 always @(posedge ck or negedge rst_n) if(!rst_n) rs_q<=1'b0; else rs_q<=1'b1;
 wire rst_s = (MUT==3) ? rst_n : rs_q;
 wire [522:0] kword={kvn_tag,kvn_d};
 wire [522:0] outword;
 wire [NS-1:0] lane_v,lane_fault;
 genvar g;
 generate for(g=0;g<NS;g=g+1) begin: slice
  localparam integer LO=g*120;
  localparam integer WIDTH=(523-LO>120)?120:523-LO;
  (* keep_hierarchy="yes" *) ot_qfd_x3_mux_native_slice #(.W(WIDTH),.MUT(MUT)) u (
   .ck(ck),.rst_n(rst_s),.qv(q[523]),.qd(q[LO+:WIDTH]),
   .qkind(q[522:517]),.kv(kvn_v),.kd(kword[LO+:WIDTH]),.kkind(kvn_tag[10:8]),
   .slot_v(slot_v),.slot_q(slot_q),.ov(lane_v[g]),.od(outword[LO+:WIDTH]),.fault(lane_fault[g]));
 end endgenerate
 assign {x3_tag,x3_d}=outword;
 assign x3_v=lane_v[0];
 // Slice controls capture identical events and retain identical state. Export
 // the registered first-slice status directly; no logic behind the face pin.
 assign fault=lane_fault[0];
`ifndef SYNTHESIS
 always @(posedge ck) if(rst_s && (lane_v!={NS{lane_v[0]}} || lane_fault!={NS{lane_fault[0]}}))
  $fatal(1,"native mux slice control state diverged");
`endif
endmodule

module ot_qfd_x3_mux_native_slice #(parameter integer W=120,MUT=0)(
 input wire ck,rst_n,qv, input wire [W-1:0] qd, input wire [5:0] qkind,
 input wire kv, input wire [W-1:0] kd, input wire [2:0] kkind,
 input wire slot_v,slot_q,
 output reg ov, output reg [W-1:0] od, output reg fault
);
 // Every input is captured directly. Payload registers have no reset load.
 (* keep="true", dont_touch="true" *) reg qv_r,kv_r,sv_r,sq_r;
 reg [W-1:0] qd_r,kd_r;
 reg [5:0] qkind_r;
 reg [2:0] kkind_r;
 always @(posedge ck) begin qd_r<=qd;kd_r<=kd;qkind_r<=qkind;kkind_r<=kkind;end
 always @(posedge ck or negedge rst_n)
  if(!rst_n) begin qv_r<=0;kv_r<=0;sv_r<=0;sq_r<=0;end
  else begin qv_r<=qv;kv_r<=kv;sv_r<=slot_v;sq_r<=slot_q;end
 reg [W-1:0] qf[0:1],kf[0:1];
 reg qr,qw,kr,kw; reg [1:0] qn,kn;
 wire choose_q=MUT==1 ? !sq_r : sq_r;
 wire available=choose_q ? qn!=0 : kn!=0;
 wire send=sv_r && available && !fault;
 wire qp=send && choose_q,kp=send && !choose_q;
 wire bad_q=qv_r && (qkind_r[5:3]!=3'b001 || qkind_r[2:1]!=0 || qkind_r[0]);
 wire bad_k=kv_r && kkind_r==3'b001;
 wire qi=qv_r && !bad_q && (qn<2 || qp) && !fault;
 wire ki=kv_r && !bad_k && (kn<2 || kp) && !fault;
 // Data is observable only with ov; neither FIFO storage nor output data needs reset.
 always @(posedge ck) begin
  if(qi) qf[qw]<=qd_r;
  if(ki) kf[kw]<=kd_r;
  if(send) od <= (choose_q ? qf[qr] : kf[kr]) ^ W'(MUT==2 && choose_q);
 end
 always @(posedge ck or negedge rst_n)
  if(!rst_n) begin qr<=0;qw<=0;kr<=0;kw<=0;qn<=0;kn<=0;ov<=0;fault<=0;end
  else begin
   ov<=send;
   if(bad_q || bad_k || (qv_r && !bad_q && !qi) || (kv_r && !bad_k && !ki) || (sv_r && !available)) fault<=1;
   if(qi) qw<=!qw;
   if(ki) kw<=!kw;
   if(qp) qr<=!qr;
   if(kp) kr<=!kr;
   case({qi,qp}) 2'b10:qn<=qn+1'b1;2'b01:qn<=qn-1'b1;default:;endcase
   case({ki,kp}) 2'b10:kn<=kn+1'b1;2'b01:kn<=kn-1'b1;default:;endcase
  end
endmodule
