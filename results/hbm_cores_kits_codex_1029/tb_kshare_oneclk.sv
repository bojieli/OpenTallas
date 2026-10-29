`timescale 1ns/1ps
module tb_kshare_oneclk #(parameter integer MUT_CLOCK=0);
 reg  hbm_clk;
 reg  hbm_rst_n;
 reg  stream_rst_n;
 reg [2:0] sm_stream;
 reg [2:0] sm_hbm;
 reg [3:0] g_k_v;
 reg [119:0] g_k_addr;
 reg [15:0] g_k_len;
 reg [67:0] g_k_tag;
 reg [3:0] g_k_we;
 reg [1023:0] g_k_wdata;
 reg [127:0] g_k_wstrb;
 reg [3:0] g_kr_rdy;
 reg [3:0] c_k_rdy;
 reg [3:0] c_k_wr_done;
 reg [3:0] c_kr_v;
 reg [67:0] c_kr_tag;
 reg [15:0] c_kr_beat;
 reg [1023:0] c_kr_data;
 reg  vm_v;
 reg  vm_bank;
 reg [15:0] vm_epoch;
 reg [14:0] vm_row;
 reg [3:0] vm_col;
 reg  wbw_v;
 reg [29:0] wbw_base;
 reg [11:0] wbw_total;
 reg [3:0] w_k_v;
 reg [119:0] w_k_addr;
 reg [1023:0] w_k_wdata;
 wire [3:0] g_g_k_rdy,c_g_k_rdy;
 wire [3:0] g_g_k_wr_done,c_g_k_wr_done;
 wire [3:0] g_g_kr_v,c_g_kr_v;
 wire [67:0] g_g_kr_tag,c_g_kr_tag;
 wire [15:0] g_g_kr_beat,c_g_kr_beat;
 wire [1023:0] g_g_kr_data,c_g_kr_data;
 wire [3:0] g_c_k_v,c_c_k_v;
 wire [119:0] g_c_k_addr,c_c_k_addr;
 wire [15:0] g_c_k_len,c_c_k_len;
 wire [67:0] g_c_k_tag,c_c_k_tag;
 wire [3:0] g_c_k_we,c_c_k_we;
 wire [1023:0] g_c_k_wdata,c_c_k_wdata;
 wire [127:0] g_c_k_wstrb,c_c_k_wstrb;
 wire [3:0] g_c_kr_rdy,c_c_kr_rdy;
 wire [3:0] g_w_k_rdy,c_w_k_rdy;
 wire [3:0] g_w_k_wr_done,c_w_k_wr_done;
 wire [3:0] g_fill_v,c_fill_v;
 wire [3:0] g_fill_bank,c_fill_bank;
 wire [23:0] g_fill_slot,c_fill_slot;
 wire [63:0] g_fill_epoch,c_fill_epoch;
 wire [1023:0] g_fill_data,c_fill_data;
 wire  g_fault,c_fault;
 initial hbm_clk=0; always #5 hbm_clk=~hbm_clk;
 ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0),.KRL1(1)) gold(
 .hbm_clk(hbm_clk),
 .hbm_rst_n(hbm_rst_n),
 .stream_clk(hbm_clk),
 .stream_rst_n(stream_rst_n),
 .sm_stream(sm_stream),
 .sm_hbm(sm_hbm),
 .g_k_v(g_k_v),
 .g_k_rdy(g_g_k_rdy),
 .g_k_addr(g_k_addr),
 .g_k_len(g_k_len),
 .g_k_tag(g_k_tag),
 .g_k_we(g_k_we),
 .g_k_wdata(g_k_wdata),
 .g_k_wstrb(g_k_wstrb),
 .g_k_wr_done(g_g_k_wr_done),
 .g_kr_v(g_g_kr_v),
 .g_kr_rdy(g_kr_rdy),
 .g_kr_tag(g_g_kr_tag),
 .g_kr_beat(g_g_kr_beat),
 .g_kr_data(g_g_kr_data),
 .c_k_v(g_c_k_v),
 .c_k_rdy(c_k_rdy),
 .c_k_addr(g_c_k_addr),
 .c_k_len(g_c_k_len),
 .c_k_tag(g_c_k_tag),
 .c_k_we(g_c_k_we),
 .c_k_wdata(g_c_k_wdata),
 .c_k_wstrb(g_c_k_wstrb),
 .c_k_wr_done(c_k_wr_done),
 .c_kr_v(c_kr_v),
 .c_kr_rdy(g_c_kr_rdy),
 .c_kr_tag(c_kr_tag),
 .c_kr_beat(c_kr_beat),
 .c_kr_data(c_kr_data),
 .vm_v(vm_v),
 .vm_bank(vm_bank),
 .vm_epoch(vm_epoch),
 .vm_row(vm_row),
 .vm_col(vm_col),
 .wbw_v(wbw_v),
 .wbw_base(wbw_base),
 .wbw_total(wbw_total),
 .w_k_v(w_k_v),
 .w_k_rdy(g_w_k_rdy),
 .w_k_addr(w_k_addr),
 .w_k_wdata(w_k_wdata),
 .w_k_wr_done(g_w_k_wr_done),
 .fill_v(g_fill_v),
 .fill_bank(g_fill_bank),
 .fill_slot(g_fill_slot),
 .fill_epoch(g_fill_epoch),
 .fill_data(g_fill_data),
 .fault(g_fault)
 );
 generate if(MUT_CLOCK) begin
 ot_hbm_svc_vm_kshare_oneclk_mut #(.MUT(0),.KRL1(1)) cand(
 .hbm_clk(hbm_clk),
 .hbm_rst_n(hbm_rst_n),
 .stream_rst_n(stream_rst_n),
 .sm_stream(sm_stream),
 .sm_hbm(sm_hbm),
 .g_k_v(g_k_v),
 .g_k_rdy(c_g_k_rdy),
 .g_k_addr(g_k_addr),
 .g_k_len(g_k_len),
 .g_k_tag(g_k_tag),
 .g_k_we(g_k_we),
 .g_k_wdata(g_k_wdata),
 .g_k_wstrb(g_k_wstrb),
 .g_k_wr_done(c_g_k_wr_done),
 .g_kr_v(c_g_kr_v),
 .g_kr_rdy(g_kr_rdy),
 .g_kr_tag(c_g_kr_tag),
 .g_kr_beat(c_g_kr_beat),
 .g_kr_data(c_g_kr_data),
 .c_k_v(c_c_k_v),
 .c_k_rdy(c_k_rdy),
 .c_k_addr(c_c_k_addr),
 .c_k_len(c_c_k_len),
 .c_k_tag(c_c_k_tag),
 .c_k_we(c_c_k_we),
 .c_k_wdata(c_c_k_wdata),
 .c_k_wstrb(c_c_k_wstrb),
 .c_k_wr_done(c_k_wr_done),
 .c_kr_v(c_kr_v),
 .c_kr_rdy(c_c_kr_rdy),
 .c_kr_tag(c_kr_tag),
 .c_kr_beat(c_kr_beat),
 .c_kr_data(c_kr_data),
 .vm_v(vm_v),
 .vm_bank(vm_bank),
 .vm_epoch(vm_epoch),
 .vm_row(vm_row),
 .vm_col(vm_col),
 .wbw_v(wbw_v),
 .wbw_base(wbw_base),
 .wbw_total(wbw_total),
 .w_k_v(w_k_v),
 .w_k_rdy(c_w_k_rdy),
 .w_k_addr(w_k_addr),
 .w_k_wdata(w_k_wdata),
 .w_k_wr_done(c_w_k_wr_done),
 .fill_v(c_fill_v),
 .fill_bank(c_fill_bank),
 .fill_slot(c_fill_slot),
 .fill_epoch(c_fill_epoch),
 .fill_data(c_fill_data),
 .fault(c_fault)
 );
 end else begin
 ot_hbm_svc_vm_kshare_oneclk #(.MUT(0),.KRL1(1)) cand(
 .hbm_clk(hbm_clk),
 .hbm_rst_n(hbm_rst_n),
 .stream_rst_n(stream_rst_n),
 .sm_stream(sm_stream),
 .sm_hbm(sm_hbm),
 .g_k_v(g_k_v),
 .g_k_rdy(c_g_k_rdy),
 .g_k_addr(g_k_addr),
 .g_k_len(g_k_len),
 .g_k_tag(g_k_tag),
 .g_k_we(g_k_we),
 .g_k_wdata(g_k_wdata),
 .g_k_wstrb(g_k_wstrb),
 .g_k_wr_done(c_g_k_wr_done),
 .g_kr_v(c_g_kr_v),
 .g_kr_rdy(g_kr_rdy),
 .g_kr_tag(c_g_kr_tag),
 .g_kr_beat(c_g_kr_beat),
 .g_kr_data(c_g_kr_data),
 .c_k_v(c_c_k_v),
 .c_k_rdy(c_k_rdy),
 .c_k_addr(c_c_k_addr),
 .c_k_len(c_c_k_len),
 .c_k_tag(c_c_k_tag),
 .c_k_we(c_c_k_we),
 .c_k_wdata(c_c_k_wdata),
 .c_k_wstrb(c_c_k_wstrb),
 .c_k_wr_done(c_k_wr_done),
 .c_kr_v(c_kr_v),
 .c_kr_rdy(c_c_kr_rdy),
 .c_kr_tag(c_kr_tag),
 .c_kr_beat(c_kr_beat),
 .c_kr_data(c_kr_data),
 .vm_v(vm_v),
 .vm_bank(vm_bank),
 .vm_epoch(vm_epoch),
 .vm_row(vm_row),
 .vm_col(vm_col),
 .wbw_v(wbw_v),
 .wbw_base(wbw_base),
 .wbw_total(wbw_total),
 .w_k_v(w_k_v),
 .w_k_rdy(c_w_k_rdy),
 .w_k_addr(w_k_addr),
 .w_k_wdata(w_k_wdata),
 .w_k_wr_done(c_w_k_wr_done),
 .fill_v(c_fill_v),
 .fill_bank(c_fill_bank),
 .fill_slot(c_fill_slot),
 .fill_epoch(c_fill_epoch),
 .fill_data(c_fill_data),
 .fault(c_fault)
 );
 end endgenerate
 integer cyc,checks,activity; initial begin checks=0;activity=0;
 hbm_rst_n=0;
 stream_rst_n=0;
 sm_stream=0;
 sm_hbm=0;
 g_k_v=0;
 g_k_addr=0;
 g_k_len=0;
 g_k_tag=0;
 g_k_we=0;
 g_k_wdata=0;
 g_k_wstrb=0;
 g_kr_rdy=0;
 c_k_rdy=0;
 c_k_wr_done=0;
 c_kr_v=0;
 c_kr_tag=0;
 c_kr_beat=0;
 c_kr_data=0;
 vm_v=0;
 vm_bank=0;
 vm_epoch=0;
 vm_row=0;
 vm_col=0;
 wbw_v=0;
 wbw_base=0;
 wbw_total=0;
 w_k_v=0;
 w_k_addr=0;
 w_k_wdata=0;
 sm_stream=3'd5;sm_hbm=3'd5;
 repeat(8) @(negedge hbm_clk);hbm_rst_n=1;stream_rst_n=1;
 for(cyc=0;cyc<12000;cyc=cyc+1) begin
 @(negedge hbm_clk);
 if(cyc>8 && (cyc<6000 || cyc>6016)) begin
 if({g_g_k_rdy,g_g_k_wr_done,g_g_kr_v,g_g_kr_tag,g_g_kr_beat,g_g_kr_data,g_c_k_v,g_c_k_addr,g_c_k_len,g_c_k_tag,g_c_k_we,g_c_k_wdata,g_c_k_wstrb,g_c_kr_rdy,g_w_k_rdy,g_w_k_wr_done,g_fill_v,g_fill_bank,g_fill_slot,g_fill_epoch,g_fill_data,g_fault} !== {c_g_k_rdy,c_g_k_wr_done,c_g_kr_v,c_g_kr_tag,c_g_kr_beat,c_g_kr_data,c_c_k_v,c_c_k_addr,c_c_k_len,c_c_k_tag,c_c_k_we,c_c_k_wdata,c_c_k_wstrb,c_c_kr_rdy,c_w_k_rdy,c_w_k_wr_done,c_fill_v,c_fill_bank,c_fill_slot,c_fill_epoch,c_fill_data,c_fault}) $fatal(1,"ONECLK_MISMATCH cycle=%0d",cyc);checks=checks+1;end
 if(g_c_k_v!=0 || g_g_kr_v!=0 || g_fill_v!=0) activity=activity+1;
 g_k_v[0 +: 4]=$urandom;
 g_k_addr[0 +: 32]=$urandom;
 g_k_addr[32 +: 32]=$urandom;
 g_k_addr[64 +: 32]=$urandom;
 g_k_addr[96 +: 24]=$urandom;
 g_k_len[0 +: 16]=$urandom;
 g_k_tag[0 +: 32]=$urandom;
 g_k_tag[32 +: 32]=$urandom;
 g_k_tag[64 +: 4]=$urandom;
 g_k_we[0 +: 4]=$urandom;
 g_k_wdata[0 +: 32]=$urandom;
 g_k_wdata[32 +: 32]=$urandom;
 g_k_wdata[64 +: 32]=$urandom;
 g_k_wdata[96 +: 32]=$urandom;
 g_k_wdata[128 +: 32]=$urandom;
 g_k_wdata[160 +: 32]=$urandom;
 g_k_wdata[192 +: 32]=$urandom;
 g_k_wdata[224 +: 32]=$urandom;
 g_k_wdata[256 +: 32]=$urandom;
 g_k_wdata[288 +: 32]=$urandom;
 g_k_wdata[320 +: 32]=$urandom;
 g_k_wdata[352 +: 32]=$urandom;
 g_k_wdata[384 +: 32]=$urandom;
 g_k_wdata[416 +: 32]=$urandom;
 g_k_wdata[448 +: 32]=$urandom;
 g_k_wdata[480 +: 32]=$urandom;
 g_k_wdata[512 +: 32]=$urandom;
 g_k_wdata[544 +: 32]=$urandom;
 g_k_wdata[576 +: 32]=$urandom;
 g_k_wdata[608 +: 32]=$urandom;
 g_k_wdata[640 +: 32]=$urandom;
 g_k_wdata[672 +: 32]=$urandom;
 g_k_wdata[704 +: 32]=$urandom;
 g_k_wdata[736 +: 32]=$urandom;
 g_k_wdata[768 +: 32]=$urandom;
 g_k_wdata[800 +: 32]=$urandom;
 g_k_wdata[832 +: 32]=$urandom;
 g_k_wdata[864 +: 32]=$urandom;
 g_k_wdata[896 +: 32]=$urandom;
 g_k_wdata[928 +: 32]=$urandom;
 g_k_wdata[960 +: 32]=$urandom;
 g_k_wdata[992 +: 32]=$urandom;
 g_k_wstrb[0 +: 32]=$urandom;
 g_k_wstrb[32 +: 32]=$urandom;
 g_k_wstrb[64 +: 32]=$urandom;
 g_k_wstrb[96 +: 32]=$urandom;
 g_kr_rdy[0 +: 4]=$urandom;
 c_k_rdy[0 +: 4]=$urandom;
 c_k_wr_done[0 +: 4]=$urandom;
 c_kr_v[0 +: 4]=$urandom;
 c_kr_tag[0 +: 32]=$urandom;
 c_kr_tag[32 +: 32]=$urandom;
 c_kr_tag[64 +: 4]=$urandom;
 c_kr_beat[0 +: 16]=$urandom;
 c_kr_data[0 +: 32]=$urandom;
 c_kr_data[32 +: 32]=$urandom;
 c_kr_data[64 +: 32]=$urandom;
 c_kr_data[96 +: 32]=$urandom;
 c_kr_data[128 +: 32]=$urandom;
 c_kr_data[160 +: 32]=$urandom;
 c_kr_data[192 +: 32]=$urandom;
 c_kr_data[224 +: 32]=$urandom;
 c_kr_data[256 +: 32]=$urandom;
 c_kr_data[288 +: 32]=$urandom;
 c_kr_data[320 +: 32]=$urandom;
 c_kr_data[352 +: 32]=$urandom;
 c_kr_data[384 +: 32]=$urandom;
 c_kr_data[416 +: 32]=$urandom;
 c_kr_data[448 +: 32]=$urandom;
 c_kr_data[480 +: 32]=$urandom;
 c_kr_data[512 +: 32]=$urandom;
 c_kr_data[544 +: 32]=$urandom;
 c_kr_data[576 +: 32]=$urandom;
 c_kr_data[608 +: 32]=$urandom;
 c_kr_data[640 +: 32]=$urandom;
 c_kr_data[672 +: 32]=$urandom;
 c_kr_data[704 +: 32]=$urandom;
 c_kr_data[736 +: 32]=$urandom;
 c_kr_data[768 +: 32]=$urandom;
 c_kr_data[800 +: 32]=$urandom;
 c_kr_data[832 +: 32]=$urandom;
 c_kr_data[864 +: 32]=$urandom;
 c_kr_data[896 +: 32]=$urandom;
 c_kr_data[928 +: 32]=$urandom;
 c_kr_data[960 +: 32]=$urandom;
 c_kr_data[992 +: 32]=$urandom;
 vm_v=$urandom;
 vm_bank=$urandom;
 vm_epoch[0 +: 16]=$urandom;
 vm_row[0 +: 15]=$urandom;
 vm_col[0 +: 4]=$urandom;
 wbw_v=$urandom;
 wbw_base[0 +: 30]=$urandom;
 wbw_total[0 +: 12]=$urandom;
 w_k_v[0 +: 4]=$urandom;
 w_k_addr[0 +: 32]=$urandom;
 w_k_addr[32 +: 32]=$urandom;
 w_k_addr[64 +: 32]=$urandom;
 w_k_addr[96 +: 24]=$urandom;
 w_k_wdata[0 +: 32]=$urandom;
 w_k_wdata[32 +: 32]=$urandom;
 w_k_wdata[64 +: 32]=$urandom;
 w_k_wdata[96 +: 32]=$urandom;
 w_k_wdata[128 +: 32]=$urandom;
 w_k_wdata[160 +: 32]=$urandom;
 w_k_wdata[192 +: 32]=$urandom;
 w_k_wdata[224 +: 32]=$urandom;
 w_k_wdata[256 +: 32]=$urandom;
 w_k_wdata[288 +: 32]=$urandom;
 w_k_wdata[320 +: 32]=$urandom;
 w_k_wdata[352 +: 32]=$urandom;
 w_k_wdata[384 +: 32]=$urandom;
 w_k_wdata[416 +: 32]=$urandom;
 w_k_wdata[448 +: 32]=$urandom;
 w_k_wdata[480 +: 32]=$urandom;
 w_k_wdata[512 +: 32]=$urandom;
 w_k_wdata[544 +: 32]=$urandom;
 w_k_wdata[576 +: 32]=$urandom;
 w_k_wdata[608 +: 32]=$urandom;
 w_k_wdata[640 +: 32]=$urandom;
 w_k_wdata[672 +: 32]=$urandom;
 w_k_wdata[704 +: 32]=$urandom;
 w_k_wdata[736 +: 32]=$urandom;
 w_k_wdata[768 +: 32]=$urandom;
 w_k_wdata[800 +: 32]=$urandom;
 w_k_wdata[832 +: 32]=$urandom;
 w_k_wdata[864 +: 32]=$urandom;
 w_k_wdata[896 +: 32]=$urandom;
 w_k_wdata[928 +: 32]=$urandom;
 w_k_wdata[960 +: 32]=$urandom;
 w_k_wdata[992 +: 32]=$urandom;
 if(cyc==6000)begin hbm_rst_n=0;stream_rst_n=0;end
 if(cyc==6008)begin hbm_rst_n=1;stream_rst_n=1;end
 end
 if(activity<100) $fatal(1,"VACUOUS activity=%0d",activity);$display("ONECLK_PASS checks=%0d activecycles=%0d",checks,activity);$finish;end
endmodule
