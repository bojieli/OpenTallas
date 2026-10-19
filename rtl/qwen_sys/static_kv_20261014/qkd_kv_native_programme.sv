`timescale 1ns/1ps
// Writer-only fixed programme: boot writes 36*5 cycle32 roots, then QKVPRG36.
// Every cycle is relative to INTERNAL accepted start (segment0 core-start).
// External start and all roots enter pin flops one edge earlier.
// A single seal supports every layer and successive tokens without cfg/reset.
// Explicit boot flops have no inferred RAM read latency. No payload, valid,
// readiness, completion, credit or runtime search can move a slot.
// VMAP (KVJ-A 10-17): the independent expected descriptor follows the writer's
// map (qkd_kv_static_writer VMAP, PV16 V layout). 1 = a V row (kind 1) expects
// group {pos[5:4],pos[0]} and address low fields {pos[2:1]} / {pos[3]} in place
// of {pos[4:3]} / {pos[5]}; K rows are unchanged. 0 = the historical t[2:0] map.
// MUT 7 (VMAP=1 only): the V-row group drops pos[0] (expected PC wrong).
// KV-GRP-CTL/MU5 10-19 (SAFE checklist items 3 / 5; defaults keep every existing view unchanged):
//   SRAM 1: the 36 x 5 x 32 b root table (5,760 runtime-indexed flops) lives in one ot_sram_1r1w_128x256_m1_r2c2
//           (row = stage - 1, bits 32w+:32 = word w; boot words land one edge after the accept through the bit write
//           mask, as the flop table's wq pipeline).  The read is issued on the start_p edge (address selected_stage - 1,
//           the value sel_q takes); the macro's registered output is copied to t0..stop_q on the ld edge, exactly where
//           the flop table was read: 0 added cycles.
//   RCOPIES N > 1: N KEPT identical copies of reset_pin_n (family wire g_rc.rpv, ot_rst_split) for the synthesis
//           reset-relay split (physical/common_flow/ot_rst_copies.py); reset_pin_n stays copy 0.
// KV-SRAM-CTL 10-19 (mu6): CTLSRAM (SRAM 1 only) selects the root-row storage family; default 0 keeps the mu5 view.
//   0 = ot_sram_1r1w_128x256_m1_r2c2 (faces 9.98 contacts/um > 6); 1 = 3 x ctl_sram_1r1w_64x64_p192 (192 b >= 160 b);
//   2 = 2 x ctl_sram_1r1w_64x128_p192.  64 words >= the 36 rows used, same port / one-edge read / model, 0 added edges.
module qkd_kv_native_programme #(parameter integer MUT=0,parameter integer VMAP=0,parameter integer RCOPIES=1,parameter integer SRAM=0,
 parameter integer CTLSRAM=0)(
 input wire ck,rst_n,
 input wire cfg_we,input wire[7:0]cfg_addr,input wire[63:0]cfg_data,
 input wire start,input wire[5:0]stage,input wire[15:0]epoch,input wire[17:0]token,
 input wire[12:0]position,input wire[1:0]generation,
 output wire compiled_word_slot,output wire[1:0]compiled_word_index,
 output wire[58:0]compiled_identity,output wire[1:0]compiled_generation,
 output wire kvn_word_slot,
 output reg configured,active,done,fault,
 output reg[31:0]cycle,
 // Independent expected physical descriptors, two writer capture edges after
 // the compiled high-half interval. These do not read actual writer outputs.
 output reg[3:0]expected_valid,output reg[19:0]expected_pc,
 output reg[1:0]expected_stack,output reg[58:0]expected_identity,
 output reg[1:0]expected_generation,output reg[28:0]expected_address
);
 // p2 (Q-COMPUTE-ELEM r2 10-15): rst_n is a plain data pin flop (synchronous capture, hold-padded like every
 // other input; p1 FF hold -4.04 ps was rst_n -> this flop's async RESETN removal). Assertion now one edge after
 // rst_n falls (release unchanged: one edge). All internal reset pins are driven by this kept pin FF's Q.
 (* keep = "true" *) reg reset_pin_n;
 always @(posedge ck) reset_pin_n<=rst_n;
 generate if(RCOPIES>1)begin:g_rc
  (* keep = "true" *) reg[RCOPIES-2:0]rc_q;
  always @(posedge ck)rc_q<={(RCOPIES-1){rst_n}};
  (* keep = "true", ot_rst_split *) wire[RCOPIES-1:0]rpv={rc_q,reset_pin_n};
 end endgenerate
 // Every functional input first lands at a dedicated pin register. Valid
 // flags reset; captured data are consumed only with their matching valid.
 (* keep = "true" *) reg cfg_we_p,start_p;
 (* keep = "true" *) reg[7:0]cfg_addr_p;
 (* keep = "true" *) reg[63:0]cfg_data_p;
 (* keep = "true" *) reg[5:0]stage_p;
 (* keep = "true" *) reg[15:0]epoch_p;
 (* keep = "true" *) reg[17:0]token_p;
 (* keep = "true" *) reg[12:0]position_p;
 (* keep = "true" *) reg[1:0]generation_p;
 always @(posedge ck)begin
  cfg_addr_p<=cfg_addr;cfg_data_p<=cfg_data;
  stage_p<=stage;epoch_p<=epoch;token_p<=token;
  position_p<=position;generation_p<=generation;
 end
 always @(posedge ck or negedge reset_pin_n)
  if(!reset_pin_n)begin cfg_we_p<=0;start_p<=0;end
  else begin cfg_we_p<=cfg_we;start_p<=start;end
 reg[31:0]t0,t1,t2,t3,stop_q;
 reg[5:0]stage_q;reg[7:0]next_cfg;
 reg[5:0]cfg_stage;reg[2:0]cfg_word;
 reg[31:0]table0[0:35],table1[0:35],table2[0:35],table3[0:35],table_stop[0:35];
 wire accept_cfg=cfg_we_p&&!active&&!configured&&!fault&&cfg_addr_p==next_cfg;
 // These 5760 boot roots are fully written before global seal; their data
 // flops do not require a reset network. The valid/seal state is reset.
 // p2: the boot-table write is registered once (one-hot stage/word, data) and lands one edge after its accept
 // (p1 TT: accept_cfg + cfg_stage/cfg_word decode fanned out to 5,760 enables). Nothing reads a table entry
 // within one edge of its write: the cfg_word==4 check reads the shadow words below, and start needs the seal,
 // which is a later accepted write.
 reg wq_v;reg[35:0]wq_stage;reg[4:0]wq_word;reg[31:0]wq_data;
 always @(posedge ck or negedge reset_pin_n)
  if(!reset_pin_n)wq_v<=0;else wq_v<=accept_cfg&&cfg_addr_p<180;
 always @(posedge ck)begin
  wq_stage<=36'd1<<cfg_stage;wq_word<=5'd1<<cfg_word;wq_data<=cfg_data_p[31:0];
 end
 genvar g;
 generate if(SRAM==0)begin:g_ftw for(g=0;g<36;g=g+1)begin:g_stage
  always @(posedge ck)if(wq_v&&wq_stage[g])begin
   if(wq_word[0])table0[g]<=wq_data;
   if(wq_word[1])table1[g]<=wq_data;
   if(wq_word[2])table2[g]<=wq_data;
   if(wq_word[3])table3[g]<=wq_data;
   if(wq_word[4])table_stop[g]<=wq_data;
  end
 end end endgenerate
 // p2: shadow copies of the current stage's words 0..3 (the same values the table receives), read by the
 // cfg_word==4 ordering check instead of a 36-way table mux (p1: cfg_stage -> mux -> compares -> fault, 21 levels).
 reg[31:0]sh0,sh1,sh2,sh3;
 always @(posedge ck)if(accept_cfg&&cfg_addr_p<180)begin
  if(cfg_word==0)sh0<=cfg_data_p[31:0];if(cfg_word==1)sh1<=cfg_data_p[31:0];
  if(cfg_word==2)sh2<=cfg_data_p[31:0];if(cfg_word==3)sh3<=cfg_data_p[31:0];
 end
 wire[5:0]selected_stage=(MUT==5)?((stage_p==36)?6'd1:stage_p+6'd1):stage_p;
 reg[58:0]identity_q;reg[1:0]generation_q;
 // Predecode cycle+1 into output pin flops. The old implementation's
 // cycle==root interval is preserved exactly after internal accepted start.
 // p2: cycle+1 == t  <=>  cycle == t-1, with t-1 registered (tm*); the root row is loaded one edge after the
 // accepted start (ld) and tm* one edge after that. Exact because the boot check enforces t0 >= 4 (t0-1 >= 3 with
 // the MUT2 offset >= 2): the first edge that can match sees cycle >= 2, when tm* already hold the new row; the
 // ld edge (cycle 0, which can never match) is gated off; stale tm* (>= 2, or all-ones after reset) cannot equal
 // cycle 1.
 reg ld;reg[5:0]sel_q;reg[31:0]tm0,tm1,tm2,tm3;
 // root row read: flop table at sel_q (SRAM 0) or the macro row read on the start_p edge (SRAM 1)
 wire[31:0]rt0,rt1,rt2,rt3,rts;
 generate if(SRAM==0)begin:g_ft
  assign rt0=table0[sel_q];assign rt1=table1[sel_q];assign rt2=table2[sel_q];assign rt3=table3[sel_q];
  assign rts=table_stop[sel_q];
 end else begin:g_sr
  reg[5:0]wq_row;
  always @(posedge ck)wq_row<=cfg_stage;
  wire[255:0]rd;
  wire[5:0]r_row=selected_stage-6'd1;
  wire[255:0]w_d={96'd0,{5{wq_data}}};
  wire[255:0]w_m={96'd0,{32{wq_word[4]}},{32{wq_word[3]}},{32{wq_word[2]}},{32{wq_word[1]}},{32{wq_word[0]}}};
  if(CTLSRAM==0)begin:g_s0
  ot_sram_1r1w_128x256_m1_r2c2 u_rows(.clk(ck),.r_ce_in(start_p),.r_addr_in({1'b0,r_row}),.rd_out(rd),
   .w_ce_in(wq_v),.w_addr_in({1'b0,wq_row}),.wd_in(w_d),.w_mask_in(w_m),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  end else if(CTLSRAM==1)begin:g_s1
  ctl_sram_1r1w_64x64_p192 u_rows_b0(.clk(ck),.r_ce_in(start_p),.r_addr_in(r_row),.rd_out(rd[0+:64]),
   .w_ce_in(wq_v),.w_addr_in(wq_row),.wd_in(w_d[0+:64]),.w_mask_in(w_m[0+:64]));
  ctl_sram_1r1w_64x64_p192 u_rows_b1(.clk(ck),.r_ce_in(start_p),.r_addr_in(r_row),.rd_out(rd[64+:64]),
   .w_ce_in(wq_v),.w_addr_in(wq_row),.wd_in(w_d[64+:64]),.w_mask_in(w_m[64+:64]));
  ctl_sram_1r1w_64x64_p192 u_rows_b2(.clk(ck),.r_ce_in(start_p),.r_addr_in(r_row),.rd_out(rd[128+:64]),
   .w_ce_in(wq_v),.w_addr_in(wq_row),.wd_in(w_d[128+:64]),.w_mask_in(w_m[128+:64]));
  assign rd[255:192]=64'd0;
  end else begin:g_s2
  ctl_sram_1r1w_64x128_p192 u_rows_b0(.clk(ck),.r_ce_in(start_p),.r_addr_in(r_row),.rd_out(rd[0+:128]),
   .w_ce_in(wq_v),.w_addr_in(wq_row),.wd_in(w_d[0+:128]),.w_mask_in(w_m[0+:128]));
  ctl_sram_1r1w_64x128_p192 u_rows_b1(.clk(ck),.r_ce_in(start_p),.r_addr_in(r_row),.rd_out(rd[128+:128]),
   .w_ce_in(wq_v),.w_addr_in(wq_row),.wd_in(w_d[128+:128]),.w_mask_in(w_m[128+:128]));
  end
  assign rt0=rd[31:0];assign rt1=rd[63:32];assign rt2=rd[95:64];assign rt3=rd[127:96];assign rts=rd[159:128];
 end endgenerate
 always @(posedge ck or negedge reset_pin_n)
  if(!reset_pin_n)begin tm0<=~32'd0;tm1<=~32'd0;tm2<=~32'd0;tm3<=~32'd0;end
  else begin tm0<=t0-((MUT==2)?32'd2:32'd1);tm1<=t1-32'd1;tm2<=t2-32'd1;tm3<=t3-32'd1;end
 wire n0=!ld&&cycle==tm0,n1=!ld&&cycle==tm1;
 wire n2=!ld&&cycle==tm2,n3=!ld&&cycle==tm3;
 wire next_slot=n0||n1||n2||n3;
 wire[1:0]next_index=n0?2'd0:n1?2'd1:n2?2'd2:2'd3;
 (* keep = "true" *) reg word_slot_q,kvn_slot_q;
 (* keep = "true" *) reg[1:0]word_index_q;
 assign compiled_word_slot=word_slot_q;
 assign kvn_word_slot=kvn_slot_q;
 assign compiled_word_index=word_index_q;
 wire slot=word_slot_q;
 wire[1:0]index=word_index_q;
 assign compiled_identity=identity_q;
 assign compiled_generation=generation_q;
 reg pending;reg kind_q;
 function automatic[2:0]group_of(input[2:0]logical_group);
  case(logical_group)
   0:group_of=2;1:group_of=3;2:group_of=4;3:group_of=5;
   4:group_of=0;5:group_of=1;6:group_of=6;7:group_of=7;
  endcase
 endfunction
 wire[12:0]pos=identity_q[18:6];
 wire vm=(VMAP!=0)&&kind_q;                        // writer cvm: compiled row is V under PV16
 wire[2:0]grp_q=vm?{pos[5:4],pos[0]^((MUT==7)?1'b1:1'b0)}:pos[2:0];
 wire[2:0]group_q=group_of(grp_q);
 always @(posedge ck or negedge reset_pin_n)begin
  if(!reset_pin_n)begin
   t0<=0;t1<=0;t2<=0;t3<=0;stop_q<=0;stage_q<=0;next_cfg<=0;cfg_stage<=0;cfg_word<=0;ld<=0;sel_q<=0;
   identity_q<=0;generation_q<=0;configured<=0;active<=0;done<=0;
   cycle<=0;word_slot_q<=0;kvn_slot_q<=0;word_index_q<=0;fault<=0;pending<=0;kind_q<=0;expected_valid<=0;
   expected_pc<=0;expected_stack<=0;expected_identity<=0;
   expected_generation<=0;expected_address<=0;
  end else begin
   done<=0;expected_valid<=0;ld<=0;
   if(ld)begin
    t0<=rt0;t1<=rt1;t2<=rt2;t3<=rt3;stop_q<=rts;
   end
   word_slot_q<=0;kvn_slot_q<=0;
   if(active)begin
    word_slot_q<=next_slot;kvn_slot_q<=next_slot;
    word_index_q<=next_index ^ ((MUT==3)?2'd1:2'd0);
   end
   pending<=slot&&word_index_q[0];
   if(slot&&index[0])kind_q<=index[1];
   if(pending)begin
    expected_valid<=4'hf;
    expected_identity<=identity_q;expected_generation<=generation_q;
    expected_stack<=pos[8:7];
    expected_pc<={group_q,2'd3,group_q,2'd2,group_q,2'd1,group_q,2'd0};
    expected_address<={19'd64+{13'd0,stage_q-6'd1},kind_q,1'b0,pos[6],vm?pos[2:1]:pos[4:3],pos[12:9],vm?pos[3]:pos[5]} ^ ((MUT==4)?29'd1:29'd0);
   end
   if(cfg_we_p)begin
    if(!accept_cfg)fault<=1;
    else if(cfg_addr_p<180)begin
     next_cfg<=next_cfg+1'b1;
     if(cfg_data_p[63:32]!=0)fault<=1;
     if(cfg_word==4)begin
      if(sh0<4||sh0>=sh1||sh1>=sh2||sh2>=sh3||
         cfg_data_p[31:0]<=sh3||cfg_data_p[31:0]-sh3<3)fault<=1;
      cfg_word<=0;cfg_stage<=cfg_stage+1'b1;
     end else cfg_word<=cfg_word+1'b1;
    end else if(cfg_addr_p==180&&cfg_data_p==64'h514b565052473336&&cfg_stage==36&&cfg_word==0)
     configured<=1;
    else fault<=1;
   end
   if(start_p)begin
    if(!configured||active||fault||cfg_we_p||stage_p<1||stage_p>36)fault<=1;
    else begin
     active<=1;cycle<=0;stage_q<=stage_p;
     ld<=1;sel_q<=selected_stage-1'b1;   // p2: row read one edge later (see tm*)
     identity_q<={epoch_p,stage_p,token_p,position_p,6'd0} ^ ((MUT==1)?(59'd1<<43):((MUT==6)?(59'd1<<37):59'd0));
     generation_q<=generation_p;
    end
   end else if(active)begin
    cycle<=cycle+1'b1;
    if(!ld&&cycle==stop_q)begin active<=0;done<=1;end
    if(&cycle)begin active<=0;fault<=1;done<=1;end
   end
  end
 end
endmodule
