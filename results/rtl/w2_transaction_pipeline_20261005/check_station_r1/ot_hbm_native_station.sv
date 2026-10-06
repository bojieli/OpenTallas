`timescale 1ns/1ps
// ONE parameterized native station parent. MODE0 reuses the pinned four-capture
// implementation unchanged. MODE1 is owned held multicast; MODE2 is an atomic
// SM-result join, not all-forward validity. Other functions require their actual
// source ABI and deliberately cannot elaborate as a valid station.
// Function-mode handshakes use the positive root clock. The outgoing root is
// four real kept inversions (same polarity); receiver insertion/hold is OPEN.
// rst_n[0] is cold POR in function modes. Warm reset requires quiesce+drain;
// no unilateral credit/reset recovery promise is made.
module ot_hbm_native_station #(
 parameter integer MODE=0,ENABLE=0,W=512,NI=1,NO=1,IW=W,
 parameter integer RELEASE_BACKPRESSURE=0,
 parameter [191:0] COHORT_MASK={192{1'b1}}
)(
 input wire fclk_i,input wire [3:0] rst_n,
 input wire i_v,input wire [W-1:0] i_d,
 output wire fclk_o,output wire o_v,output wire [W-1:0] o_d,
 // Function ABI, real ownership and finite permissions. in_data is one SM
 // record per input for MODE2; out_data is a held full vector per MODE1 tap.
 input wire quiesce,
 input wire [NI-1:0] in_v,output wire [NI-1:0] in_r,
 input wire [NI*IW-1:0] in_data,input wire [NI*192-1:0] in_owner,
 output wire [NO-1:0] out_v,input wire [NO-1:0] out_r,
 output wire [NO*W-1:0] out_data,output wire [NO*192-1:0] out_owner,
 input wire [NO-1:0] ACK_v,input wire [NO*192-1:0] ACK_owner,
 // Release pulses once after actual acceptance+matching reverse ACKs.
 // Upstream must reserve its reverse receipt on acceptance (VM-root contract).
 input wire source_release_r,
 output wire source_release,drained,paused,fault
);
 generate if(MODE==0)begin:forwarding
  ot_hbm_native_register_slice #(.W(W),.ENABLE(ENABLE)) u_forward(
   .fclk_i(fclk_i),.rst_n(rst_n),.i_v(i_v),.i_d(i_d),.fclk_o(fclk_o),.o_v(o_v),.o_d(o_d));
  assign in_r=0;assign out_v=0;assign out_data=0;assign out_owner=0;
  assign source_release=0;assign drained=1;assign paused=0;assign fault=0;
 end else if(!ENABLE)begin:disabled
  assign fclk_o=0;assign o_v=0;assign o_d=0;assign in_r=0;
  assign out_v=0;assign out_data=0;assign out_owner=0;
  assign source_release=0;assign drained=1;assign paused=0;assign fault=0;
 end else begin:held
  initial begin
   if(MODE!=1&&MODE!=2)$fatal(1,"actual cdist/duplex ABI required; no generic forwarding substitute");
   if(NO<1||NO>4||NI<1||NI>8)$fatal(1,"native station shape outside priced range");
   if(MODE==1&&(NI!=1||IW!=W))$fatal(1,"multicast has one whole-vector source");
   if(MODE==2&&(NO!=1||IW!=270||W!=NI*IW||COHORT_MASK==0))
    $fatal(1,"SM gather needs actual270b records, ordered NI lanes and nonzero cohort identity mask");
  end
  // Explicit forwarding cells, never an independent free output clock.
  wire c1,c2,c3;
  ot_fwd_clk_inv u_clk0(.a(fclk_i),.y(c1));
  ot_fwd_clk_inv u_clk1(.a(c1),.y(c2));
  ot_fwd_clk_inv u_clk2(.a(c2),.y(c3));
  ot_fwd_clk_inv u_clk3(.a(c3),.y(fclk_o));
  assign o_v=0;assign o_d=0;
  localparam PW=IW+192;
  wire [NI-1:0] cv,ce,cf,ready_i;
  wire [NI*PW-1:0] seats;
  wire [63:0] ctl;
  wire normal,ctl_fault,repairing;
  wire active=ctl[0];wire [3:0] sent=ctl[4:1],acked=ctl[8:5];
  wire join_present=&cv;
  wire release_all;
  wire illegal;
  wire [NO-1:0] ack_valid,ack_ready,ack_fault,ack_empty;
  wire receipt_capacity=(MODE!=1)||(&ack_ready);
  wire [NO*192-1:0] ack_seats;
  wire ack_consume=normal&&join_present&&active&&!(|cf);
  // Actual reverse receipt seats: no ACK_ready exists in the VM-root ABI.
  // One receipt per branch is reserved for the live transaction. Repair of
  // payload/control cannot discard an arriving receipt. Receipt overload or
  // receipt UE fails closed with ownership retained.
  for(genvar a=0;a<NO;a=a+1)begin:receipts
   if(MODE==1)begin:reserved
    ot_hbm_w2_protected_cut_check_on #(.W(192)) u_ack(
     .clk(fclk_i),.por_n(rst_n[0]),.in_v(ACK_v[a]&&!fault),.in_r(ack_ready[a]),
     .in_d(ACK_owner[a*192+:192]),.out_v(ack_valid[a]),
     .out_r(ack_consume),.out_d(ack_seats[a*192+:192]),.empty(ack_empty[a]),.fault(ack_fault[a]));
   end else begin:unused
    assign ack_valid[a]=0;assign ack_ready[a]=0;assign ack_fault[a]=0;assign ack_empty[a]=1;assign ack_seats[a*192+:192]=0;
   end
  end
  assign fault=(|cf)||ctl_fault||(|ack_fault)||illegal;
  assign paused=repairing || (!(|cf)&&!(&ce)&&!join_present) ||
   ((MODE==1)&&!(|ack_fault)&&(|(~ack_empty&~ack_valid)));
  assign drained=(&ce)&&(&ack_empty)&&normal&&!active&&!fault;
  assign source_release=release_all&&!fault;
  for(genvar k=0;k<NI;k=k+1)begin:inputs
   // Existing cut, including its actual five-word repair seat and valid bit.
   ot_hbm_w2_protected_cut_check_on #(.W(PW)) u_cut(
    .clk(fclk_i),.por_n(rst_n[0]),.in_v(in_v[k]&&!quiesce&&!fault&&receipt_capacity),.in_r(ready_i[k]),
    .in_d({in_owner[k*192+:192],in_data[k*IW+:IW]}),
    .out_v(cv[k]),.out_r(release_all&&!fault),.out_d(seats[k*PW+:PW]),.empty(ce[k]),.fault(cf[k]));
   assign in_r[k]=ready_i[k]&&!quiesce&&!fault&&receipt_capacity;
  end
  wire [191:0] owner0=seats[IW+:192];
  reg cohort_bad;
  always @*begin
   cohort_bad=0;
   if(MODE==2&&join_present)begin
    for(integer k=0;k<NI;k=k+1)begin
     // Full real owner is carried. A source owner must bind any less strict
     // shared-cohort mask; it is never inferred from a width ledger.
     if((seats[k*PW+IW+:192]&COHORT_MASK)!=(owner0&COHORT_MASK))cohort_bad=1;
     // Actual SM tuple contract {fault,rv,rrow12,rdata256}.
     if(seats[k*PW+269]||!seats[k*PW+268]||seats[k*PW+256+:12]!=seats[256+:12])cohort_bad=1;
    end
   end
  end
  localparam [3:0] ALL=(4'b1111>>(4-NO));
  reg ack_bad;
  reg [3:0] next_sent,next_acked;
  always @*begin
   ack_bad=0;next_sent=sent;next_acked=acked;
   if(MODE==1)begin
    for(integer t=0;t<NO;t=t+1)begin
     if(out_v[t]&&out_r[t])next_sent[t]=1;
     if(ACK_v[t]&&!ack_ready[t])ack_bad=1;
     if(normal&&join_present)begin
      if(ACK_v[t]&&(!active||!sent[t]||acked[t]||ACK_owner[t*192+:192]!=owner0))ack_bad=1;
      if(ack_valid[t])begin
       if(!active||!sent[t]||acked[t]||ack_seats[t*192+:192]!=owner0)ack_bad=1;
       else next_acked[t]=1;
      end
     end
    end
   end else if(|ACK_v)ack_bad=1;
  end
  assign illegal=cohort_bad||ack_bad;
  // Opt-in held retirement for a real full-frame upstream receipt seat.
  // Default0 preserves the original readyless-release ABI; no added state.
  assign release_all=normal&&join_present&&active&&
   (!RELEASE_BACKPRESSURE||source_release_r)&&
   ((MODE==1)?((acked&ALL)==ALL):out_r[0]);
  wire arm=normal&&join_present&&!active&&!fault;
  wire [63:0] next_ctl=release_all?64'b0:
   arm?64'b1:{55'b0,next_acked,next_sent,active};
  ot_hbm_w2_protected_bank_check_on #(.WORDS(1)) u_permissions(
   .clk(fclk_i),.por_n(rst_n[0]),.load(normal&&(arm||release_all||next_sent!=sent||next_acked!=acked)),
   .load_encoded(1'b0),.fatal(illegal),.d(next_ctl),.encoded_d(72'b0),
   .q(ctl),.encoded_q(),.normal(normal),.fault(ctl_fault),.repairing(repairing));
  for(genvar t=0;t<NO;t=t+1)begin:outputs
   assign out_v[t]=normal&&join_present&&active&&!fault&&((MODE==1)?!sent[t]:1'b1);
   assign out_owner[t*192+:192]=owner0;
   if(MODE==1)assign out_data[t*W+:W]=seats[IW-1:0];
   else begin:gather
    for(genvar k=0;k<NI;k=k+1)begin:ordered
     assign out_data[t*W+k*IW+:IW]=seats[k*PW+:IW];
    end
   end
  end
 end endgenerate
endmodule
