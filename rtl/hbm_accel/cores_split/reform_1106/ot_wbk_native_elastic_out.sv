`timescale 1ns/1ps
`default_nettype none
// Candidate only: literal native ready/valid, qualified ONLY for the pinned
// common-clock Kshare profile whose READY is a function of posedge state.
// The opposite-edge face capture sees that same READY at the next accept edge.
// Existing head data registers are the outputs; there is no blind wide stage.
module ot_wbq_sw_split_out__elastic_native #(parameter integer READY_NEGEDGE=1, MUT=0)(
 input wire hbm_clk,hbm_rst_n,
 input wire [15:0] in_v,output wire [15:0] in_ready,
 input wire [479:0] in_addr,input wire [4095:0] in_data,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,
 output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata
);
 wire rr;
 ot_hbm_face_rst_relay #(.W(1),.N(2)) u_brst_hbm_rst_n(.clk(hbm_clk),.rst_ni(hbm_rst_n),.rst_no(rr));
 genvar p;
 generate for(p=0;p<16;p=p+1)begin:pc_pin
  wire krst;wire ready_face;
  ot_reset_sync u_krst(.clk(hbm_clk),.async_rst_n(rr),.sync_rst_n(krst));
  if(READY_NEGEDGE!=0)begin:g_neg
   ot_wbk_native_ready_face u_bin_ready(.clk(hbm_clk),.d(w_k_rdy[p]),.q(ready_face));
  end else begin:g_wrong_phase
   ot_hbm_face_reg #(.W(1)) u_bin_ready(.clk(hbm_clk),.d(w_k_rdy[p]),.q(ready_face));
  end
  ot_wbk_native_elastic2 #(.WIDTH(286),.MUT(MUT)) u_k(
   .clk(hbm_clk),.rst_n(krst),.in_v(in_v[p]),.in_r(in_ready[p]),
   .in_data({in_addr[30*p+:30],in_data[256*p+:256]}),
   .out_v(w_k_v[p]),.out_r(ready_face),.out_data({w_k_addr[30*p+:30],w_k_wdata[256*p+:256]}));
 end endgenerate
endmodule

(* keep_hierarchy, keep *)
module ot_wbk_native_ready_face(input wire clk,d,output reg q);
 always @(negedge clk)q<=d;
endmodule

(* keep_hierarchy, keep *)
module ot_wbk_native_valid_face(input wire clk,rst_n,d,output reg q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=d;
endmodule

module ot_wbk_native_elastic2 #(parameter integer WIDTH=1,MUT=0)(
 input wire clk,rst_n,input wire in_v,output wire in_r,
 input wire[WIDTH-1:0]in_data,output wire out_v,input wire out_r,
 output wire[WIDTH-1:0]out_data
);
 reg head_valid,tail_valid;reg[WIDTH-1:0]head_data,tail_data;
 wire push=in_v&&in_r,pop=head_valid&&out_r;
 wire head_next=push?1'b1:pop?tail_valid:head_valid;
 assign in_r=!tail_valid;assign out_data=head_data;
 // Dedicated output copy: internal control never consumes the output FF's Q.
 ot_wbk_native_valid_face u_bout_valid(.clk(clk),.rst_n(rst_n),.d(head_next),.q(out_v));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin head_valid<=0;tail_valid<=0;end
  else begin
   head_valid<=head_next;
   case({push,pop})
    2'b10:begin
     if(!head_valid)head_data<=in_data;
     else begin tail_data<=in_data;tail_valid<=1;end
    end
    2'b01:begin if(tail_valid)head_data<=tail_data;tail_valid<=0;end
    2'b11:begin head_data<=in_data;tail_valid<=0;end
    default:;
   endcase
   if(MUT!=0&&push&&head_valid&&!out_r)head_data<=in_data;
  end
 end
endmodule
`default_nettype wire
