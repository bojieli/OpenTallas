`timescale 1ps/1fs
`default_nettype none
// Minimum real caller/provider composition, default OFF. No SM implementation,
// service controller, source arithmetic, generated clock, or timing exception.
// Prebuild: uarch_model.hbm_vm_publication_parent_model(). Frame matches Gibbs:
// job[31:0], gen[35:32], token[52:36], position[72:53].
module ot_hbm_vm_publication_parent #(parameter integer ENABLE=0)(
 input wire clk_sm,por_n,warm_req,
 input wire bind_v,output wire bind_r,input wire [72:0] bind_frame,
 input wire [6:0] bind_rank,input wire [31:0] bind_base,bind_span,
 input wire retire_v,output wire retire_r,input wire [72:0] retire_frame,
 output wire [72:0] held_frame,output wire retained,warm_ack,fault,
 input wire activation_wr_v,output wire activation_wr_r,
 input wire [72:0] activation_wr_frame,input wire activation_wr_bank,
 input wire [6:0] activation_wr_addr,input wire [2062:0] activation_wr_data,
 input wire [191:0] activation_wr_owner,
 output wire activation_ACK_v,input wire activation_ACK_r,
 output wire [72:0] activation_ACK_frame,output wire [191:0] activation_ACK_owner,
 input wire activation_rd_v,output wire activation_rd_r,
 input wire [72:0] activation_rd_frame,input wire activation_rd_bank,
 input wire [6:0] activation_rd_addr,input wire [191:0] activation_rd_owner,
 output wire [3:0] tap_v,input wire [3:0] tap_r,
 output wire [4*2063-1:0] tap_data,output wire [4*192-1:0] tap_owner,
 output wire [4*73-1:0] tap_frame,output wire [3:0] tap_source_clk,
 input wire [3:0] tap_ACK_v,output wire [3:0] tap_ACK_r,
 input wire [4*192-1:0] tap_ACK_owner,input wire [4*73-1:0] tap_ACK_frame,
 output wire activation_release,input wire activation_release_r,
 output wire [72:0] activation_release_frame,output wire [191:0] activation_release_owner,
 input wire su_pub_v,output wire su_pub_r,input wire [72:0] su_pub_frame,
 input wire [31:0] su_pub_addr,input wire [1023:0] su_pub_data,
 output wire su_ACK_v,input wire su_ACK_r,
 input wire result_pub_v,output wire result_pub_r,input wire [72:0] result_pub_frame,
 input wire [31:0] result_pub_addr,input wire [1023:0] result_pub_data,
 output wire result_ACK_v,input wire result_ACK_r,
 output wire [31:0] publication_ACK_addr,output wire [72:0] publication_ACK_frame,
 input wire index_read_v,output wire index_read_r,input wire [72:0] index_read_frame,
 input wire [6:0] index_read_rank,input wire [31:0] index_read_addr,
 input wire [5:0] index_read_words,input wire [7:0] index_read_tag,
 output wire index_rsp_v,input wire index_rsp_r,output wire [1023:0] index_rsp_data,
 output wire [7:0] index_rsp_tag,output wire [72:0] index_rsp_frame,
 output wire [6:0] index_rsp_rank
);
 generate if(!ENABLE)begin:off
  assign bind_r=0;assign retire_r=0;assign held_frame=0;assign retained=0;
  assign warm_ack=0;assign fault=0;assign activation_wr_r=0;assign activation_rd_r=0;
  assign activation_ACK_v=0;assign activation_ACK_frame=0;assign activation_ACK_owner=0;
  assign tap_v=0;assign tap_data=0;assign tap_owner=0;assign tap_frame=0;
  assign tap_source_clk=0;assign tap_ACK_r=0;assign activation_release=0;
  assign activation_release_frame=0;assign activation_release_owner=0;
  assign su_pub_r=0;assign su_ACK_v=0;assign result_pub_r=0;assign result_ACK_v=0;
  assign publication_ACK_addr=0;assign publication_ACK_frame=0;assign index_read_r=0;
  assign index_rsp_v=0;assign index_rsp_data=0;assign index_rsp_tag=0;
  assign index_rsp_frame=0;assign index_rsp_rank=0;
 end else begin:on
  wire [155:0] ctx;reg [155:0] ctx_next;
  wire cg,cc,cu,vg,vc,vu,pg,pc,pu;
  wire [255:0] row_valid;reg [255:0] valid_next;
  wire [1:0] pub;reg [1:0] pub_next;
  wire live=ctx[144],quarantine=ctx[145],sticky=ctx[146];
  wire [6:0] rank=ctx[79:73];wire [31:0] base=ctx[111:80],span=ctx[143:112];
  wire pending_activation=ctx[155];wire [7:0] activation_seat=ctx[154:147];
  assign held_frame=ctx[72:0];
  wire root_drained,root_fault,root_wr_r,root_rd_r,root_ACK_v;
  wire index_drained,index_fault,ibind_r,iwr_r,iACK_v,irsp_v,iread_r;
  wire [3:0] ack_iv,ack_or,ack_empty,ack_fault;
  wire [4*265-1:0] ack_data;
  wire good=cg&&vg&&pg;
  wire release_empty,release_fault,release_valid,release_ready,root_release;
  wire [265:0] release_data;
  wire all_drained=release_empty&&!root_release&&root_drained&&index_drained&&(&ack_empty)&&!pending_activation&&!pub[1];
  wire [32:0] bend={1'b0,bind_base}+{1'b0,bind_span};
  wire shape_bad=bind_rank>=96||bind_span==0||bind_span>16384||(|bind_base[4:0])||(|bind_span[4:0])||bend[32];
  wire wrong_live=live&&cg&&(
    (activation_wr_v&&activation_wr_frame!=held_frame)||
    (activation_rd_v&&activation_rd_frame!=held_frame)||
    (su_pub_v&&su_pub_frame!=held_frame)||(result_pub_v&&result_pub_frame!=held_frame)||
    (index_read_v&&(index_read_frame!=held_frame||index_read_rank!=rank))||
    (retire_v&&retire_frame!=held_frame));
  wire old_row=live&&good&&activation_rd_v&&activation_rd_frame==held_frame&&
                !row_valid[{activation_rd_bank,activation_rd_addr}];
  wire bad_bind=bind_v&&!live&&good&&!warm_req&&!quarantine&&all_drained&&shape_bad;
  reg wrong_ACK;
  always @*begin
   wrong_ACK=0;
   for(integer k=0;k<4;k=k+1)
    if(ack_iv[k]&&live&&cg&&ack_data[k*265+192+:73]!=held_frame)wrong_ACK=1;
  end
  assign fault=cu||vu||pu||sticky||root_fault||index_fault||(|ack_fault)||release_fault||(root_release&&release_data[265])||wrong_live||old_row||bad_bind||wrong_ACK;
  wire permission=live&&good&&!fault;
  wire admission=permission&&!warm_req&&!quarantine;
  assign retained=live||!good||fault;
  assign bind_r=good&&!live&&!fault&&!warm_req&&!quarantine&&all_drained&&ibind_r&&!shape_bad;
  wire bf=bind_v&&bind_r;
  assign retire_r=permission&&all_drained&&retire_frame==held_frame;
  assign warm_ack=good&&!fault&&quarantine&&!live&&all_drained;
  assign activation_wr_r=admission&&root_wr_r&&!pending_activation&&release_empty&&!root_release;
  assign activation_rd_r=admission&&root_rd_r&&!activation_wr_v&&release_empty&&!root_release&&row_valid[{activation_rd_bank,activation_rd_addr}];
  wire awv=activation_wr_v&&admission&&!pending_activation&&release_empty&&!root_release;
  wire arv=activation_rd_v&&admission&&!activation_wr_v&&release_empty&&!root_release&&row_valid[{activation_rd_bank,activation_rd_addr}];
  wire aw=activation_wr_v&&activation_wr_r;
  wire ar=activation_rd_v&&activation_rd_r;
  assign activation_ACK_v=permission&&root_ACK_v&&pending_activation;
  wire wa=activation_ACK_v&&activation_ACK_r;
  assign activation_ACK_frame=held_frame;
  wire [3:0] root_tap_v;
  assign tap_v=root_tap_v&{4{permission}};
  // These are the literal source root connections, not independent clocks or
  // measured receiver insertion. Gauss owns the five-slice forwarded wrapper.
  assign tap_source_clk={4{clk_sm}};
  for(genvar k=0;k<4;k=k+1)begin:receipts
   assign tap_frame[k*73+:73]=held_frame;
   wire ai;
   // Incoming reverse receipts preserve already accepted work during parent
   // metadata CE. They carry full frame+owner; validation waits for good.
   wire receive=live&&!cu&&!sticky&&!ack_fault[k];
   assign tap_ACK_r[k]=ai&&receive;
   ot_hbm_w2_protected_cut #(.W(265)) u_receipt(
    .clk(clk_sm),.por_n(por_n),.in_v(tap_ACK_v[k]&&receive),.in_r(ai),
    .in_d({tap_ACK_frame[k*73+:73],tap_ACK_owner[k*192+:192]}),
    .out_v(ack_iv[k]),.out_r(ack_or[k]),.out_d(ack_data[k*265+:265]),
    .empty(ack_empty[k]),.fault(ack_fault[k]));
   assign ack_or[k]=permission;
  end
  wire [4*192-1:0] root_ack_owner;
  for(genvar k=0;k<4;k=k+1)assign root_ack_owner[k*192+:192]=ack_data[k*265+:192];
  ot_hbm_die_vm_multicast_root #(.ENABLE(1)) u_activation(
   .clk(clk_sm),.por_n(por_n),.wr_v(awv),.wr_ready(root_wr_r),
   .wr_bank(activation_wr_bank),.wr_addr(activation_wr_addr),.wr_data(activation_wr_data),.wr_owner(activation_wr_owner),
   .wr_ACK_v(root_ACK_v),.wr_ACK_ready(wa),.wr_ACK_owner(activation_ACK_owner),
   .rd_v(arv),.rd_ready(root_rd_r),.rd_bank(activation_rd_bank),.rd_addr(activation_rd_addr),.rd_owner(activation_rd_owner),
   .tap_v(root_tap_v),.tap_ready(tap_r&{4{permission}}),.tap_data(tap_data),.tap_owner(tap_owner),
   .tap_ACK_v(ack_iv&ack_or),.tap_ACK_owner(root_ack_owner),
   .native_release(root_release),.drained(root_drained),.fault(root_fault));
  // The child release is a pulse and cannot be backpressured. A dedicated
  // coded seat captures that already owed receipt even while its empty word
  // repairs CE. New activation work waits for consumption, so no overwrite.
  reg [71:0] release_code[0:4];
  wire [319:0] release_raw;wire [4:0] release_ce,release_ue;
  for(genvar k=0;k<5;k=k+1)begin:release_decode
   wire [65:0] dec=ot_gpu_w6_secded_pkg::decode64(release_code[k]);
   assign release_raw[k*64+:64]=dec[63:0];
   assign release_ce[k]=dec[64];assign release_ue[k]=dec[65];
  end
  assign release_data=release_raw[265:0];
  assign release_fault=|release_ue;
  assign release_valid=release_data[265]&&!(|release_ce)&&!release_fault;
  assign release_empty=!release_data[265]&&!(|release_ce)&&!release_fault;
  assign release_ready=release_empty;
  assign activation_release=release_valid&&permission;
  assign activation_release_frame=release_data[264:192];
  assign activation_release_owner=release_data[191:0];
  wire [319:0] new_release={54'b0,1'b1,held_frame,tap_owner[191:0]};
  always @(posedge clk_sm or negedge por_n)begin
   if(!por_n)for(integer k=0;k<5;k=k+1)release_code[k]<=ot_gpu_w6_secded_pkg::encode64(0);
   else if(!release_fault)begin
    if(root_release&&!release_data[265])
     for(integer k=0;k<5;k=k+1)release_code[k]<=ot_gpu_w6_secded_pkg::encode64(new_release[k*64+:64]);
    else if(|release_ce)
     for(integer k=0;k<5;k=k+1)release_code[k]<=ot_gpu_w6_secded_pkg::encode64(release_raw[k*64+:64]);
    else if(activation_release&&activation_release_r)
     for(integer k=0;k<5;k=k+1)release_code[k]<=ot_gpu_w6_secded_pkg::encode64(0);
   end
  end
  // One existing SRAM write port: native SU publication wins the simultaneous
  // arbitration, result publication keeps its real valid/data until accepted.
  wire select_result=!su_pub_v;
  wire wr_candidate=admission&&!pub[1]&&(su_pub_v||result_pub_v);
  wire iw=wr_candidate&&iwr_r;
  assign su_pub_r=admission&&!pub[1]&&iwr_r;
  assign result_pub_r=admission&&!pub[1]&&!su_pub_v&&iwr_r;
  assign su_ACK_v=permission&&iACK_v&&pub[1]&&!pub[0];
  assign result_ACK_v=permission&&iACK_v&&pub[1]&&pub[0];
  wire pa=(su_ACK_v&&su_ACK_r)||(result_ACK_v&&result_ACK_r);
  assign publication_ACK_frame=held_frame;
  assign index_read_r=admission&&iread_r&&!pub[1]&&!su_pub_v&&!result_pub_v;
  wire read_candidate=index_read_v&&admission&&!pub[1]&&!su_pub_v&&!result_pub_v;
  assign index_rsp_v=permission&&irsp_v;
  assign index_rsp_frame=held_frame;
  wire [31:0] aj;wire [3:0] ag;wire [19:0] ap;wire [6:0] ak;
  wire [31:0] rj;wire [3:0] rg;wire [19:0] rp;
  ot_hbm_index_fp32_sram_adapter #(.ENABLE(1)) u_index(
   .clk(clk_sm),.por_n(por_n),.bind_v(bf),.bind_ready(ibind_r),
   .bind_base_word(bind_base),.bind_span_words(bind_span),.bind_job(bind_frame[31:0]),
   .bind_gen(bind_frame[35:32]),.bind_pos(bind_frame[72:53]),.bind_rank(bind_rank),.owner_held(),
   .wr_v(wr_candidate),.wr_ready(iwr_r),.wr_addr(select_result?result_pub_addr:su_pub_addr),
   .wr_data(select_result?result_pub_data:su_pub_data),.wr_job(held_frame[31:0]),
   .wr_gen(held_frame[35:32]),.wr_pos(held_frame[72:53]),.wr_rank(rank),
   .wr_ACK_v(iACK_v),.wr_ACK_ready(pa),.wr_ACK_addr(publication_ACK_addr),
   .wr_ACK_job(aj),.wr_ACK_gen(ag),.wr_ACK_pos(ap),.wr_ACK_rank(ak),.positive_publication_ACK(),
   .read_v(read_candidate),.read_r(iread_r),.read_addr(index_read_addr),.read_words(index_read_words),
   .read_tag(index_read_tag),.read_job(held_frame[31:0]),.read_gen(held_frame[35:32]),
   .read_pos(held_frame[72:53]),.read_rank(rank),
   .rsp_v(irsp_v),.rsp_r(index_rsp_r&&permission),.rsp_data(index_rsp_data),.rsp_tag(index_rsp_tag),
   .rsp_job(rj),.rsp_gen(rg),.rsp_pos(rp),.rsp_rank(index_rsp_rank),.drained(index_drained),.fault(index_fault));
  always @*begin
   ctx_next=ctx;valid_next=row_valid;pub_next=pub;
   if(warm_req)ctx_next[145]=1;
   else if(!live)ctx_next[145]=0;
   if(fault)ctx_next[146]=1;
   if(bf)begin
    ctx_next[143:0]={bind_span,bind_base,bind_rank,bind_frame};
    ctx_next[144]=1;ctx_next[155:147]=0;valid_next=0;pub_next=0;
   end
   if(aw)begin ctx_next[155]=1;ctx_next[154:147]={activation_wr_bank,activation_wr_addr};end
   if(wa)begin ctx_next[155]=0;valid_next[activation_seat]=1;end
   if(iw)pub_next={1'b1,select_result};
   if(pa)pub_next=0;
   if(retire_v&&retire_r)ctx_next[144]=0;
  end
  ot_hbm_accel_gu_metadata #(.WIDTH(156)) descriptor(
   .clk(clk_sm),.rst_n(por_n),.we(good&&ctx_next!=ctx),.next_data(ctx_next),.data(ctx),.good(cg),.ce(cc),.due(cu));
  ot_hbm_accel_gu_metadata #(.WIDTH(256)) validity(
   .clk(clk_sm),.rst_n(por_n),.we(good&&valid_next!=row_valid),.next_data(valid_next),.data(row_valid),.good(vg),.ce(vc),.due(vu));
  ot_hbm_accel_gu_metadata #(.WIDTH(2)) publisher(
   .clk(clk_sm),.rst_n(por_n),.we(good&&pub_next!=pub),.next_data(pub_next),.data(pub),.good(pg),.ce(pc),.due(pu));
 end endgenerate
endmodule
`default_nettype wire
