module ot_ds_seven_class_boundary_bank #(parameter ENABLE=0)(
input wire fast_clk,slow_clk,cold_n,fast_rst_n,slow_rst_n,
input wire [13:0] abort_s,abort_d,in_v,out_ready,retire_v,reconcile_v,allcopies_fenced,
output wire [13:0] in_ready,out_v,retire_ready,pending,quarantined,
input wire [14*16128-1:0] in_data,output wire [14*16128-1:0] out_data,
input wire [14*228-1:0] in_owner,retire_owner,reconcile_owner,
output wire [14*228-1:0] out_owner,pending_owner);
// class0: su_kv_staging, source payload16128, S2F; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(16128),.ENABLE(ENABLE)) plane_0(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_s[0]),.abort_d(abort_d[0]),.in_v(in_v[0]),.in_ready(in_ready[0]),
 .in_data(in_data[0*16128+:16128]),.in_owner(in_owner[0*228+:228]),
 .out_v(out_v[0]),.out_ready(out_ready[0]),.out_data(out_data[0*16128+:16128]),.out_owner(out_owner[0*228+:228]),
 .retire_v(retire_v[0]),.retire_ready(retire_ready[0]),.retire_owner(retire_owner[0*228+:228]),
 .reconcile_v(reconcile_v[0]),.allcopies_fenced(allcopies_fenced[0]),.reconcile_owner(reconcile_owner[0*228+:228]),
 .pending(pending[0]),.quarantined(quarantined[0]),.pending_owner(pending_owner[0*228+:228]));
// class1: me_result_write, source payload2236, F2S; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(2236),.ENABLE(ENABLE)) plane_1(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_s[1]),.abort_d(abort_d[1]),.in_v(in_v[1]),.in_ready(in_ready[1]),
 .in_data(in_data[1*16128+:2236]),.in_owner(in_owner[1*228+:228]),
 .out_v(out_v[1]),.out_ready(out_ready[1]),.out_data(out_data[1*16128+:2236]),.out_owner(out_owner[1*228+:228]),
 .retire_v(retire_v[1]),.retire_ready(retire_ready[1]),.retire_owner(retire_owner[1*228+:228]),
 .reconcile_v(reconcile_v[1]),.allcopies_fenced(allcopies_fenced[1]),.reconcile_owner(reconcile_owner[1*228+:228]),
 .pending(pending[1]),.quarantined(quarantined[1]),.pending_owner(pending_owner[1*228+:228]));
 assign out_data[1*16128+2236+:13892]='0;
// class2: field_x_request, source payload31, F2S; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(31),.ENABLE(ENABLE)) plane_2(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_s[2]),.abort_d(abort_d[2]),.in_v(in_v[2]),.in_ready(in_ready[2]),
 .in_data(in_data[2*16128+:31]),.in_owner(in_owner[2*228+:228]),
 .out_v(out_v[2]),.out_ready(out_ready[2]),.out_data(out_data[2*16128+:31]),.out_owner(out_owner[2*228+:228]),
 .retire_v(retire_v[2]),.retire_ready(retire_ready[2]),.retire_owner(retire_owner[2*228+:228]),
 .reconcile_v(reconcile_v[2]),.allcopies_fenced(allcopies_fenced[2]),.reconcile_owner(reconcile_owner[2*228+:228]),
 .pending(pending[2]),.quarantined(quarantined[2]),.pending_owner(pending_owner[2*228+:228]));
 assign out_data[2*16128+31+:16097]='0;
// class2: field_x_reply, source payload2048, S2F; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(2048),.ENABLE(ENABLE)) plane_3(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_s[3]),.abort_d(abort_d[3]),.in_v(in_v[3]),.in_ready(in_ready[3]),
 .in_data(in_data[3*16128+:2048]),.in_owner(in_owner[3*228+:228]),
 .out_v(out_v[3]),.out_ready(out_ready[3]),.out_data(out_data[3*16128+:2048]),.out_owner(out_owner[3*228+:228]),
 .retire_v(retire_v[3]),.retire_ready(retire_ready[3]),.retire_owner(retire_owner[3*228+:228]),
 .reconcile_v(reconcile_v[3]),.allcopies_fenced(allcopies_fenced[3]),.reconcile_owner(reconcile_owner[3*228+:228]),
 .pending(pending[3]),.quarantined(quarantined[3]),.pending_owner(pending_owner[3*228+:228]));
 assign out_data[3*16128+2048+:14080]='0;
// class2: field_id_request, source payload31, F2S; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(31),.ENABLE(ENABLE)) plane_4(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_s[4]),.abort_d(abort_d[4]),.in_v(in_v[4]),.in_ready(in_ready[4]),
 .in_data(in_data[4*16128+:31]),.in_owner(in_owner[4*228+:228]),
 .out_v(out_v[4]),.out_ready(out_ready[4]),.out_data(out_data[4*16128+:31]),.out_owner(out_owner[4*228+:228]),
 .retire_v(retire_v[4]),.retire_ready(retire_ready[4]),.retire_owner(retire_owner[4*228+:228]),
 .reconcile_v(reconcile_v[4]),.allcopies_fenced(allcopies_fenced[4]),.reconcile_owner(reconcile_owner[4*228+:228]),
 .pending(pending[4]),.quarantined(quarantined[4]),.pending_owner(pending_owner[4*228+:228]));
 assign out_data[4*16128+31+:16097]='0;
// class2: field_id_reply, source payload32, S2F; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(32),.ENABLE(ENABLE)) plane_5(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_s[5]),.abort_d(abort_d[5]),.in_v(in_v[5]),.in_ready(in_ready[5]),
 .in_data(in_data[5*16128+:32]),.in_owner(in_owner[5*228+:228]),
 .out_v(out_v[5]),.out_ready(out_ready[5]),.out_data(out_data[5*16128+:32]),.out_owner(out_owner[5*228+:228]),
 .retire_v(retire_v[5]),.retire_ready(retire_ready[5]),.retire_owner(retire_owner[5*228+:228]),
 .reconcile_v(reconcile_v[5]),.allcopies_fenced(allcopies_fenced[5]),.reconcile_owner(reconcile_owner[5*228+:228]),
 .pending(pending[5]),.quarantined(quarantined[5]),.pending_owner(pending_owner[5*228+:228]));
 assign out_data[5*16128+32+:16096]='0;
// class3: field_row_write, source payload8064, F2S; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(8064),.ENABLE(ENABLE)) plane_6(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_s[6]),.abort_d(abort_d[6]),.in_v(in_v[6]),.in_ready(in_ready[6]),
 .in_data(in_data[6*16128+:8064]),.in_owner(in_owner[6*228+:228]),
 .out_v(out_v[6]),.out_ready(out_ready[6]),.out_data(out_data[6*16128+:8064]),.out_owner(out_owner[6*228+:228]),
 .retire_v(retire_v[6]),.retire_ready(retire_ready[6]),.retire_owner(retire_owner[6*228+:228]),
 .reconcile_v(reconcile_v[6]),.allcopies_fenced(allcopies_fenced[6]),.reconcile_owner(reconcile_owner[6*228+:228]),
 .pending(pending[6]),.quarantined(quarantined[6]),.pending_owner(pending_owner[6*228+:228]));
 assign out_data[6*16128+8064+:8064]='0;
// class4: collective_read_request, source payload16, F2S; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(16),.ENABLE(ENABLE)) plane_7(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_s[7]),.abort_d(abort_d[7]),.in_v(in_v[7]),.in_ready(in_ready[7]),
 .in_data(in_data[7*16128+:16]),.in_owner(in_owner[7*228+:228]),
 .out_v(out_v[7]),.out_ready(out_ready[7]),.out_data(out_data[7*16128+:16]),.out_owner(out_owner[7*228+:228]),
 .retire_v(retire_v[7]),.retire_ready(retire_ready[7]),.retire_owner(retire_owner[7*228+:228]),
 .reconcile_v(reconcile_v[7]),.allcopies_fenced(allcopies_fenced[7]),.reconcile_owner(reconcile_owner[7*228+:228]),
 .pending(pending[7]),.quarantined(quarantined[7]),.pending_owner(pending_owner[7*228+:228]));
 assign out_data[7*16128+16+:16112]='0;
// class4: collective_read_reply, source payload512, S2F; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(512),.ENABLE(ENABLE)) plane_8(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_s[8]),.abort_d(abort_d[8]),.in_v(in_v[8]),.in_ready(in_ready[8]),
 .in_data(in_data[8*16128+:512]),.in_owner(in_owner[8*228+:228]),
 .out_v(out_v[8]),.out_ready(out_ready[8]),.out_data(out_data[8*16128+:512]),.out_owner(out_owner[8*228+:228]),
 .retire_v(retire_v[8]),.retire_ready(retire_ready[8]),.retire_owner(retire_owner[8*228+:228]),
 .reconcile_v(reconcile_v[8]),.allcopies_fenced(allcopies_fenced[8]),.reconcile_owner(reconcile_owner[8*228+:228]),
 .pending(pending[8]),.quarantined(quarantined[8]),.pending_owner(pending_owner[8*228+:228]));
 assign out_data[8*16128+512+:15616]='0;
// class4: collective_write, source payload2112, F2S; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(2112),.ENABLE(ENABLE)) plane_9(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_s[9]),.abort_d(abort_d[9]),.in_v(in_v[9]),.in_ready(in_ready[9]),
 .in_data(in_data[9*16128+:2112]),.in_owner(in_owner[9*228+:228]),
 .out_v(out_v[9]),.out_ready(out_ready[9]),.out_data(out_data[9*16128+:2112]),.out_owner(out_owner[9*228+:228]),
 .retire_v(retire_v[9]),.retire_ready(retire_ready[9]),.retire_owner(retire_owner[9*228+:228]),
 .reconcile_v(reconcile_v[9]),.allcopies_fenced(allcopies_fenced[9]),.reconcile_owner(reconcile_owner[9*228+:228]),
 .pending(pending[9]),.quarantined(quarantined[9]),.pending_owner(pending_owner[9*228+:228]));
 assign out_data[9*16128+2112+:14016]='0;
// class5: index_query_request, source payload124, F2S; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(124),.ENABLE(ENABLE)) plane_10(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_s[10]),.abort_d(abort_d[10]),.in_v(in_v[10]),.in_ready(in_ready[10]),
 .in_data(in_data[10*16128+:124]),.in_owner(in_owner[10*228+:228]),
 .out_v(out_v[10]),.out_ready(out_ready[10]),.out_data(out_data[10*16128+:124]),.out_owner(out_owner[10*228+:228]),
 .retire_v(retire_v[10]),.retire_ready(retire_ready[10]),.retire_owner(retire_owner[10*228+:228]),
 .reconcile_v(reconcile_v[10]),.allcopies_fenced(allcopies_fenced[10]),.reconcile_owner(reconcile_owner[10*228+:228]),
 .pending(pending[10]),.quarantined(quarantined[10]),.pending_owner(pending_owner[10*228+:228]));
 assign out_data[10*16128+124+:16004]='0;
// class5: index_query_reply, source payload128, S2F; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(128),.ENABLE(ENABLE)) plane_11(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_s[11]),.abort_d(abort_d[11]),.in_v(in_v[11]),.in_ready(in_ready[11]),
 .in_data(in_data[11*16128+:128]),.in_owner(in_owner[11*228+:228]),
 .out_v(out_v[11]),.out_ready(out_ready[11]),.out_data(out_data[11*16128+:128]),.out_owner(out_owner[11*228+:228]),
 .retire_v(retire_v[11]),.retire_ready(retire_ready[11]),.retire_owner(retire_owner[11*228+:228]),
 .reconcile_v(reconcile_v[11]),.allcopies_fenced(allcopies_fenced[11]),.reconcile_owner(reconcile_owner[11*228+:228]),
 .pending(pending[11]),.quarantined(quarantined[11]),.pending_owner(pending_owner[11*228+:228]));
 assign out_data[11*16128+128+:16000]='0;
// class6: selector_read_request, source payload124, F2S; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(124),.ENABLE(ENABLE)) plane_12(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_s[12]),.abort_d(abort_d[12]),.in_v(in_v[12]),.in_ready(in_ready[12]),
 .in_data(in_data[12*16128+:124]),.in_owner(in_owner[12*228+:228]),
 .out_v(out_v[12]),.out_ready(out_ready[12]),.out_data(out_data[12*16128+:124]),.out_owner(out_owner[12*228+:228]),
 .retire_v(retire_v[12]),.retire_ready(retire_ready[12]),.retire_owner(retire_owner[12*228+:228]),
 .reconcile_v(reconcile_v[12]),.allcopies_fenced(allcopies_fenced[12]),.reconcile_owner(reconcile_owner[12*228+:228]),
 .pending(pending[12]),.quarantined(quarantined[12]),.pending_owner(pending_owner[12*228+:228]));
 assign out_data[12*16128+124+:16004]='0;
// class6: selector_read_reply, source payload2048, S2F; no 4/3 widening.
 ot_ds_owned_ratio_boundary #(.W(2048),.ENABLE(ENABLE)) plane_13(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_s[13]),.abort_d(abort_d[13]),.in_v(in_v[13]),.in_ready(in_ready[13]),
 .in_data(in_data[13*16128+:2048]),.in_owner(in_owner[13*228+:228]),
 .out_v(out_v[13]),.out_ready(out_ready[13]),.out_data(out_data[13*16128+:2048]),.out_owner(out_owner[13*228+:228]),
 .retire_v(retire_v[13]),.retire_ready(retire_ready[13]),.retire_owner(retire_owner[13*228+:228]),
 .reconcile_v(reconcile_v[13]),.allcopies_fenced(allcopies_fenced[13]),.reconcile_owner(reconcile_owner[13*228+:228]),
 .pending(pending[13]),.quarantined(quarantined[13]),.pending_owner(pending_owner[13*228+:228]));
 assign out_data[13*16128+2048+:14080]='0;
endmodule
