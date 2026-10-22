`timescale 1ns/1ps
`default_nettype none
// Six dated descriptors through the existing F20 configuration protocol.
// Dates are sampled engine-start edges relative to local edge zero. Release is
// exclusive. All bank clients are reserved throughout active; no request arbiter.
module ot_hbm_su_indexed_scalar_f20_routed #(
 parameter integer READ_SAMPLE=11,WRITE_COMMIT=8,MUT_PHASE=0,NATIVE_BANKED=0,SEGMENTED96=0,
 parameter integer OUTBOUND_EDGES=0,RETURN_EDGES=0,
 parameter [7:0] TARGET=8'd180
)(input wire clk,rst_n,
 input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,
 input wire[255:0]cfg_data,input wire desc_v,input wire[11:0]desc_base,
 input wire[12:0]desc_limit,input wire[15:0]desc_loops,input wire launch_v,
 input wire[32*257-1:0]rr,
 output wire[32*17-1:0]rq,output wire[32*281-1:0]wq,
 output reg active,done,program_fault,output wire configured,target_fault,engine_fault,
 output reg[15:0]edge_index,output wire engine_busy,engine_done,
 output wire engine_start,output wire[119:0]descriptor,output wire active0,active1,reservation_active,output wire[31:0]bank_reserve
);
 wire we,raw_sv,sv;
 ot_hbm_gather_reserve_bit sv0(.clk(clk),.d(raw_sv),.q(sv));
 wire[2:0]resets;
 ot_rst_relay #(.REGIONS(3),.SYNC_STAGES(2),.TREE_STAGES(1)) reset_tree(.clk(clk),.rst_n_in(rst_n),.rst_n(resets));
 reg[OUTBOUND_EDGES+1:0]tail;
 always @(posedge clk or negedge resets[1])if(!resets[1])tail<=0;else tail<={tail[OUTBOUND_EDGES:0],active};
 assign reservation_active=active|(|tail);wire[7:0]wa,sb;wire[8:0]sl;wire[15:0]loops;wire[255:0]wd;
 ot_static_program_target #(.TARGET(TARGET),.PCW(3),.INSTALLED_ROWS(6)) target(
  .clk(clk),.clk_cap(clk),.rst_n(resets[0]),.tgt(TARGET),
  .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
  .program_active(reservation_active),.program_cfg_we(we),.program_cfg_addr(wa),.program_cfg_data(wd),
  .program_start_v(raw_sv),.program_start_base(sb),.program_start_limit(sl),.program_start_loops(loops),
  .configured(configured),.fault(target_fault));
 reg[2:0]pc;reg[3:0]last;wire[223:0]row;
 wire advance=active&&(edge_index>=2)&&(edge_index==row[151:136]-16'd3);
 wire final_row=({1'b0,pc}+1'b1==last);
 wire clear_active=active&&(edge_index>=2)&&(edge_index==row[151:136]-1'b1)&&final_row;
 wire set_active=sv&&!reservation_active&&sb<6&&sl<=6&&sl>sb&&loops==1;
 ot_hbm_gather_active_copy copy0(.clk(clk),.rst_n(resets[1]),.set(set_active),.clear(clear_active),.q(active0));
 ot_hbm_gather_active_copy copy1(.clk(clk),.rst_n(resets[1]),.set(set_active),.clear(clear_active),.q(active1));
 if(NATIVE_BANKED!=0)begin:g_local_rows
  for(genvar g=0;g<2;g=g+1)begin:group
   wire we_g,sv_g,adv_g;wire[7:0]wa_g;wire[111:0]wd_g;wire[2:0]start_g;
   ot_hbm_gather_field_group group0(.clk(clk),.we(we),.wa(wa),.wd(wd[g*112+:112]),
    .sv(raw_sv),.start_row(sb[2:0]),.advance(advance),.we_q(we_g),.wa_q(wa_g),.wd_q(wd_g),
    .sv_q(sv_g),.start_q(start_g),.advance_q(adv_g));
   for(genvar f=0;f<28;f=f+1)begin:field
    ot_hbm_gather_field_table field0(.clk(clk),.we(we_g),.wa(wa_g),.wd(wd_g[f*4+:4]),
     .sv(sv_g),.start_row(start_g),.advance(adv_g),.q(row[g*112+f*4+:4]));
   end
  end end else begin:g_flat_rows
  reg[223:0]rows[0:5];
  always @(posedge clk)if(we&&wa<6&&!active)rows[wa]<=wd[223:0];
  assign row=rows[pc];
 end
 reg row_entry;
 assign descriptor=row[119:0];
 wire start_aux;
 (* keep *) ot_hbm_gather_start_test #(.NATIVE(NATIVE_BANKED)) start0(.active(active),.edge_index(edge_index),.date(row[135:120]),.q(engine_start));
 (* keep *) ot_hbm_gather_start_test #(.NATIVE(NATIVE_BANKED)) start1(.active(active),.edge_index(edge_index),.date(row[135:120]),.q(start_aux));
 localparam integer MIN_RELEASE=2*READ_SAMPLE+WRITE_COMMIT+7;
 always @(posedge clk or negedge resets[1])begin
  if(!resets[1])begin active<=0;done<=0;program_fault<=0;edge_index<=0;pc<=0;last<=0;row_entry<=0;end
  else begin
   done<=0;edge_index<=sv?16'd0:edge_index+1'b1;
   if(we)begin
    if(reservation_active || wa>=6 || (SEGMENTED96==0&&wd[223:152]!=0) || (NATIVE_BANKED!=0&&wd[135:120]<2) || wd[151:136]<{1'b0,wd[135:120]}+MIN_RELEASE)
     program_fault<=1;

   end
   if(sv)begin
    if(reservation_active || sb>=6 || sl>6 || sl<=sb || loops!=1)program_fault<=1;
    else begin active<=1;edge_index<=0;pc<=sb[2:0];last<=sl[3:0];row_entry<=0;end
   end
   if(active)begin
    if(row_entry)begin if(row[135:120]<edge_index)program_fault<=1;row_entry<=0;end
    if(engine_start && engine_busy)program_fault<=1;
    if(edge_index==row[151:136]-1'b1)begin
     if(engine_busy && !engine_done)program_fault<=1;
     if({1'b0,pc}+1'b1==last)begin active<=0;done<=1;end
     else begin
      pc<=pc+1'b1;
      // No hidden wait: overlapping or backwards dates are a programme fault.
      row_entry<=1;
     end
    end
    if(edge_index==16'hffff)begin active<=0;program_fault<=1;end
   end
  end
 end
 if(NATIVE_BANKED!=0)begin:g_banked
 ot_hbm_su_indexed_scalar_banked_routed #(.READ_SAMPLE(READ_SAMPLE),.WRITE_COMMIT(WRITE_COMMIT),.SEGMENTED96(SEGMENTED96),.MUT_PHASE(MUT_PHASE),.OUTBOUND_EDGES(OUTBOUND_EDGES),.RETURN_EDGES(RETURN_EDGES)) engine(
  .clk(clk),.rst_n(resets[2]),.start(engine_start),.start_aux(start_aux),
  .index_word(descriptor[23:0]),.score_base(descriptor[47:24]),.score_limit(descriptor[71:48]),
  .dest_word(descriptor[95:72]),.dyn_mul(descriptor[119:96]),.extra_bases(row[223:152]),.reserve0(active0),.reserve1(active1),.bank_reserve(bank_reserve),.rr(rr),.rq(rq),.wq(wq),
  .busy(engine_busy),.done(engine_done),.fault(engine_fault));
 end else begin:g_original
 assign bank_reserve=32'd0;
 ot_hbm_su_indexed_scalar #(.READ_SAMPLE(READ_SAMPLE),.WRITE_COMMIT(WRITE_COMMIT),.MUT_PHASE(MUT_PHASE)) engine(
  .clk(clk),.rst_n(resets[2]),.start(engine_start),
  .index_word(descriptor[23:0]),.score_base(descriptor[47:24]),.score_limit(descriptor[71:48]),
  .dest_word(descriptor[95:72]),.dyn_mul(descriptor[119:96]),.rr(rr),.rq(rq),.wq(wq),
  .busy(engine_busy),.done(engine_done),.fault(engine_fault));
 end
endmodule
`default_nettype wire
