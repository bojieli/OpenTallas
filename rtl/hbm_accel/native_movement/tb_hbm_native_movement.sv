`timescale 1ns/1ps
module tb;
 reg [5:0] opcode=29;reg [1:0] dtype=2;reg [3:0] lane_mask=15,index_valid=15;
 reg [27:0] source_index=0;reg [7:0] source_select=0;
 reg [8191:0] a_data=0,b_data=0,c_data=0;reg [255:0] literal_data=0;
 reg sticky_fault=0,lease_required=0,lease_visible=0;
 wire [255:0] result;wire [1:0] result_type;wire [3:0] lane_fault;wire supported;
 integer checks=0;
 ot_hbm_native_movement #(.ENABLE(1)) dut(.*);
 wire [255:0] disabled_result;wire [1:0] disabled_type;wire [3:0] disabled_fault;wire disabled_supported;
 ot_hbm_native_movement off(.opcode(opcode),.dtype(dtype),.lane_mask(lane_mask),.source_index(source_index),
 .source_select(source_select),.index_valid(index_valid),.a_data(a_data),.b_data(b_data),.c_data(c_data),
 .literal_data(literal_data),.sticky_fault(sticky_fault),.lease_required(lease_required),.lease_visible(lease_visible),
 .result(disabled_result),.result_type(disabled_type),.lane_fault(disabled_fault),.supported(disabled_supported));
 task must(input bit ok,input [255:0] message_text);begin checks=checks+1;if(!ok)$fatal(1,"FAIL %s",message_text);end endtask
 initial begin
 a_data[0 +:64]=64'h0123456789abcdef;a_data[3*64 +:64]=64'hfedcba9876543210;
 b_data[0 +:64]=64'h8877665544332211;c_data[127*64 +:64]=64'h0102030405060708;
 source_index={7'd127,7'd0,7'd3,7'd0};source_select={2'd2,2'd1,2'd0,2'd0};#1;
 must(result=={64'h0102030405060708,64'h8877665544332211,64'hfedcba9876543210,64'h0123456789abcdef},"retained layout selection");
 must(lane_fault==0&&supported,"layout legal");must(!disabled_supported&&disabled_result==0&&disabled_fault==0,"default off");
 dtype=1;#1;must(result[63:0]==64'h89abcdef,"U32 high zero");
 dtype=0;#1;must(result[63:0]==64'h89abcdef,"F32 bits unchanged");
 dtype=3;#1;must(result[63:0]==64'hef,"U8 byte unchanged");
 dtype=2;opcode=27;literal_data={64'h8000000000000000,64'h7fffffffffffffff,64'hffffffffffffffff,64'h42};#1;
 must(result==literal_data,"CONST exact immediate bits");
 opcode=28;source_index={7'd127,7'd126,7'd125,7'd124};#1;
 must(result=={64'd127,64'd126,64'd125,64'd124},"IOTA ordered hardware ordinal");
 dtype=1;#1;must(lane_fault==15,"IOTA I64 only");
 opcode=26;dtype=2;#1;must(lane_fault==15,"LOAD before actual visibility");lease_visible=1;#1;must(lane_fault==0,"LOAD retained visible");
 opcode=37;sticky_fault=1;#1;must(lane_fault==15,"packet sticky fault blocks");
 sticky_fault=0;lease_required=1;lease_visible=0;#1;must(lane_fault==15,"packet lease hidden");
 lease_visible=1;#1;must(lane_fault==0,"packet actual visible no fault");
 opcode=36;dtype=0;source_index=0;source_select=0;a_data[63:0]=64'h80000000;#1;
 must(lane_fault==15,"assert minus zero false");a_data[63:0]=64'h7fc12345;#1;must(lane_fault==0,"assert NaN truth as source");
 opcode=29;index_valid=4'b1101;#1;must(lane_fault==2,"invalid dynamic index rejected");
 lane_mask=4'b0001;#1;must(result[255:64]==0&&lane_fault==0,"tail mask no phantom fault");
 opcode=17;#1;must(!supported&&result==0,"arithmetic owner not duplicated");
 $display("PASS native_movement checks=%0d",checks);$finish;
 end
endmodule
