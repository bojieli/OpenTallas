`default_nettype none
// SOURCE-ONLY shared nativeCW308 collar dispatch. Exactly one existing106/107
// collar supplies cmd/cycle. There is no new target, ROM, ready or arbitration.
module ot_hbm_static_dma_cmd_dispatch(
 input wire clk,rst_n,cmd_v_i,input wire[307:0]cmd_i,input wire busy_i,backend_fault_i,
 output wire load_v_o,store_v_o,output reg fault_o
);
 wire[226:0]move=cmd_i[290:64];
 // These are227-bit MOVE offsets. FullCW308 equivalents65:64 and158:157.
 wire is_load=move[1:0]==2'd0&&move[94:93]==2'd1;
 wire is_store=move[1:0]==2'd1&&move[94:93]==2'd0;
 assign load_v_o=cmd_v_i&&is_load&&!busy_i&&!backend_fault_i&&!fault_o;
 assign store_v_o=cmd_v_i&&is_store&&!busy_i&&!backend_fault_i&&!fault_o;
 always @(posedge clk)begin
 if(!rst_n)fault_o<=0;
 else if(backend_fault_i||(cmd_v_i&&(busy_i||!(is_load||is_store))))fault_o<=1;
 end
endmodule
`default_nettype wire
