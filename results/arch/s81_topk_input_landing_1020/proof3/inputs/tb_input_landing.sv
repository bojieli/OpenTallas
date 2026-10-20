`timescale 1ns/1ps
module tb_input_landing;
reg clk=0; always #5 clk=~clk; reg rst_n=0; reg [514:0] lane=0; integer cyc,j,checks=0; integer counts[0:15];
wire [0:0] g_b_v, d_b_v;
wire [15:0] g_b_lv, d_b_lv;
wire [255:0] g_b_val, d_b_val;
wire [319:0] g_b_idx, d_b_idx;
wire [0:0] g_b_last, d_b_last;
wire [0:0] g_h_v, d_h_v;
wire [9:0] g_h_k, d_h_k;
wire [7:0] g_h_tag, d_h_tag;
wire [1:0] g_h_q, d_h_q;
wire [0:0] g_act, d_act;
wire [1:0] g_act_q, d_act_q;
wire [0:0] g_e_fmt, d_e_fmt;
wire [0:0] g_e_orphan, d_e_orphan;
wire [0:0] g_e_link, d_e_link;
ot_s81ph_hq_in_gold u_g (.clk(clk),.rst_n(rst_n),.lane(lane),.b_v(g_b_v),.b_lv(g_b_lv),.b_val(g_b_val),.b_idx(g_b_idx),.b_last(g_b_last),.h_v(g_h_v),.h_k(g_h_k),.h_tag(g_h_tag),.h_q(g_h_q),.act(g_act),.act_q(g_act_q),.e_fmt(g_e_fmt),.e_orphan(g_e_orphan),.e_link(g_e_link));
ot_s81ph_hq_in u_d (.clk(clk),.rst_n(rst_n),.lane(lane),.b_v(d_b_v),.b_lv(d_b_lv),.b_val(d_b_val),.b_idx(d_b_idx),.b_last(d_b_last),.h_v(d_h_v),.h_k(d_h_k),.h_tag(d_h_tag),.h_q(d_h_q),.act(d_act),.act_q(d_act_q),.e_fmt(d_e_fmt),.e_orphan(d_e_orphan),.e_link(d_e_link));
wire [620:0] gold={g_b_v,g_b_lv,g_b_val,g_b_idx,g_b_last,g_h_v,g_h_k,g_h_tag,g_h_q,g_act,g_act_q,g_e_fmt,g_e_orphan,g_e_link};
wire [620:0] dut={d_b_v,d_b_lv,d_b_val,d_b_idx,d_b_last,d_h_v,d_h_k,d_h_tag,d_h_q,d_act,d_act_q,d_e_fmt,d_e_orphan,d_e_link};
initial begin
  for (j=0;j<16;j=j+1) counts[j]=0;
  for (cyc=0;cyc<24000;cyc=cyc+1) begin
    @(negedge clk);
    for (j=0;j<16;j=j+1) lane[32*j +: 32]=$urandom;
    lane[514:512]=$urandom; lane[512:509]=4'(cyc%16);
    counts[cyc%16]=counts[cyc%16]+1;
    rst_n=(cyc>=8 && cyc%137>2);
    @(posedge clk); #1;
    if (cyc>=8) begin
      if (gold !== dut) begin
`ifdef OT_S81PH_HQ_INPUT_RAW_MUT
        $display("IN_LAND FAIL MUT=%0d cycle=%0d type=%0d golden=%h dut=%h",`OT_S81PH_HQ_INPUT_RAW_MUT,cyc,lane[512:509],gold,dut);
`else
        $display("IN_LAND FAIL MUT=0 cycle=%0d type=%0d golden=%h dut=%h",cyc,lane[512:509],gold,dut);
`endif
        $fatal(1,"INPUT_LANDING_LOCKSTEP_REJECT");
      end
      checks=checks+1;
    end
  end
  for (j=0;j<16;j=j+1) if(counts[j]!=1500) $fatal(1,"TYPE_COVERAGE");
  $display("IN_LAND PASS checks=%0d all16types=1500 resets=random_periodic added_edges=0",checks);
  $finish;
end
endmodule

