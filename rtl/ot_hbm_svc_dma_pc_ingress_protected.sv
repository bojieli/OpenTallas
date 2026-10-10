`timescale 1ns/1ps
// Additive, off-by-default protected CPU/controller tile. Model dbe2b9ed0.
// Four64b SECDED words per sector; paired metadata/control and finite decode
// publication debt. Native returns have no invented ready/backpressure port.
module ot_hbm_svc_dma_pc_ingress_protected #(
 parameter integer ENABLE=0,DEPTH=32,SLOT_BITS=6,PUB=4
)(
 input wire clk,rst,
 output wire reserve_ready,input wire reserve_take,input wire[1:0] reserve_bank,input wire[3:0] reserve_len,
 input wire in_v,input wire[1:0] in_bank,input wire[SLOT_BITS-1:0] in_slot,
 input wire[7:0] in_idx,input wire[255:0] in_data,input wire in_fault,in_epoch,
 input wire[3:0] write_ready,output wire out_v,output wire[1:0] out_bank,
 output wire[SLOT_BITS-1:0] out_slot,output wire[7:0] out_idx,
 output wire[255:0] out_data,output wire out_fault,out_epoch,output wire control_fault
);
 localparam CW=6,PW=5,MW=16;
 reg[CW-1:0]reserved[0:3],reserved_n[0:3],arrived[0:3],arrived_n[0:3],stored[0:3],stored_n[0:3];
 reg[PW-1:0]head[0:3],head_n[0:3],tail[0:3],tail_n[0:3];
 reg[287:0]payload[0:3][0:DEPTH-1];
 reg[MW-1:0]metadata[0:3][0:DEPTH-1],metadata_n[0:3][0:DEPTH-1];
 reg[1:0]turn,turn_n,pub_alloc,pub_alloc_n,pub_emit,pub_emit_n;
 reg[2:0]pub_used,pub_used_n;
 reg[17:0]enc_meta,enc_meta_n,pending_meta[0:1],pending_meta_n[0:1];
 reg enc_valid,enc_valid_n;
 reg[1:0]pending_valid,pending_valid_n;
 reg[255:0]pub_data[0:PUB-1],pub_data_n[0:PUB-1];
 reg[17:0]pub_meta[0:PUB-1],pub_meta_n[0:PUB-1];
 reg[PUB-1:0]pub_valid,pub_valid_n;
 reg sticky,sticky_n;
 reg[255:0]encoder_input;
 // always_comb establishes an initial event for the existing codec even for
 // a constant first zero word. This synthesizes to wires, with no logic cost.
 always_comb encoder_input=in_data;
 wire[287:0]encoded;wire[255:0]decoded;wire[3:0]dec_ov,dec_ce,dec_ue;
 integer b,j,k,need[0:3],selected,store_entry;
 reg bad,capacity;reg[287:0]decode_word;
 wire pop=out_v;
 wire launch=ENABLE&&!control_fault&&selected>=0&&pub_used<PUB;
 generate for(genvar w=0;w<4;w=w+1)begin:codec
 ot_secded_enc #(.K(64),.R(8))enc(.clk(clk),.d(encoder_input[w*64+:64]),.q(encoded[w*72+:72]));
 ot_secded_dec #(.K(64),.R(8))dec(.clk(clk),.rst_n(!rst),.v(launch),.w(decode_word[w*72+:72]),.ov(dec_ov[w]),.d(decoded[w*64+:64]),.ce(dec_ce[w]),.ue(dec_ue[w]),.n_ce(),.n_ue());
 end endgenerate
 always @*begin
 bad=(sticky!==~sticky_n)||(turn!==~turn_n)||(pub_alloc!==~pub_alloc_n)||(pub_emit!==~pub_emit_n)||(pub_used!==~pub_used_n)||pub_used>PUB||
     (enc_valid!==~enc_valid_n)||(enc_meta!==~enc_meta_n)||(pending_valid!==~pending_valid_n)||(pub_valid!==~pub_valid_n);
 for(b=0;b<4;b=b+1)begin
 if(reserved[b]!==~reserved_n[b]||arrived[b]!==~arrived_n[b]||stored[b]!==~stored_n[b]||head[b]!==~head_n[b]||tail[b]!==~tail_n[b]||reserved[b]>DEPTH||arrived[b]>reserved[b]||stored[b]>arrived[b])bad=1;
 for(j=0;j<DEPTH;j=j+1)if(metadata[b][j]!==~metadata_n[b][j])bad=1;
 end
 for(j=0;j<2;j=j+1)if(pending_meta[j]!==~pending_meta_n[j])bad=1;
 for(j=0;j<PUB;j=j+1)if(pub_valid[j]&&(pub_data[j]!==~pub_data_n[j]||pub_meta[j]!==~pub_meta_n[j]))bad=1;
 for(b=0;b<4;b=b+1)need[b]=0;
 for(j=0;j<4;j=j+1)if(j<reserve_len)need[(reserve_bank+j)&3]=need[(reserve_bank+j)&3]+1;
 capacity=reserve_len>=1&&reserve_len<=4;
 for(b=0;b<4;b=b+1)if(reserved[b]+need[b]>DEPTH)capacity=0;
 selected=-1;
 for(j=0;j<4;j=j+1)if(selected<0&&stored[(turn+j)&3]!=0)selected=(turn+j)&3;
 decode_word=0;if(selected>=0)decode_word=payload[selected][head[selected]];
 store_entry=(pub_alloc-pending_valid[0]-pending_valid[1])&(PUB-1);
 end
 assign control_fault=sticky||bad;
 assign reserve_ready=ENABLE&&!control_fault&&capacity;
 assign out_v=ENABLE&&!control_fault&&pub_valid[pub_emit]&&write_ready[pub_meta[pub_emit][17:16]];
 assign out_bank=pub_meta[pub_emit][17:16];
 assign {out_slot,out_idx,out_epoch,out_fault}=pub_meta[pub_emit][15:0];
 assign out_data=control_fault?256'd0:pub_data[pub_emit];
 initial if(DEPTH!=32||SLOT_BITS!=6||PUB!=4)$fatal(1,"Protected ingress modeled32depth/6slot/4publication only");
 always @(posedge clk)begin
 if(rst)begin
 sticky<=0;sticky_n<=1;turn<=0;turn_n<=~2'd0;pub_alloc<=0;pub_alloc_n<=~2'd0;pub_emit<=0;pub_emit_n<=~2'd0;pub_used<=0;pub_used_n<=~3'd0;
 enc_valid<=0;enc_valid_n<=1;enc_meta<=0;enc_meta_n<=~18'd0;pending_valid<=0;pending_valid_n<=~2'd0;pub_valid<=0;pub_valid_n<=~4'd0;
 for(k=0;k<4;k=k+1)begin
 reserved[k]<=0;reserved_n[k]<=~6'd0;arrived[k]<=0;arrived_n[k]<=~6'd0;stored[k]<=0;stored_n[k]<=~6'd0;
 head[k]<=0;head_n[k]<=~5'd0;tail[k]<=0;tail_n[k]<=~5'd0;
 for(j=0;j<DEPTH;j=j+1)begin payload[k][j]<=0;metadata[k][j]<=0;metadata_n[k][j]<=~16'd0;end
 end
 for(k=0;k<2;k=k+1)begin pending_meta[k]<=0;pending_meta_n[k]<=~18'd0;end
 for(k=0;k<PUB;k=k+1)begin pub_data[k]<=0;pub_data_n[k]<=~256'd0;pub_meta[k]<=0;pub_meta_n[k]<=~18'd0;end
 end else if(ENABLE)begin
 if(control_fault||(reserve_take&&!reserve_ready)||(in_v&&(arrived[in_bank]>=reserved[in_bank]+(reserve_take?need[in_bank]:0)||arrived[in_bank]>=DEPTH))||dec_ov!={4{pending_valid[1]}})begin sticky<=1;sticky_n<=0;end
 if(!control_fault)begin
 enc_valid<=in_v;enc_valid_n<=~in_v;
 if(in_v)begin enc_meta<={in_bank,in_slot,in_idx,in_epoch,in_fault};enc_meta_n<=~{in_bank,in_slot,in_idx,in_epoch,in_fault};end
 pending_valid<={pending_valid[0],launch};pending_valid_n<=~{pending_valid[0],launch};
 pending_meta[1]<=pending_meta[0];pending_meta_n[1]<=pending_meta_n[0];
 if(launch)begin pending_meta[0]<={2'(selected),metadata[selected][head[selected]]};pending_meta_n[0]<=~{2'(selected),metadata[selected][head[selected]]};end
 pub_used<=pub_used+launch-pop;pub_used_n<=~(3'(pub_used+launch-pop));
 for(k=0;k<4;k=k+1)begin
 reserved[k]<=reserved[k]+(reserve_take?need[k]:0)-(pop&&out_bank==k);reserved_n[k]<=~(6'(reserved[k]+(reserve_take?need[k]:0)-(pop&&out_bank==k)));
 arrived[k]<=arrived[k]+(in_v&&in_bank==k)-(pop&&out_bank==k);arrived_n[k]<=~(6'(arrived[k]+(in_v&&in_bank==k)-(pop&&out_bank==k)));
 stored[k]<=stored[k]+(enc_valid&&enc_meta[17:16]==k)-(launch&&selected==k);stored_n[k]<=~(6'(stored[k]+(enc_valid&&enc_meta[17:16]==k)-(launch&&selected==k)));
 end
 if(enc_valid)begin
 payload[enc_meta[17:16]][tail[enc_meta[17:16]]]<=encoded;
 metadata[enc_meta[17:16]][tail[enc_meta[17:16]]]<=enc_meta[15:0];metadata_n[enc_meta[17:16]][tail[enc_meta[17:16]]]<=enc_meta_n[15:0];
 tail[enc_meta[17:16]]<=tail[enc_meta[17:16]]+1;tail_n[enc_meta[17:16]]<=~(5'(tail[enc_meta[17:16]]+1));
 end
 if(launch)begin
 head[selected]<=head[selected]+1;head_n[selected]<=~(5'(head[selected]+1));turn<=selected+1;turn_n<=~(2'(selected+1));
 pub_alloc<=pub_alloc+1;pub_alloc_n<=~(2'(pub_alloc+1));
 end
 if(pending_valid[1])begin
 pub_data[store_entry]<=(|dec_ue)?256'd0:decoded;pub_data_n[store_entry]<=~((|dec_ue)?256'd0:decoded);
 pub_meta[store_entry]<={pending_meta[1][17:1],pending_meta[1][0]|(|dec_ue)};pub_meta_n[store_entry]<=~{pending_meta[1][17:1],pending_meta[1][0]|(|dec_ue)};
 pub_valid[store_entry]<=1;pub_valid_n[store_entry]<=0;
 end
 if(pop)begin pub_valid[pub_emit]<=0;pub_valid_n[pub_emit]<=1;pub_emit<=pub_emit+1;pub_emit_n<=~(2'(pub_emit+1));end
 end
 end
 end
endmodule
