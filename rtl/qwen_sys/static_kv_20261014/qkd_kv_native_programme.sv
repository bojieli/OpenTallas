`timescale 1ns/1ps
// Writer-only fixed programme: boot writes 36*5 cycle32 roots, then QKVPRG36.
// Every cycle is relative to accepted start (segment0 core-start interval).
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
 reg[31:0]t0,t1,t2,t3,stop_q;
 reg[5:0]stage_q;reg[7:0]next_cfg;
 reg[5:0]cfg_stage;reg[2:0]cfg_word;
 reg[31:0]table0[0:35],table1[0:35],table2[0:35],table3[0:35],table_stop[0:35];
 wire accept_cfg=cfg_we&&!active&&!configured&&!fault&&cfg_addr==next_cfg;
 // These 5760 boot roots are fully written before global seal; their data
 // flops do not require a reset network. The valid/seal state is reset.
 genvar g;
 generate for(g=0;g<36;g=g+1)begin:g_stage
  always @(posedge ck)if(accept_cfg&&cfg_addr<180&&cfg_stage==g)begin
   case(cfg_word)
    0:table0[g]<=cfg_data[31:0];1:table1[g]<=cfg_data[31:0];
    2:table2[g]<=cfg_data[31:0];3:table3[g]<=cfg_data[31:0];
    4:table_stop[g]<=cfg_data[31:0];
   endcase
  end
 end endgenerate
 wire[5:0]selected_stage=(MUT==5)?((stage==36)?6'd1:stage+6'd1):stage;
 reg[58:0]identity_q;reg[1:0]generation_q;
 wire s0=cycle==(t0-((MUT==2)?1:0)), s1=cycle==t1, s2=cycle==t2, s3=cycle==t3;
 wire slot=active&&(s0||s1||s2||s3);
 assign compiled_word_slot=slot;
 assign kvn_word_slot=slot;
 wire[1:0]index=s0?2'd0:s1?2'd1:s2?2'd2:2'd3;
 assign compiled_word_index=index ^ ((MUT==3)?2'd1:2'd0);
 assign compiled_identity=identity_q ^ ((MUT==1)?(59'd1<<43):((MUT==6)?(59'd1<<37):59'd0));
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
   cycle<=0;fault<=0;pending<=0;kind_q<=0;expected_valid<=0;
   expected_pc<=0;expected_stack<=0;expected_identity<=0;
   expected_generation<=0;expected_address<=0;
  end else begin
   done<=0;expected_valid<=0;
   pending<=slot&&index[0];
   if(slot&&index[0])kind_q<=index[1];
   if(pending)begin
    expected_valid<=4'hf;
    expected_identity<=identity_q;expected_generation<=generation_q;
    expected_stack<=pos[8:7];
    expected_pc<={group_q,2'd3,group_q,2'd2,group_q,2'd1,group_q,2'd0};
    expected_address<={19'd64+{13'd0,stage_q-6'd1},kind_q,1'b0,pos[6],pos[4:3],pos[12:9],pos[5]} ^ ((MUT==4)?29'd1:29'd0);
   end
   if(cfg_we)begin
    if(!accept_cfg)fault<=1;
    else if(cfg_addr<180)begin
     next_cfg<=next_cfg+1'b1;
     if(cfg_data[63:32]!=0)fault<=1;
     if(cfg_word==4)begin
      if(table0[cfg_stage]<4||table0[cfg_stage]>=table1[cfg_stage]||
         table1[cfg_stage]>=table2[cfg_stage]||table2[cfg_stage]>=table3[cfg_stage]||
         cfg_data[31:0]<=table3[cfg_stage]||cfg_data[31:0]-table3[cfg_stage]<3)fault<=1;
      cfg_word<=0;cfg_stage<=cfg_stage+1'b1;
     end else cfg_word<=cfg_word+1'b1;
    end else if(cfg_addr==180&&cfg_data==64'h514b565052473336&&cfg_stage==36&&cfg_word==0)
     configured<=1;
    else fault<=1;
   end
   if(start)begin
    if(!configured||active||fault||cfg_we||stage<1||stage>36)fault<=1;
    else begin
     active<=1;cycle<=0;stage_q<=stage;
     t0<=table0[selected_stage-1'b1];t1<=table1[selected_stage-1'b1];
     t2<=table2[selected_stage-1'b1];t3<=table3[selected_stage-1'b1];stop_q<=table_stop[selected_stage-1'b1];
     identity_q<={epoch,stage,token,position,6'd0};
     generation_q<=generation;
    end
   end else if(active)begin
    cycle<=cycle+1'b1;
    if(cycle==stop_q)begin active<=0;done<=1;end
    if(&cycle)begin active<=0;fault<=1;done<=1;end
   end
  end
 end
endmodule
