// Actual RoPE73 native32 successor: two real SRAMs, kept per-slice controls, regional reset.
`timescale 1ns/1ps
// Structural native32 successor. Two registered ingress edges replace the old
// hardened view's one ingress + one egress wrapper edges. All core state planes
// see the same second-edge commands. Payload/counter controls are local kept
// copies; the row stays in the identical real SRAM. No credits or wait states.
// Active full-view latency equivalence and reset warmup require measured proof.
module qkd_embedding_row_tx_rope #(parameter integer MUT=0)(
 input wire ck,rst_n,fill_begin,
 input wire [17:0] fill_token,input wire [15:0] fill_epoch,input wire [12:0] fill_position,
 input wire word_v,input wire [511:0] word_data,input wire [17:0] word_token,
 input wire [5:0] word_index,input wire word_scale,input wire [15:0] word_epoch,
 input wire emb_tx_slot,
 output reg emb_tx_v,output reg [547:0] emb_tx_payload,output reg fault,
 output reg row_ready,output wire row_open
);
 localparam integer PAY=35,FILL=4,SCALE=39,MACRO=40,MAIN=41,CONTROLS=42;
 (* keep=1,dont_touch=1 *)reg [2:0] slot_first;
 (* keep=1,dont_touch=1 *)reg [1:0] fill_first;
 reg word_v_first,word_scale_first;
 (* keep=1,dont_touch=1 *)reg [5:0] index_first[0:4];
 reg [511:0] data_first,data_second;
 reg [17:0] token_first,token_second,ftok_first,ftok_second;
 reg [15:0] epoch_first,epoch_second,fep_first,fep_second;
 reg [12:0] pos_first,pos_second,pos;
 reg [7:0] rope_filled;
 (* keep=1,dont_touch=1 *)reg fill_rope;
 (* keep=1,dont_touch=1 *)reg [9:0] word_rope,rope_selected;
 reg [5:0] index_second;
 (* keep=1,dont_touch=1 *)reg [PAY-1:0] slot_payload;
 (* keep=1,dont_touch=1 *)reg [CONTROLS-1:0] slot_control,fill_control;
 (* keep=1,dont_touch=1 *)reg [3:0] fill_flags;
 (* keep=1,dont_touch=1 *)reg [2:0] fill_metadata;
 (* keep=1,dont_touch=1 *)reg [9:0] word_valid,word_is_scale;
 (* keep=1,dont_touch=1 *)reg [63:0] index_hot;
 always @(posedge ck)begin
  slot_first<={3{emb_tx_slot}};fill_first<={2{fill_begin}};
  word_v_first<=word_v;word_scale_first<=word_scale;
  for(integer i=0;i<5;i=i+1)index_first[i]<=word_index;
  pos_first<=fill_position;pos_second<=pos_first;
  fill_rope<=fill_first[0];
  word_rope<={10{token_first>=18'd151936}};
  rope_selected<={10{index_first[4][5:3]==pos[2:0]}};
  data_first<=word_data;data_second<=data_first;
  token_first<=word_token;token_second<=token_first;
  epoch_first<=word_epoch;epoch_second<=epoch_first;
  ftok_first<=fill_token;ftok_second<=ftok_first;
  fep_first<=fill_epoch;fep_second<=fep_first;
  index_second<=index_first[4];
  for(integer i=0;i<PAY;i=i+1)slot_payload[i]<=slot_first[i%3];
  for(integer i=0;i<CONTROLS;i=i+1)begin
   slot_control[i]<=slot_first[(i+PAY)%3];fill_control[i]<=fill_first[i%2];
  end
  for(integer i=0;i<4;i=i+1)fill_flags[i]<=fill_first[(i+CONTROLS)%2];
  for(integer i=0;i<3;i=i+1)fill_metadata[i]<=fill_first[(i+CONTROLS+4)%2];
  word_valid<={10{word_v_first}};word_is_scale<={10{word_scale_first}};
  for(integer i=0;i<64;i=i+1)index_hot[i]<=index_first[i/16]==6'(i);
 end
 // Reset is a registered face followed by two real regional relay levels.
 (* keep=1,dont_touch=1 *)reg [3:0] reset_face;
 // The old view observes two reset landing + body reset + egress capture (four
 // edges). Retiming those reset observations to ingress keeps assertion exact;
 // regional release adds six explicitly priced warmup edges.
 always @(posedge ck)reset_face<={reset_face[2:0],rst_n};
 wire [2:0] reset_roots;wire [47:0] reset_regions;
 ot_rst_relay #(.REGIONS(3)) u_reset_root(.clk(ck),.rst_n_in(reset_face[3]),.rst_n(reset_roots));
 for(genvar r=0;r<3;r=r+1)begin:g_reset
  ot_rst_relay #(.REGIONS(16)) u_leaf(.clk(ck),.rst_n_in(reset_roots[r]),.rst_n(reset_regions[r*16+:16]));
 end
 (* keep=1,dont_touch=1 *)reg [6:0] n_state[0:CONTROLS-1];
 (* keep=1,dont_touch=1 *)reg [CONTROLS-1:0] armed_state;
 for(genvar c=0;c<CONTROLS;c=c+1)begin:g_state
  always @(posedge ck or negedge reset_regions[c])
   if(!reset_regions[c])begin n_state[c]<=0;armed_state[c]<=0;end
   else begin
    if(slot_control[c])begin
     if(n_state[c]!=7'd73)n_state[c]<=n_state[c]+7'd1;
     if(n_state[c]==7'd72)armed_state[c]<=0;
    end
    if(fill_control[c])begin n_state[c]<=0;armed_state[c]<=1;end
   end
 end
 reg [63:0] filled;wire [63:0] filled_next;
 for(genvar g=0;g<4;g=g+1)begin:g_filled
  wire take_word=word_valid[g]&&!word_is_scale[g]&&!word_rope[g];
  assign filled_next[g*16+:16]=fill_flags[g]?16'd0:(filled[g*16+:16]|({16{take_word}}&index_hot[g*16+:16]));
  always @(posedge ck or negedge reset_regions[42+g])
   if(!reset_regions[42+g])filled[g*16+:16]<=0;
   else filled[g*16+:16]<=filled_next[g*16+:16];
 end
 reg [17:0] tok;reg [15:0] ep,scale;reg scale_filled;
 always @(posedge ck)begin
  if(fill_metadata[0])tok[15:0]<=ftok_second[15:0];
  if(fill_metadata[1])tok[17:16]<=ftok_second[17:16];
  if(fill_metadata[2])begin ep<=fep_second;pos<=pos_second;end
  if(word_valid[4]&&word_is_scale[4]&&!word_rope[4]&&armed_state[SCALE]&&n_state[SCALE]==0)scale<=data_second[15:0];
 end
 wire resident=armed_state[MAIN]&&(&filled)&&scale_filled&&(&rope_filled);
 wire [6:0] read_word=(MUT==3)?(n_state[MACRO]==0?7'd0:n_state[MACRO]-7'd1):n_state[MACRO];
 wire read_enable=slot_control[MACRO]&&n_state[MACRO]<7'd64;
 wire write_enable=word_valid[5]&&!word_is_scale[5]&&!word_rope[5]&&armed_state[MACRO]&&n_state[MACRO]==0;
 wire [511:0] memory_q;
 ot_sram_1r1w_64x512_m1_r2c2 u_row(
  .clk(ck),.r_ce_in(read_enable),.r_addr_in(read_word[5:0]),.rd_out(memory_q),
  .w_ce_in(write_enable),.w_addr_in(index_second),.wd_in(data_second),.w_mask_in({512{1'b1}}),
  .rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(18'd0));
 wire [511:0] rope_q;
 wire rope_read=slot_control[MACRO]&&n_state[MACRO]>=64&&n_state[MACRO]<72;
 wire rope_write=word_valid[7]&&word_rope[7]&&!word_is_scale[7]&&rope_selected[7]&&armed_state[MACRO]&&n_state[MACRO]==0;
 ot_sram_1r1w_64x512_m1_r2c2 u_rope(
  .clk(ck),.r_ce_in(rope_read),.r_addr_in(6'(n_state[MACRO]-64)),.rd_out(rope_q),
  .w_ce_in(rope_write),.w_addr_in({3'd0,index_second[2:0]}),.wd_in(data_second),.w_mask_in({512{1'b1}}),
  .rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(18'd0));
 always @(posedge ck or negedge reset_regions[47])
  if(!reset_regions[47])rope_filled<=0;
  else if(fill_rope)rope_filled<=0;
  else if(word_valid[8]&&word_rope[8]&&rope_selected[8]&&!word_is_scale[8])rope_filled[index_second[2:0]]<=1;
 wire [547:0] header={tok,6'd0,12'd0,464'd0,ep,16'd0,scale};
 for(genvar p=0;p<PAY;p=p+1)begin:g_payload
  localparam integer LO=p*16;
  localparam integer WIDTH=548-LO<16?548-LO:16;
  wire [5:0] word_out=(MUT==1)?n_state[p][5:0]:n_state[p][5:0]-6'd1;
  wire [547:0] body={tok,word_out,12'd0,memory_q};
  wire [547:0] rope_body={tok,6'(n_state[p]-65),11'd0,1'b1,rope_q};
  always @(posedge ck)if(slot_payload[p])
   emb_tx_payload[LO+:WIDTH]<=n_state[p]==0?header[LO+:WIDTH]:(n_state[p]>=65?rope_body[LO+:WIDTH]:body[LO+:WIDTH]);
 end
 wire [6:0] n_next=fill_control[MAIN]?7'd0:
  (slot_control[MAIN]&&n_state[MAIN]!=73?n_state[MAIN]+7'd1:n_state[MAIN]);
 wire armed_next=fill_control[MAIN]?1'b1:
  (slot_control[MAIN]&&n_state[MAIN]==72?1'b0:armed_state[MAIN]);
 wire scale_next=fill_control[MAIN]?1'b0:
  (word_valid[6]&&word_is_scale[6]&&!word_rope[6]?1'b1:scale_filled);
 wire duplicate_word=|(filled&index_hot);
 wire [17:0] expected_rope_token=18'd151936+{8'd0,pos[12:3]};
 assign row_open=(MUT==4)?row_ready:armed_state[MAIN];
 always @(posedge ck or negedge reset_regions[46])
  if(!reset_regions[46])begin emb_tx_v<=0;fault<=0;scale_filled<=0;row_ready<=0;end
  else begin
   emb_tx_v<=slot_control[MAIN];scale_filled<=scale_next;
   // Registered next-state observation matches the old combinational ready
   // followed by its egress pin register, after moving that edge to ingress.
   row_ready<=armed_next&&(&filled_next)&&scale_next&&(&rope_filled)&&n_next==0;
   if(word_valid[6])begin
    if(!armed_state[MAIN]||n_state[MAIN]!=0||fill_control[MAIN])fault<=1;
    if(token_second!=(word_rope[6]?expected_rope_token:tok)||epoch_second!=ep)fault<=1;
    if(word_rope[6])begin
     if(word_is_scale[6]||(rope_selected[6]&&rope_filled[index_second[2:0]]))fault<=1;
    end else if(word_is_scale[6])begin if(scale_filled)fault<=1;end
    else if(duplicate_word)fault<=1;
   end
   if(slot_control[MAIN])begin
    if(n_state[MAIN]==0&&!resident&&MUT!=2)fault<=1;
    if(!armed_state[MAIN]||n_state[MAIN]==65)fault<=1;
   end
   if(fill_control[MAIN])begin
    if(armed_state[MAIN]||(n_state[MAIN]!=0&&n_state[MAIN]!=73)||slot_control[MAIN]||ftok_second>=151936)fault<=1;
   end
  end
endmodule
