`timescale 1ns/1ps
// Writer-only fixed programme: boot writes 36*5 cycle32 roots, then QKVPRG36.
// Every cycle is relative to INTERNAL accepted start (segment0 core-start).
// External start and all roots enter pin flops one edge earlier.
// A single seal supports every layer and successive tokens without cfg/reset.
// Explicit boot flops have no inferred RAM read latency. No payload, valid,
// readiness, completion, credit or runtime search can move a slot.
module qkd_kv_native_programme #(parameter integer MUT=0)(
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
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin cfg_we_p<=0;start_p<=0;end
  else begin cfg_we_p<=cfg_we;start_p<=start;end
 reg[31:0]t0,t1,t2,t3,stop_q;
 reg[5:0]stage_q;reg[7:0]next_cfg;
 reg[5:0]cfg_stage;reg[2:0]cfg_word;
 reg[31:0]table0[0:35],table1[0:35],table2[0:35],table3[0:35],table_stop[0:35];
 wire accept_cfg=cfg_we_p&&!active&&!configured&&!fault&&cfg_addr_p==next_cfg;
 // These 5760 boot roots are fully written before global seal; their data
 // flops do not require a reset network. The valid/seal state is reset.
 genvar g;
 generate for(g=0;g<36;g=g+1)begin:g_stage
  always @(posedge ck)if(accept_cfg&&cfg_addr_p<180&&cfg_stage==g)begin
   case(cfg_word)
    0:table0[g]<=cfg_data_p[31:0];1:table1[g]<=cfg_data_p[31:0];
    2:table2[g]<=cfg_data_p[31:0];3:table3[g]<=cfg_data_p[31:0];
    4:table_stop[g]<=cfg_data_p[31:0];
   endcase
  end
 end endgenerate
 wire[5:0]selected_stage=(MUT==5)?((stage_p==36)?6'd1:stage_p+6'd1):stage_p;
 reg[58:0]identity_q;reg[1:0]generation_q;
 // Predecode cycle+1 into output pin flops. The old implementation's
 // cycle==root interval is preserved exactly after internal accepted start.
 wire[31:0]next_cycle=cycle+32'd1;
 wire n0=next_cycle==(t0-((MUT==2)?1:0)),n1=next_cycle==t1;
 wire n2=next_cycle==t2,n3=next_cycle==t3;
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
 wire[2:0]group_q=group_of(pos[2:0]);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   t0<=0;t1<=0;t2<=0;t3<=0;stop_q<=0;stage_q<=0;next_cfg<=0;cfg_stage<=0;cfg_word<=0;
   identity_q<=0;generation_q<=0;configured<=0;active<=0;done<=0;
   cycle<=0;word_slot_q<=0;kvn_slot_q<=0;word_index_q<=0;fault<=0;pending<=0;kind_q<=0;expected_valid<=0;
   expected_pc<=0;expected_stack<=0;expected_identity<=0;
   expected_generation<=0;expected_address<=0;
  end else begin
   done<=0;expected_valid<=0;
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
    expected_address<={19'd64+{13'd0,stage_q-6'd1},kind_q,1'b0,pos[6],pos[4:3],pos[12:9],pos[5]} ^ ((MUT==4)?29'd1:29'd0);
   end
   if(cfg_we_p)begin
    if(!accept_cfg)fault<=1;
    else if(cfg_addr_p<180)begin
     next_cfg<=next_cfg+1'b1;
     if(cfg_data_p[63:32]!=0)fault<=1;
     if(cfg_word==4)begin
      if(table0[cfg_stage]<4||table0[cfg_stage]>=table1[cfg_stage]||
         table1[cfg_stage]>=table2[cfg_stage]||table2[cfg_stage]>=table3[cfg_stage]||
         cfg_data_p[31:0]<=table3[cfg_stage]||cfg_data_p[31:0]-table3[cfg_stage]<3)fault<=1;
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
     t0<=table0[selected_stage-1'b1];t1<=table1[selected_stage-1'b1];
     t2<=table2[selected_stage-1'b1];t3<=table3[selected_stage-1'b1];stop_q<=table_stop[selected_stage-1'b1];
     identity_q<={epoch_p,stage_p,token_p,position_p,6'd0} ^ ((MUT==1)?(59'd1<<43):((MUT==6)?(59'd1<<37):59'd0));
     generation_q<=generation_p;
    end
   end else if(active)begin
    cycle<=cycle+1'b1;
    if(cycle==stop_q)begin active<=0;done<=1;end
    if(&cycle)begin active<=0;fault<=1;done<=1;end
   end
  end
 end
endmodule
