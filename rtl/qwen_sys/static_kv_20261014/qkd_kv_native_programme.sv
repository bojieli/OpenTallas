`timescale 1ns/1ps
// Candidate writer-only fixed programme. Six ascending boot writes load four
// cycle32 roots, {reserved26,stage6,stop32}, then QKVPRG01. Small roots are
// explicit flops, not an inferred control-store macro. No payload, valid,
// readiness, completion, credit or runtime search can move a slot.
// cycle=0 is the interval immediately after accepted start. Receiver samples
// the slot at the following rising edge. Configuration is exceptional boot;
// reset is required to replace a sealed image. Root identity is captured once.
module qkd_kv_native_programme #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire cfg_we,input wire[2:0]cfg_addr,input wire[63:0]cfg_data,
 input wire start,input wire[15:0]epoch,input wire[17:0]token,
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
 reg[5:0]stage_q;reg[2:0]next_cfg;
 reg[58:0]identity_q;reg[1:0]generation_q;
 wire s0=cycle==(t0-((MUT==2)?1:0)), s1=cycle==t1, s2=cycle==t2, s3=cycle==t3;
 wire slot=active&&(s0||s1||s2||s3);
 assign compiled_word_slot=slot;
 assign kvn_word_slot=slot;
 wire[1:0]index=s0?2'd0:s1?2'd1:s2?2'd2:2'd3;
 assign compiled_word_index=index ^ ((MUT==3)?2'd1:2'd0);
 assign compiled_identity=identity_q ^ ((MUT==1)?(59'd1<<43):59'd0);
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
   t0<=0;t1<=0;t2<=0;t3<=0;stop_q<=0;stage_q<=0;next_cfg<=0;
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
    if(active||configured||cfg_addr!=next_cfg)fault<=1;
    else begin
     next_cfg<=next_cfg+1'b1;
     case(cfg_addr)
      0:begin t0<=cfg_data[31:0];if(cfg_data[63:32]!=0)fault<=1;end
      1:begin t1<=cfg_data[31:0];if(cfg_data[63:32]!=0)fault<=1;end
      2:begin t2<=cfg_data[31:0];if(cfg_data[63:32]!=0)fault<=1;end
      3:begin t3<=cfg_data[31:0];if(cfg_data[63:32]!=0)fault<=1;end
      4:begin stop_q<=cfg_data[31:0];stage_q<=cfg_data[37:32];if(cfg_data[63:38]!=0)fault<=1;end
      5:begin
       if(cfg_data!=64'h514b565052473031||t0<4||t0>=t1||t1>=t2||t2>=t3||
          stop_q<=t3||stop_q-t3<3||stage_q<1||stage_q>36||fault)fault<=1;
       else configured<=1;
      end
      default:fault<=1;
     endcase
    end
   end
   if(start)begin
    if(!configured||active||fault||cfg_we)fault<=1;
    else begin
     active<=1;cycle<=0;identity_q<={epoch,stage_q,token,position,6'd0};
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
