`timescale 1ns/1ps
// Actual frozen NC6 W2 component; C0 is client0, KV stays client5.
// One held return sidecar survives the W2 restore pipeline. All backend16 bits
// are retained. This does not fabricate the absent R14 full16 echo/quarantine.
module ot_hbm_w5_w2_pc_adapter #(parameter integer ENABLE=0,parameter [6:0] PC=0)(
 input wire clk,por_n,rst_n,admission_stop,rearm_v,provider_fenced,reset_fenced,
 output wire rearm_rdy,idle,output wire fault,
 input wire c0_req_v,output wire c0_req_r,input wire [38:0] c0_byte,input wire [91:0] c0_meta,
 output wire c0_rsp_v,input wire c0_rsp_r,output wire [91:0] c0_rsp_meta,
 output wire [15:0] c0_rsp_backend16,output wire [255:0] c0_rsp_data,
 input wire [4:0] other_req_v,other_req_we,output wire [4:0] other_req_r,
 input wire [169:0] other_addr,input wire [159:0] other_tag,input wire [19:0] other_gen,
 input wire [1279:0] other_data,input wire [459:0] other_meta,
 output wire [4:0] other_rsp_v,other_wr_done_v,input wire [4:0] other_rsp_r,other_wr_done_r,
 output wire [159:0] other_rsp_tag,other_wr_done_tag,output wire [19:0] other_rsp_gen,other_wr_done_gen,
 output wire [1279:0] other_rsp_data,
 output wire p_req_v,p_req_we,input wire p_req_r,
 output wire [33:0] p_req_addr,output wire [34:0] p_req_tag,output wire [3:0] p_req_gen,
 output wire [255:0] p_req_data,output wire [91:0] p_req_meta,
 input wire p_rsp_v,output wire p_rsp_r,input wire [34:0] p_rsp_tag,
 input wire [3:0] p_rsp_gen,input wire [255:0] p_rsp_data,
 input wire [91:0] p_rsp_meta,input wire [15:0] p_rsp_backend16,
 input wire p_wr_done_v,output wire p_wr_done_r,input wire [34:0] p_wr_done_tag,input wire [3:0] p_wr_done_gen
);
 wire [5:0] req_r,rsp_v,wr_v;wire [191:0] rsp_tags,wr_tags;
 wire [23:0] rsp_gens,wr_gens;wire [1535:0] rsp_data;
 wire kernel_fault,kernel_rsp_r;
 reg side_v,local_fault;reg [91:0] side_meta;reg [15:0] side_backend;
 wire legal_req=c0_byte<39'd81000000000 && c0_byte[4:0]==0 && c0_meta[91:85]==PC && c0_meta[84:82]==0;
 wire legal_side=p_rsp_tag[34:32]==0 && p_rsp_meta[91:85]==PC && p_rsp_meta[84:82]==0 &&
  p_rsp_tag[31:0]==p_rsp_meta[81:50] && p_rsp_gen==p_rsp_meta[49:46];
 wire side_match=side_v && rsp_tags[31:0]==side_meta[81:50] && rsp_gens[3:0]==side_meta[49:46];
 wire live=(ENABLE!=0) && por_n && !local_fault && !kernel_fault;
 wire returned_C0=p_rsp_tag[34:32]==0;
 wire side_ready=!side_v || !returned_C0;
 wire accepted_response=p_rsp_v && p_rsp_r;
 wire kernel_c0_ready=live && c0_rsp_r && side_match;
 assign c0_req_r=live && rst_n && legal_req && req_r[0];
 assign c0_rsp_v=live && rsp_v[0] && side_match;
 assign c0_rsp_meta=side_meta;assign c0_rsp_backend16=side_backend;assign c0_rsp_data=rsp_data[255:0];
 assign other_req_r=req_r[5:1];assign other_rsp_v=rsp_v[5:1];assign other_wr_done_v=wr_v[5:1];
 assign other_rsp_tag=rsp_tags[191:32];assign other_wr_done_tag=wr_tags[191:32];
 assign other_rsp_gen=rsp_gens[23:4];assign other_wr_done_gen=wr_gens[23:4];assign other_rsp_data=rsp_data[1535:256];
 assign p_rsp_r=live && side_ready && kernel_rsp_r;
 assign p_req_meta=(p_req_tag[34:32]==0)?c0_meta:other_meta[(p_req_tag[34:32]-1)*92+:92];
 assign fault=local_fault || kernel_fault;
 ot_hdc_qwen_pc_exact_completion #(.OPT_EXACT(ENABLE)) exact(
 .clk(clk),.rst_n(por_n),.admission_stop(admission_stop || !rst_n || local_fault),.rearm_v(rearm_v),.provider_fenced(provider_fenced),.reset_fenced(reset_fenced),.rearm_rdy(rearm_rdy),.idle(idle),
 .c_req_v({other_req_v,c0_req_v && legal_req && live && rst_n}),.c_req_we({other_req_we,1'b0}),.c_req_rdy(req_r),
 .c_req_addr({other_addr,c0_byte[38:5]}),.c_req_tag({other_tag,c0_meta[81:50]}),.c_req_gen({other_gen,c0_meta[49:46]}),.c_req_data({other_data,256'd0}),
 .c_rsp_v(rsp_v),.c_wr_done_v(wr_v),.c_rsp_rdy({other_rsp_r,kernel_c0_ready}),.c_wr_done_rdy({other_wr_done_r,1'b0}),
 .c_rsp_tag(rsp_tags),.c_wr_done_tag(wr_tags),.c_rsp_gen(rsp_gens),.c_wr_done_gen(wr_gens),.c_rsp_data(rsp_data),
 .p_req_v(p_req_v),.p_req_we(p_req_we),.p_req_rdy(p_req_r),.p_req_addr(p_req_addr),.p_req_tag(p_req_tag),.p_req_gen(p_req_gen),.p_req_data(p_req_data),
 .p_rsp_v(p_rsp_v && live && side_ready),.p_rsp_rdy(kernel_rsp_r),.p_rsp_tag(p_rsp_tag),.p_rsp_gen(p_rsp_gen),.p_rsp_data(p_rsp_data),
 .p_wr_done_v(p_wr_done_v),.p_wr_done_ready(p_wr_done_r),.p_wr_done_tag(p_wr_done_tag),.p_wr_done_gen(p_wr_done_gen),.fault(kernel_fault));
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin side_v<=0;local_fault<=0;side_meta<=0;side_backend<=0;end
  else begin
   if(live && c0_req_v && !legal_req) local_fault<=1;
   if(accepted_response && returned_C0) begin
    if(!legal_side) local_fault<=1;
    else begin side_v<=1;side_meta<=p_rsp_meta;side_backend<=p_rsp_backend16;end
   end
   if(c0_rsp_v && c0_rsp_r) side_v<=0;
   if(live && rsp_v[0] && !side_match) local_fault<=1;
  end
 end
endmodule
