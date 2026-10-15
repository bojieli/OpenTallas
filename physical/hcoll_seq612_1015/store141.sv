`timescale 1ns/1ps
// Physical alias only. The frozen native leaf is instantiated without new logic.
module ot_hgi_coll_seq_store141_phys(input wire clk,we,input wire[5:0]wa,ra,input wire[140:0]din,output wire[140:0]dout);
 ot_qkvd_llr_replay_sram_leaf #(.W(141),.QD(64)) u_leaf(.ck(clk),.we(we),.wa(wa),.ra(ra),.din(din),.dout(dout));
endmodule
