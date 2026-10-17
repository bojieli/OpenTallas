`timescale 1ns/1ps
// NEW exact HB specializations. Each body retains real24banks/25roots. No physical inheritance.
// BSTN=1: parent-root input stations (exact retiming; one ck-domain capture per primary input for the multi-root kit).
module qfd_res_train_half_b2_0(input wire ck,
input wire rst_n,
input wire [23:0] ck_bank,
input wire train_start,
input wire [3:0] train_count,
input wire [31:0] capture_stride,
input wire payload_write,
input wire [3:0] slot_count,
input wire [2212:0] rq,
output wire [550:0] rb,
output wire fault);
qfd_res_train_half_b2 #(.BAND(0),.NB(6),.D(2),.MAX_TRAIN(8),.MUT(0),.BSTN(1))u_native(.ck(ck),.rst_n(rst_n),.ck_bank(ck_bank),.train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),.slot_count(slot_count),.rq(rq),.rb(rb),.fault(fault));
endmodule
module qfd_res_train_half_b2_1(input wire ck,
input wire rst_n,
input wire [23:0] ck_bank,
input wire train_start,
input wire [3:0] train_count,
input wire [31:0] capture_stride,
input wire payload_write,
input wire [3:0] slot_count,
input wire [2212:0] rq,
output wire [550:0] rb,
output wire fault);
qfd_res_train_half_b2 #(.BAND(1),.NB(6),.D(2),.MAX_TRAIN(8),.MUT(0),.BSTN(1))u_native(.ck(ck),.rst_n(rst_n),.ck_bank(ck_bank),.train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),.slot_count(slot_count),.rq(rq),.rb(rb),.fault(fault));
endmodule
module qfd_res_train_half_b2_2(input wire ck,
input wire rst_n,
input wire [23:0] ck_bank,
input wire train_start,
input wire [3:0] train_count,
input wire [31:0] capture_stride,
input wire payload_write,
input wire [3:0] slot_count,
input wire [2212:0] rq,
output wire [550:0] rb,
output wire fault);
qfd_res_train_half_b2 #(.BAND(2),.NB(6),.D(2),.MAX_TRAIN(8),.MUT(0),.BSTN(1))u_native(.ck(ck),.rst_n(rst_n),.ck_bank(ck_bank),.train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),.slot_count(slot_count),.rq(rq),.rb(rb),.fault(fault));
endmodule
module qfd_res_train_half_b2_3(input wire ck,
input wire rst_n,
input wire [23:0] ck_bank,
input wire train_start,
input wire [3:0] train_count,
input wire [31:0] capture_stride,
input wire payload_write,
input wire [3:0] slot_count,
input wire [2212:0] rq,
output wire [550:0] rb,
output wire fault);
qfd_res_train_half_b2 #(.BAND(3),.NB(6),.D(2),.MAX_TRAIN(8),.MUT(0),.BSTN(1))u_native(.ck(ck),.rst_n(rst_n),.ck_bank(ck_bank),.train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),.slot_count(slot_count),.rq(rq),.rb(rb),.fault(fault));
endmodule
module qfd_res_train_half_b2_4(input wire ck,
input wire rst_n,
input wire [23:0] ck_bank,
input wire train_start,
input wire [3:0] train_count,
input wire [31:0] capture_stride,
input wire payload_write,
input wire [3:0] slot_count,
input wire [2212:0] rq,
output wire [550:0] rb,
output wire fault);
qfd_res_train_half_b2 #(.BAND(4),.NB(6),.D(2),.MAX_TRAIN(8),.MUT(0),.BSTN(1))u_native(.ck(ck),.rst_n(rst_n),.ck_bank(ck_bank),.train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),.slot_count(slot_count),.rq(rq),.rb(rb),.fault(fault));
endmodule
module qfd_res_train_half_b2_5(input wire ck,
input wire rst_n,
input wire [23:0] ck_bank,
input wire train_start,
input wire [3:0] train_count,
input wire [31:0] capture_stride,
input wire payload_write,
input wire [3:0] slot_count,
input wire [2212:0] rq,
output wire [550:0] rb,
output wire fault);
qfd_res_train_half_b2 #(.BAND(5),.NB(6),.D(2),.MAX_TRAIN(8),.MUT(0),.BSTN(1))u_native(.ck(ck),.rst_n(rst_n),.ck_bank(ck_bank),.train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),.slot_count(slot_count),.rq(rq),.rb(rb),.fault(fault));
endmodule
