// Additive protected fullNC6 canonical transport seam; default off.
// Functional qualification pending. No constant clean/fence/ready authorities.
module ot_gpu_w2_canonical_endpoint #(
 parameter integer OPT_EXACT=0, NC=6, MAX_OUT=16, AW=34,
 parameter integer CTAGW=32, GENW=4, SIDW=3, PTAGW=35,
 parameter logic [6:0] PC_ID=0
)(
 input wire clk,rst_n,admission_stop,rearm_v,provider_fenced,reset_fenced,
 output wire rearm_rdy,idle,
 input wire [NC-1:0] c_req_v,c_req_we,
 output wire [NC-1:0] c_req_rdy,
 input wire [NC*AW-1:0] c_req_addr,
 input wire [NC*CTAGW-1:0] c_req_tag,
 input wire [NC*GENW-1:0] c_req_gen,
 input wire [NC*256-1:0] c_req_data,
 output wire [NC-1:0] c_rsp_v,c_wr_done_v,
 input wire [NC-1:0] c_rsp_rdy,c_wr_done_rdy,
 output wire [NC*CTAGW-1:0] c_rsp_tag,c_wr_done_tag,
 output wire [NC*GENW-1:0] c_rsp_gen,c_wr_done_gen,
 output wire [NC*256-1:0] c_rsp_data,
 output wire p_req_v,p_req_we,
 input wire p_req_rdy,
 output wire [AW-1:0] p_req_addr,
 output wire [PTAGW-1:0] p_req_tag,
 output wire [GENW-1:0] p_req_gen,
 output wire [255:0] p_req_data,
 input wire p_rsp_v,p_wr_done_v,
 output wire p_rsp_rdy,p_wr_done_ready,
 input wire [PTAGW-1:0] p_rsp_tag,p_wr_done_tag,
 input wire [GENW-1:0] p_rsp_gen,p_wr_done_gen,
 input wire [255:0] p_rsp_data,
 output wire fault,repair_busy,
 input wire reverse_fenced,
 output wire[45:0] p_req_owner46,
 output wire[NC*46-1:0] c_rsp_owner46,c_wr_done_owner46,
 output wire service_admission_hold
);
 // Identity scope is DIE/STACK supplied by the caller's route. Preserve the
 // full original tag32 and source generation4. A 16-bit PHY ticket requires
 // its separate reversible live mapping, not a slice of this source identity.
 assign p_req_owner46={PC_ID,p_req_tag,p_req_gen};
 // Actual repair/fault outputs notify the caller/global admission owner.
 assign service_admission_hold=fault||repair_busy;
 genvar client;
 generate for(client=0;client<NC;client=client+1)begin:identity
  assign c_rsp_owner46[46*client+:46]={PC_ID,3'(client),c_rsp_tag[32*client+:32],c_rsp_gen[4*client+:4]};
  assign c_wr_done_owner46[46*client+:46]={PC_ID,3'(client),c_wr_done_tag[32*client+:32],c_wr_done_gen[4*client+:4]};
 end endgenerate
 initial begin
  if(NC!=6||MAX_OUT!=16||AW!=34||CTAGW!=32||GENW!=4||SIDW!=3||PTAGW!=35)
   $fatal(1,"canonical W2 fullwidth source geometry required");
 end
 // Exactly one full primary; it instantiates the actual 37CW secondary and
 // eight combinational correction engines. No parallel raw completion path.
 ot_w2_nc6_protected_completion #(.OPT_EXACT(OPT_EXACT),.NC(NC),.MAX_OUT(MAX_OUT),
  .AW(AW),.CTAGW(CTAGW),.GENW(GENW),.SIDW(SIDW),.PTAGW(PTAGW),.PC_ID(PC_ID)) controller(
.clk(clk),
.rst_n(rst_n),
.admission_stop(admission_stop),
.rearm_v(rearm_v),
.provider_fenced(provider_fenced),
.reset_fenced(reset_fenced),
.rearm_rdy(rearm_rdy),
.idle(idle),
.c_req_v(c_req_v),
.c_req_we(c_req_we),
.c_req_rdy(c_req_rdy),
.c_req_addr(c_req_addr),
.c_req_tag(c_req_tag),
.c_req_gen(c_req_gen),
.c_req_data(c_req_data),
.c_rsp_v(c_rsp_v),
.c_wr_done_v(c_wr_done_v),
.c_rsp_rdy(c_rsp_rdy),
.c_wr_done_rdy(c_wr_done_rdy),
.c_rsp_tag(c_rsp_tag),
.c_wr_done_tag(c_wr_done_tag),
.c_rsp_gen(c_rsp_gen),
.c_wr_done_gen(c_wr_done_gen),
.c_rsp_data(c_rsp_data),
.p_req_v(p_req_v),
.p_req_we(p_req_we),
.p_req_rdy(p_req_rdy),
.p_req_addr(p_req_addr),
.p_req_tag(p_req_tag),
.p_req_gen(p_req_gen),
.p_req_data(p_req_data),
.p_rsp_v(p_rsp_v),
.p_wr_done_v(p_wr_done_v),
.p_rsp_rdy(p_rsp_rdy),
.p_wr_done_ready(p_wr_done_ready),
.p_rsp_tag(p_rsp_tag),
.p_wr_done_tag(p_wr_done_tag),
.p_rsp_gen(p_rsp_gen),
.p_wr_done_gen(p_wr_done_gen),
.p_rsp_data(p_rsp_data),
.fault(fault),
.repair_busy(repair_busy),
.reverse_fenced(reverse_fenced)
 );
endmodule
