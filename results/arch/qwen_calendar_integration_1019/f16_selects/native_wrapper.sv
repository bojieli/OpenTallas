module qfd_f16_native (
 input wire ck,rst_n,pw_v,input wire[9:0]pw_addr,input wire[63:0]pw_data,
 input wire all_copies_authenticated,fusedcap,input wire[63:0]installed_digest,input wire[15:0]installed_epoch,
 input wire start_v,input wire[1:0]start_user,input wire[5:0]start_stage,input wire[15:0]start_epoch,
 input wire retire_v,input wire[1:0]retire_user,input wire ME_XPF_retired,
 input wire[15:0]observation,input wire[5:0]event_stage,input wire[15:0]event_epoch,
 output wire template_ready,output wire[3:0]context_active,all_witnesses_complete,
 output reg group_complete,output reg[1:0]complete_user,output reg[3:0]complete_group,
 output reg fault
);
qfd_dv_typed_witness_control #(.ENABLE(1),.SAFE_COMPARE(1),.SAFE_SELECT(1)) dut(.*);
endmodule
