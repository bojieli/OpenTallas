(* blackbox *) module ot_wbq_root_store #(parameter integer LANE=0)(
 input wire fifo_clk,hbm_clk,srst,hrst,
 input wire [1:0]root_id,input wire [31:0]base,
 input wire [11:0]total,committed,ordinal,
 input wire filling,fill_bank,copy_q,copy_bank,copy_start,s_stop,
 input wire [255:0]wd,input wire wd_v,fifo_re,
 output wire [287:0]fifo_head,output wire fifo_empty
);
endmodule
