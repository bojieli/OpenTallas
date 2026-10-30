`default_nettype none
// SOURCE-ONLY combinational adapter to the actual62bit NPC2 LOAD command, directcount1..8 (not count-minus-one).
// The scheduler supplies already-owned fixed-window row/column, buffer and epoch.
// A mismatch faults immediately; no request, ready, refill or wait is fabricated.
module ot_hbm_static_load_addr_map #(parameter integer MUT_PC=0)(
 input wire addr_v_i,input wire[39:0]src_byte_i,dst_word_i,input wire[2:0]fmt_i,
 input wire[3:0]count_i,input wire buffer_i,input wire[15:0]epoch_i,input wire[14:0]window_row_i,input wire[3:0]window_col_i,
 output wire load_v_o,output wire fault_o,output wire[61:0]load_cmd_o,
 output wire[2:0]source_leaf_o,output wire[1:0]source_quad_o
);
 wire[4:0]pc=src_byte_i[11:7]^src_byte_i[16:12]^src_byte_i[21:17]^(MUT_PC!=0?5'd1:5'd0);
 wire[5:0]slot={src_byte_i[12],src_byte_i[19:17],src_byte_i[6:5]};
 wire badalign=(fmt_i==0||fmt_i==5)?(|src_byte_i[1:0]):fmt_i==1?src_byte_i[0]:1'b0;
 wire[2:0]esize=(fmt_i==0||fmt_i==5)?3'd4:fmt_i==1?3'd2:3'd1;
 wire[6:0]byte_count={4'd0,esize}*{3'd0,count_i};
 wire bad=count_i==0||count_i>8||({1'b0,dst_word_i[2:0]}+count_i>8)||({2'd0,src_byte_i[4:0]}+byte_count>32)||
 ({5'd0,src_byte_i[34:0]}>40'd22500000000-{33'd0,byte_count})||(|src_byte_i[39:37])||src_byte_i[36:35]!=2||(|dst_word_i[39:18])||fmt_i==3||fmt_i==7||badalign||
 src_byte_i[34:20]!=window_row_i||src_byte_i[16:13]!=window_col_i;
 assign fault_o=addr_v_i&&bad;
 assign load_v_o=addr_v_i&&!bad;
 assign source_leaf_o=pc[2:0];
 assign source_quad_o=pc[4]?2'd3:2'd2;
 assign load_cmd_o={dst_word_i[17:16],dst_word_i[5:3],1'b0,count_i,dst_word_i[2:0],1'b0,dst_word_i[17:3],fmt_i,
                   src_byte_i[4:0],slot,1'b0,pc[3],epoch_i,buffer_i};
endmodule
`default_nettype wire
