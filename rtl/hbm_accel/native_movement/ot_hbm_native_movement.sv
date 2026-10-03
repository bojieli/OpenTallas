`timescale 1ns/1ps
// Stateless data selection only. Pauli owns the ONE protected command/result
// holders, source-derived address generator, assertion/sticky fault, visibility
// authority and matching reverse. No tied READY, clock, lease mint or oracle.
// Prospective sizing: canonical_qwen_native_opcode_abi.movement_model().
module ot_hbm_native_movement #(
 parameter bit ENABLE=0
)(
 input wire [5:0] opcode,
 input wire [1:0] dtype,
 input wire [3:0] lane_mask,
 input wire [27:0] source_index,
 input wire [7:0] source_select,
 input wire [3:0] index_valid,
 input wire [8191:0] a_data,b_data,c_data,
 input wire [255:0] literal_data,
 input wire sticky_fault,
 input wire lease_required,
 input wire lease_visible,
 output reg [255:0] result,
 output wire [1:0] result_type,
 output reg [3:0] lane_fault,
 output wire supported
);
 // Global IDs preserve the independent Boole bits-engine IDs0..16.
 localparam [5:0] LOAD=26,CONST_OP=27,IOTA=28,RESHAPE=29,SLICE=30,
 TRANSPOSE=31,CONCAT_OP=32,BROADCAST=33,TAKE=34,SCATTER=35,
 ASSERT_OP=36,PACKET_COMMIT=37;
 assign result_type=dtype;
 assign supported=ENABLE&&(opcode>=LOAD&&opcode<=PACKET_COMMIT);
 integer i;
 reg [6:0] idx;
 reg [1:0] sel;
 reg [63:0] word_value;
 always @* begin
  result=0;lane_fault=0;idx=0;sel=0;word_value=0;
  for(i=0;i<4;i=i+1)begin
   if(supported&&lane_mask[i])begin
    idx=source_index[7*i +:7];sel=source_select[2*i +:2];
    word_value=0;
    if(opcode==CONST_OP)word_value=literal_data[64*i +:64];
    else if(opcode==IOTA)begin
     // Literal source arange is I64. The controller owns the ordered beat's
     // ordinal; it is not an arithmetic result supplied by a Python callback.
     word_value={57'd0,idx};
     if(dtype!=2)lane_fault[i]=1;
    end else begin
     case(sel)
      0:word_value=a_data[64*idx +:64];
      1:word_value=b_data[64*idx +:64];
      2:word_value=c_data[64*idx +:64];
      default:lane_fault[i]=1;
     endcase
    end
    if(!index_valid[i])lane_fault[i]=1;
    if(opcode==LOAD&&!lease_visible)lane_fault[i]=1;
    if(opcode==PACKET_COMMIT&&(sticky_fault||(lease_required&&!lease_visible)))lane_fault[i]=1;
    if(opcode==ASSERT_OP)begin
     if(dtype==0)begin
      if(word_value[30:0]==0)lane_fault[i]=1; // both signed zeros are false
     end else if(word_value==0)lane_fault[i]=1;
    end
    case(dtype)
     0,1:result[64*i +:64]={32'd0,word_value[31:0]};
     2:result[64*i +:64]=word_value;
     3:result[64*i +:64]={56'd0,word_value[7:0]};
    endcase
   end
  end
 end
endmodule
