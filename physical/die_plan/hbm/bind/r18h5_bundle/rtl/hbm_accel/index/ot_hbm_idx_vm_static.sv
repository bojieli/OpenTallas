`default_nettype none
// Compiler-fixed local/mirror IDX read face. A descriptor at edge n produces
// a registered request; bank samples at n+1, responds n+7 (bank ABI n+6),
// and this face captures at n+8. No queue, credit, lease or runtime waiting.
// SID, bank ownership, and all eight capture edges belong to the compiler.
// RT_EXTRA: fixed extra round-trip edges between this face and the banks (the
// owning tile's vm_rq output and vm_rr input pin registers, +1 each = 2); the
// capture edge becomes n+8+RT_EXTRA. Default 0 = the historical n+8 face.
// DRST: 1 (default, historical) = every flop async-reset. 0 (idx_op successor,
// H-NETLIST/IDXP-OPQ 2026-10-16) = only control flops are reset (due, fault,
// request/result valid bits); tags, request sectors and result data are
// reset-free data flops, each consumed only under its reset valid bit. Same
// cycle timing and values on every valid-qualified field.
module ot_hbm_idx_vm_static #(
 parameter integer MUT=0,
 parameter integer RT_EXTRA=0,
 parameter integer DRST=1
)(
 input wire clk,rst_n,
 input wire [1:0] sid,
 input wire [135:0] read_slot, // eight {valid,mirror/global_sector15}
 input wire [127:0] read_tag,
 output wire [135:0] vm_rq,
 input wire [2055:0] vm_rr,
 output wire [2055:0] result,
 output reg [127:0] result_tag,
 output reg fault
);
 localparam integer D=8+RT_EXTRA;
 reg [7:0] due[0:D-1];
 reg [127:0] tags[0:D-1];
 wire [7:0] expected=due[(MUT==2)?D-2:D-1];
 generate if(DRST!=0) begin:g_rst
 reg [135:0] rq_q;
 reg [2055:0] res_q;
 assign vm_rq=rq_q;
 assign result=res_q;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   rq_q<=0;res_q<=0;result_tag<=0;fault<=0;
   for(integer d=0;d<D;d=d+1) begin due[d]<=0;tags[d]<=0;end
  end else begin
   for(integer d=1;d<D;d=d+1) begin due[d]<=due[d-1];tags[d]<=tags[d-1];end
   tags[0]<=read_tag;
   result_tag<=tags[(MUT==3)?D-2:D-1];
   for(integer b=0;b<8;b=b+1) begin
    // Remote main reads are illegal on this face, never silently remapped.
    due[0][b]<=read_slot[17*b+16];
    rq_q[17*b+:17]<=read_slot[17*b+:17];
    if(MUT==1 && read_slot[17*b+16]) rq_q[17*b+3]<=~read_slot[17*b+3];
    if(read_slot[17*b+16] && (read_slot[17*b+:3]!=3'(b) ||
      (!read_slot[17*b+15] && read_slot[17*b+13+:2]!=sid))) begin
     fault<=1;rq_q[17*b+16]<=0;due[0][b]<=0;
    end
    if(vm_rr[257*b+256]!=expected[b]) fault<=1;
    res_q[257*b+:257]<={expected[b] && vm_rr[257*b+256],vm_rr[257*b+:256]};
   end
  end
 end
 end else begin:g_nrst
 reg [7:0] rq_v,res_v;   // reset control
 reg [127:0] rq_s;       // reset-free request sectors
 reg [2047:0] res_d;     // reset-free result data
 for(genvar b=0;b<8;b=b+1) begin:g_pack
  assign vm_rq[17*b+:17]={rq_v[b],rq_s[16*b+:16]};
  assign result[257*b+:257]={res_v[b],res_d[256*b+:256]};
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   rq_v<=0;res_v<=0;fault<=0;
   for(integer d=0;d<D;d=d+1) due[d]<=0;
  end else begin
   for(integer d=1;d<D;d=d+1) due[d]<=due[d-1];
   for(integer b=0;b<8;b=b+1) begin
    // Remote main reads are illegal on this face, never silently remapped.
    due[0][b]<=read_slot[17*b+16];
    rq_v[b]<=read_slot[17*b+16];
    if(read_slot[17*b+16] && (read_slot[17*b+:3]!=3'(b) ||
      (!read_slot[17*b+15] && read_slot[17*b+13+:2]!=sid))) begin
     fault<=1;rq_v[b]<=0;due[0][b]<=0;
    end
    if(vm_rr[257*b+256]!=expected[b]) fault<=1;
    res_v[b]<=expected[b] && vm_rr[257*b+256];
   end
  end
 end
 always @(posedge clk) begin
  for(integer d=1;d<D;d=d+1) tags[d]<=tags[d-1];
  tags[0]<=read_tag;
  result_tag<=tags[(MUT==3)?D-2:D-1];
  for(integer b=0;b<8;b=b+1) begin
   rq_s[16*b+:16]<=read_slot[17*b+:16];
   if(MUT==1 && read_slot[17*b+16]) rq_s[16*b+3]<=~read_slot[17*b+3];
   res_d[256*b+:256]<=vm_rr[257*b+:256];
  end
 end
 end endgenerate
endmodule
`default_nettype wire
