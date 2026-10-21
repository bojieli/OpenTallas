`timescale 1ns/1ps
`default_nettype none
// Optional scalar VM adapter for selected L0 broadcast / indexed gather.
// NOT instantiated by the existing die. Integration must give it a real VM
// calendar owner, route its request/return ports, and arbitrate RF ingress.
// One fixed slot at a time; busy is diagnostic, never backpressure.
// Requests are sampled on the edge with vm_read_v=1; return is sampled exactly
// READ_RETURN later. Missing/early/extra returns latch fault. All addresses
// are VM WORD addresses; placement translation is outside this adapter.
// Indexed mode reads live I, computes base+U32(I)*INDEX_MUL, then reads A.
// Broadcast mode reads A directly; rr_wd broadcasts the live selected word
// into the reserved eight-word RF sector. Gather writes ONE masked VM word.
module ot_hbm_vm_scalar_runtime_1021 #(
 parameter integer READ_RETURN=18,
 parameter [31:0] INDEX_MUL=32'd1
)(
 input wire clk,rst_n,
 input wire cmd_v,cmd_indexed,cmd_to_rf,
 input wire [23:0] cmd_base_word,cmd_index_word,cmd_destination_word,
 input wire [4:0] cmd_rf_sector,
 output wire busy,
 output wire vm_read_v,output wire [20:0] vm_read_sector,
 input wire vm_return_v,input wire [255:0] vm_return_data,
 output reg vm_write_v,output reg [20:0] vm_write_sector,
 output reg [7:0] vm_write_mask,output reg [255:0] vm_write_data,
 output reg rr_wv,output reg [4:0] rr_wa,output reg [255:0] rr_wd,
 output reg done,output reg fault
);
 localparam IDLE=0,INDEX_REQ=1,INDEX_WAIT=2,ADDRESS_MUL=3,
            ADDRESS_ADD=4,DATA_REQ=5,DATA_WAIT=6;
 reg [2:0] state;
 integer remain;
 reg [23:0] base_word,index_word,destination_word,source_word;
 reg [4:0] rf_sector;
 reg to_rf;
 reg [31:0] index_value;
 reg [63:0] product;
 wire [64:0] runtime_address={1'b0,product}+{41'd0,base_word};
 assign busy=state!=IDLE;
 assign vm_read_v=state==INDEX_REQ||state==DATA_REQ;
 assign vm_read_sector=(state==INDEX_REQ)?index_word[23:3]:source_word[23:3];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=IDLE;remain<=0;vm_write_v<=0;rr_wv<=0;done<=0;fault<=0;
  end else begin
   vm_write_v<=0;rr_wv<=0;done<=0;
   if(cmd_v&&state!=IDLE)fault<=1;
   if(vm_return_v&&!((state==INDEX_WAIT||state==DATA_WAIT)&&remain==0))fault<=1;
   case(state)
    IDLE:if(cmd_v)begin
     base_word<=cmd_base_word;index_word<=cmd_index_word;
     destination_word<=cmd_destination_word;rf_sector<=cmd_rf_sector;
     source_word<=cmd_base_word;to_rf<=cmd_to_rf;
     state<=cmd_indexed?INDEX_REQ:DATA_REQ;
    end
    INDEX_REQ:begin remain<=READ_RETURN-1;state<=INDEX_WAIT;end
    INDEX_WAIT:if(remain!=0)remain<=remain-1;
     else if(!vm_return_v)begin fault<=1;state<=IDLE;done<=1;end
     else begin index_value<=vm_return_data[index_word[2:0]*32+:32];state<=ADDRESS_MUL;end
    ADDRESS_MUL:begin product<=index_value*INDEX_MUL;state<=ADDRESS_ADD;end
    ADDRESS_ADD:if(|runtime_address[64:24])begin fault<=1;state<=IDLE;done<=1;end
     else begin source_word<=runtime_address[23:0];state<=DATA_REQ;end
    DATA_REQ:begin remain<=READ_RETURN-1;state<=DATA_WAIT;end
    DATA_WAIT:if(remain!=0)remain<=remain-1;
     else begin
      done<=1;state<=IDLE;
      if(!vm_return_v)fault<=1;
      else if(to_rf)begin
       rr_wv<=1;rr_wa<=rf_sector;
       rr_wd<={8{vm_return_data[source_word[2:0]*32+:32]}};
      end else begin
       vm_write_v<=1;vm_write_sector<=destination_word[23:3];
       vm_write_mask<=8'd1<<destination_word[2:0];
       vm_write_data<=256'd0;
       vm_write_data[destination_word[2:0]*32+:32]<=vm_return_data[source_word[2:0]*32+:32];
      end
     end
    default:begin state<=IDLE;fault<=1;end
   endcase
  end
 end
endmodule
`default_nettype wire
