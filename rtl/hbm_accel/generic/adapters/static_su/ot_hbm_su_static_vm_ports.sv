`timescale 1ns/1ps
`default_nettype none
// Static SU VM interface of one quarter: NPG independently placeable port groups, one per VM bank pair.
// ADOPTED floorplan T_band2__npg4_s5 (GLOBAL-FP-H, main 952c5933c; coordinator 09:35 PT 10-15): the 8-bank slice sits in
// the 1.8 mm VM band between SM rows 2/3, so EVERY quadrant incl. SW/SE uses 4 bank-pair groups (NPG 4,
// BANK_GROUP 32'h3322_1100 = {0,0,1,1,2,2,3,3}); the earlier 5-group SW/SE map (0x43322110, v15/D geometry) is
// superseded (with it the adopted plan's worst cut is 0.636 instead of 0.556). NPG/BANK_GROUP stay parameters so the
// die contract states the map; the logical buses below stay one port per quarter, only the pin/leaf plan and the
// clock root follow the group.
// Each bank leaf drives the SU (near) station of the LG tap of its bank (ot_hbm_vm_lg_static_bank, READ_RETURN 10,
// WRITE_RETURN 7). No register stage is added: request pins go straight to the LG leaf's sampled local inputs, so
// the compiler latencies stay 10/7. No queues, credits, ready, arbitration or runtime rescheduling.
// The LG tap's read/write SELECTS are NOT driven here: one source, the VM calendar programme (compiler-scheduled,
// h_vm; coordinator decision 10-15 on main 517963b2f). The SU issues on the calendar's slots; a request off the
// calendar is not sampled by the leaf, so its return never arrives and the return check latches FAULT.
// Checks only (never stall, never replay):
//   * a request must address this quarter's slice (SID == QID, no mirror) and its own bank (F2 per-quarter spread);
//   * every read must return exactly READ_RETURN edges later, every write must be done exactly WRITE_RETURN edges
//     later; a missing or unsolicited return latches FAULT.
// MUT=1 (bench must fail): the leaf forgets the per-quarter spread and sends the logical SID-major slice bits.
module ot_hbm_su_static_vm_bank_leaf #(parameter integer QID=0,B=0,READ_RETURN=10,WRITE_RETURN=7,MUT=0)(
 input wire clk,rst_n,
 input wire [16:0] su_rq,                // {v,sector16}
 input wire [280:0] su_wq,               // {v,sector16,data256,mask8}
 output wire [256:0] su_rr,              // {v,data256} at issue + READ_RETURN
 output wire su_w_done,
 output wire [16:0] lg_rq,output wire [280:0] lg_wq,
 input wire [256:0] lg_rr,input wire lg_w_done,
 output reg fault
);
 reg rcal[0:READ_RETURN];   // rcal[k] (as seen before an edge) = request sampled k edges earlier
 reg wcal[0:WRITE_RETURN];
 function automatic ok(input [15:0] s);
  ok=!s[15]&&s[14:13]==2'(QID)&&s[2:0]==3'(B);
 endfunction
 wire [15:0] sec=su_rq[15:0];
 assign lg_rq={su_rq[16],MUT!=0?{sec[15],2'(QID^1),sec[12:0]}:sec};
 assign lg_wq=su_wq;
 assign su_rr=lg_rr;
 assign su_w_done=lg_w_done;
 integer i;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   fault<=0;for(i=0;i<=READ_RETURN;i=i+1)rcal[i]<=0;for(i=0;i<=WRITE_RETURN;i=i+1)wcal[i]<=0;
  end else begin
   for(i=1;i<=READ_RETURN;i=i+1)rcal[i]<=rcal[i-1];
   for(i=1;i<=WRITE_RETURN;i=i+1)wcal[i]<=wcal[i-1];
   rcal[0]<=su_rq[16];wcal[0]<=su_wq[280];
   if(su_rq[16]&&!ok(su_rq[15:0]))fault<=1;
   if(su_wq[280]&&!ok(su_wq[279:264]))fault<=1;
   // the LG leaf presents the return READ_RETURN edges after sampling the request (WRITE_RETURN for done)
   if(lg_rr[256]!==rcal[READ_RETURN])fault<=1;
   if(lg_w_done!==wcal[WRITE_RETURN])fault<=1;
  end
endmodule

module ot_hbm_su_static_vm_ports #(parameter integer QID=0,READ_RETURN=10,WRITE_RETURN=7,MUT=0,NPG=4,
                                   parameter [31:0] BANK_GROUP=32'h3322_1100)(
 input wire [NPG-1:0] pg_clk,            // one compensated clock entry per port group (same edge/phase)
 input wire rst_n,
 input wire [8*17-1:0] su_rq,input wire [8*281-1:0] su_wq,
 output wire [8*257-1:0] su_rr,output wire [7:0] su_w_done,
 output wire [8*17-1:0] lg_rq,output wire [8*281-1:0] lg_wq,
 input wire [8*257-1:0] lg_rr,input wire [7:0] lg_w_done,
 output wire [NPG-1:0] fault
);
 wire [7:0] bf;
 for(genvar b=0;b<8;b=b+1)begin:g_bank
  localparam integer G=BANK_GROUP[4*b+:4];
  if(G>=NPG)begin:g_bad ot_hbm_su_static_vm_ports_BANK_GROUP_exceeds_NPG u_trap();end
  ot_hbm_su_static_vm_bank_leaf #(.QID(QID),.B(b),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) leaf(
   .clk(pg_clk[G]),.rst_n(rst_n),.su_rq(su_rq[b*17+:17]),.su_wq(su_wq[b*281+:281]),
   .su_rr(su_rr[b*257+:257]),.su_w_done(su_w_done[b]),
   .lg_rq(lg_rq[b*17+:17]),.lg_wq(lg_wq[b*281+:281]),.lg_rr(lg_rr[b*257+:257]),.lg_w_done(lg_w_done[b]),
   .fault(bf[b]));
 end
 for(genvar g=0;g<NPG;g=g+1)begin:g_pg
  wire [7:0] mine;
  for(genvar b=0;b<8;b=b+1)begin:g_m assign mine[b]=(BANK_GROUP[4*b+:4]==g)&&bf[b];end
  assign fault[g]=|mine;
  // every group must own at least one bank (no empty clock root / pin cluster)
  if(!((BANK_GROUP[3:0]==g)||(BANK_GROUP[7:4]==g)||(BANK_GROUP[11:8]==g)||(BANK_GROUP[15:12]==g)||
       (BANK_GROUP[19:16]==g)||(BANK_GROUP[23:20]==g)||(BANK_GROUP[27:24]==g)||(BANK_GROUP[31:28]==g)))begin:g_empty
   ot_hbm_su_static_vm_ports_empty_group u_trap();
  end
 end
endmodule
`default_nettype wire
