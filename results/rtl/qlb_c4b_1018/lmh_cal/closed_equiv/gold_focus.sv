module gold(
 input wire clk,input wire rst_n,
 input wire pw_v,input wire [9:0]pw_addr,input wire[63:0]pw_data,
 input wire start,input wire[5:0]stage,
 input wire[11:0]start_base,
 input wire candidate_v,input wire[11:0]candidate_pc,input wire[1:0]candidate_unit,
 input wire available,input wire end_ok,input wire cp_available,
 output wire issue_v,output wire end_v,output wire[55:0]cp_cmd,output wire cp_v,output wire[11:0]issue_pc,output wire[1:0]issue_unit,
 output wire active,output wire done,output wire[31:0]cycle,output wire image_ready,output wire fault
);
gold_ot_qwen_fixed_issue_pw #(.DENSE_IMAGE(1),.OWN(1),.SREG(1),.SLATE(1)) u(.*);
endmodule
