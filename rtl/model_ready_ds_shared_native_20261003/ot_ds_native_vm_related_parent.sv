`timescale 1ns/1ps
`default_nettype none
// Actual thirteen native-VM planes; class0 SU/KV remains its source-owned
// staging/visible service. One full native VM below, never one per reader.
module ot_ds_native_vm_related_parent #(parameter integer ENABLE=0)(
 input wire fast_clk,slow_clk,cold_n,fast_rst_n,slow_rst_n,abort_fast,abort_slow,
 input wire [4:0] r_v,output wire [4:0] r_ready,
 input wire [19:0] r_enable,input wire [599:0] r_addr,input wire [824:0] r_context,
 output wire [4:0] q_v,input wire [4:0] q_ready,output wire [10239:0] q_data,
 output wire [1139:0] q_owner,
 input wire [3:0] me_en,input wire [119:0] me_wordaddr,input wire [63:0] me_mask,input wire [2047:0] me_data,
 input wire [127:0] row_en,input wire [3839:0] row_addr,input wire [4095:0] row_data,
 input wire [3:0] coll_en,input wire [59:0] coll_wordaddr,input wire [2047:0] coll_data,
 input wire [494:0] w_context,output wire [2:0] w_ready,w_visible,w_pending,
 output wire [127:0] row_visible_mask,
 output wire fault,quarantined,output wire [7:0] debt,
 output wire [3:0] debug_native_write_accept,debug_native_visible,
 output wire debug_native_read_accept
);
 wire [4:0] rv,rr,pqv,pqr,reqret,reqrr,qp,qq,reqp,reqquar;
 wire [19:0] re;wire [599:0] ra;wire [1139:0] ro,pqo,reqro,qpo;
 wire [10239:0] pqdata;
 wire [2:0] wv,wr,wret,wretr,wquar;
 wire [383:0] we;wire [11519:0] wa;wire [12287:0] wd;wire [683:0] wo,wro;
 wire [7:0] accept,exhausted;wire [1823:0] issued_owner;
 reg [31:0] epoch[0:7];reg [15:0] batch[0:7];reg [10:0] rid[0:7];
 reg [2:0] was_write_pending;reg [4:0] reply_sent;
 reg format_fault;reg [127:0] accepted_row_mask;
 assign row_visible_mask=w_visible[1] ? accepted_row_mask : 128'b0;
 wire provider_fault,provider_quarantine;wire [7:0] provider_debt;
 assign debt=provider_debt|{w_pending,reqp};
 assign w_visible=was_write_pending&~w_pending&~wquar&{3{fast_rst_n&&!abort_fast}};
 always @(posedge fast_clk)begin
  if(!cold_n)begin was_write_pending<=0;format_fault<=0;accepted_row_mask<=0;end
  else begin
   was_write_pending<=w_pending;
   if(accept[6])accepted_row_mask<=row_en;
   if(r_v[2] && (|r_addr[240+15+:15]))format_fault<=1;
  end
 end
 genvar ns;
 generate for(ns=0;ns<8;ns=ns+1)begin: namespace
  wire [164:0] context_bits;
  if(ns<5)assign context_bits=r_context[ns*165+:165];else assign context_bits=w_context[(ns-5)*165+:165];
  assign issued_owner[ns*228+:228]={4'(ns),context_bits,epoch[ns],batch[ns],rid[ns]};
  assign exhausted[ns]=(epoch[ns]==32'hffffffff && rid[ns]==11'h7ff);
  always @(posedge fast_clk)begin
   if(!cold_n)begin epoch[ns]<=0;batch[ns]<=0;rid[ns]<=0;end
   else if(accept[ns])begin
    if(rid[ns]==11'h7ff)begin rid[ns]<=0;epoch[ns]<=epoch[ns]+1'b1;batch[ns]<=batch[ns]+1'b1;end
    else rid[ns]<=rid[ns]+1'b1;
   end
  end
 end endgenerate
 always @(posedge slow_clk)begin
  if(!cold_n)reply_sent<=0;
  else for(integer r=0;r<5;r=r+1)begin
   if(pqv[r]&&pqr[r])reply_sent[r]<=1;
   if(reply_sent[r]&&!qp[r]&&!qq[r])reply_sent[r]<=0;
  end
 end
 wire [4:0] consumed=reply_sent&~qp&~qq&{5{slow_rst_n&&!abort_slow}};
 wire [2:0] formats_bad;
 assign fault=provider_fault||format_fault;
 assign quarantined=provider_quarantine||(|reqquar)||(|qq)||(|wquar);
 wire [30:0] request_0;wire [30:0] source_0;assign source_0={r_enable[0],r_addr[0+:30]};
 wire [2047:0] reply_0;wire source_ready_0,reply_retire_ready_0,qraw_0;
 assign q_v[0]=qraw_0&&reply_retire_ready_0;
 assign r_ready[0]=source_ready_0&&!exhausted[0]&&!format_fault;
 assign accept[0]=r_v[0]&&r_ready[0];
 ot_ds_owned_ratio_boundary #(.W(31),.ENABLE(ENABLE)) req_0(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_fast),.abort_d(abort_slow),.in_v(r_v[0]&&!exhausted[0]&&!format_fault),.in_ready(source_ready_0),
 .in_data(source_0),.in_owner(issued_owner[0+:228]),.out_v(rv[0]),.out_ready(rr[0]),.out_data(request_0),.out_owner(ro[0+:228]),
 .retire_v(reqret[0]),.retire_ready(reqrr[0]),.retire_owner(reqro[0+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(reqp[0]),.quarantined(reqquar[0]),.pending_owner());
 assign re[0+:4]={3'b0,request_0[30]};assign ra[0+:120]={90'b0,request_0[29:0]};
 ot_ds_owned_ratio_boundary #(.W(2048),.ENABLE(ENABLE)) reply_crossing_0(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_slow),.abort_d(abort_fast),.in_v(pqv[0]),.in_ready(pqr[0]),.in_data(pqdata[0+: 2048]),.in_owner(pqo[0+:228]),
 .out_v(qraw_0),.out_ready(q_ready[0]&&reply_retire_ready_0),.out_data(reply_0),.out_owner(q_owner[0+:228]),
 .retire_v(qraw_0&&q_ready[0]&&reply_retire_ready_0),.retire_ready(reply_retire_ready_0),.retire_owner(q_owner[0+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(qp[0]),.quarantined(qq[0]),.pending_owner(qpo[0+:228]));
 assign q_data[0+:2048]={ {(2048-2048){1'b0}},reply_0};
 wire [30:0] request_1;wire [30:0] source_1;assign source_1={r_enable[4],r_addr[120+:30]};
 wire [31:0] reply_1;wire source_ready_1,reply_retire_ready_1,qraw_1;
 assign q_v[1]=qraw_1&&reply_retire_ready_1;
 assign r_ready[1]=source_ready_1&&!exhausted[1]&&!format_fault;
 assign accept[1]=r_v[1]&&r_ready[1];
 ot_ds_owned_ratio_boundary #(.W(31),.ENABLE(ENABLE)) req_1(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_fast),.abort_d(abort_slow),.in_v(r_v[1]&&!exhausted[1]&&!format_fault),.in_ready(source_ready_1),
 .in_data(source_1),.in_owner(issued_owner[228+:228]),.out_v(rv[1]),.out_ready(rr[1]),.out_data(request_1),.out_owner(ro[228+:228]),
 .retire_v(reqret[1]),.retire_ready(reqrr[1]),.retire_owner(reqro[228+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(reqp[1]),.quarantined(reqquar[1]),.pending_owner());
 assign re[4+:4]={3'b0,request_1[30]};assign ra[120+:120]={90'b0,request_1[29:0]};
 ot_ds_owned_ratio_boundary #(.W(32),.ENABLE(ENABLE)) reply_crossing_1(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_slow),.abort_d(abort_fast),.in_v(pqv[1]),.in_ready(pqr[1]),.in_data(pqdata[2048+: 32]),.in_owner(pqo[228+:228]),
 .out_v(qraw_1),.out_ready(q_ready[1]&&reply_retire_ready_1),.out_data(reply_1),.out_owner(q_owner[228+:228]),
 .retire_v(qraw_1&&q_ready[1]&&reply_retire_ready_1),.retire_ready(reply_retire_ready_1),.retire_owner(q_owner[228+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(qp[1]),.quarantined(qq[1]),.pending_owner(qpo[228+:228]));
 assign q_data[2048+:2048]={ {(2048-32){1'b0}},reply_1};
 wire [15:0] request_2;wire [15:0] source_2;assign source_2={r_enable[8],r_addr[240+:15]};
 wire [511:0] reply_2;wire source_ready_2,reply_retire_ready_2,qraw_2;
 assign q_v[2]=qraw_2&&reply_retire_ready_2;
 assign r_ready[2]=source_ready_2&&!exhausted[2]&&!format_fault&&!(|r_addr[240+15+:15]);
 assign accept[2]=r_v[2]&&r_ready[2];
 ot_ds_owned_ratio_boundary #(.W(16),.ENABLE(ENABLE)) req_2(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_fast),.abort_d(abort_slow),.in_v(r_v[2]&&!exhausted[2]&&!format_fault&&!(|r_addr[240+15+:15])),.in_ready(source_ready_2),
 .in_data(source_2),.in_owner(issued_owner[456+:228]),.out_v(rv[2]),.out_ready(rr[2]),.out_data(request_2),.out_owner(ro[456+:228]),
 .retire_v(reqret[2]),.retire_ready(reqrr[2]),.retire_owner(reqro[456+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(reqp[2]),.quarantined(reqquar[2]),.pending_owner());
 assign re[8+:4]={3'b0,request_2[15]};assign ra[240+:120]={90'b0,11'b0,request_2[14:0],4'b0};
 ot_ds_owned_ratio_boundary #(.W(512),.ENABLE(ENABLE)) reply_crossing_2(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_slow),.abort_d(abort_fast),.in_v(pqv[2]),.in_ready(pqr[2]),.in_data(pqdata[4096+: 512]),.in_owner(pqo[456+:228]),
 .out_v(qraw_2),.out_ready(q_ready[2]&&reply_retire_ready_2),.out_data(reply_2),.out_owner(q_owner[456+:228]),
 .retire_v(qraw_2&&q_ready[2]&&reply_retire_ready_2),.retire_ready(reply_retire_ready_2),.retire_owner(q_owner[456+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(qp[2]),.quarantined(qq[2]),.pending_owner(qpo[456+:228]));
 assign q_data[4096+:2048]={ {(2048-512){1'b0}},reply_2};
 wire [123:0] request_3;wire [123:0] source_3;assign source_3={r_enable[12+:4],r_addr[360+:120]};
 wire [127:0] reply_3;wire source_ready_3,reply_retire_ready_3,qraw_3;
 assign q_v[3]=qraw_3&&reply_retire_ready_3;
 assign r_ready[3]=source_ready_3&&!exhausted[3]&&!format_fault;
 assign accept[3]=r_v[3]&&r_ready[3];
 ot_ds_owned_ratio_boundary #(.W(124),.ENABLE(ENABLE)) req_3(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_fast),.abort_d(abort_slow),.in_v(r_v[3]&&!exhausted[3]&&!format_fault),.in_ready(source_ready_3),
 .in_data(source_3),.in_owner(issued_owner[684+:228]),.out_v(rv[3]),.out_ready(rr[3]),.out_data(request_3),.out_owner(ro[684+:228]),
 .retire_v(reqret[3]),.retire_ready(reqrr[3]),.retire_owner(reqro[684+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(reqp[3]),.quarantined(reqquar[3]),.pending_owner());
 assign re[12+:4]=request_3[123:120];assign ra[360+:120]=request_3[119:0];
 ot_ds_owned_ratio_boundary #(.W(128),.ENABLE(ENABLE)) reply_crossing_3(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_slow),.abort_d(abort_fast),.in_v(pqv[3]),.in_ready(pqr[3]),.in_data(pqdata[6144+: 128]),.in_owner(pqo[684+:228]),
 .out_v(qraw_3),.out_ready(q_ready[3]&&reply_retire_ready_3),.out_data(reply_3),.out_owner(q_owner[684+:228]),
 .retire_v(qraw_3&&q_ready[3]&&reply_retire_ready_3),.retire_ready(reply_retire_ready_3),.retire_owner(q_owner[684+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(qp[3]),.quarantined(qq[3]),.pending_owner(qpo[684+:228]));
 assign q_data[6144+:2048]={ {(2048-128){1'b0}},reply_3};
 wire [123:0] request_4;wire [123:0] source_4;assign source_4={r_enable[16+:4],r_addr[480+:120]};
 wire [2047:0] reply_4;wire source_ready_4,reply_retire_ready_4,qraw_4;
 assign q_v[4]=qraw_4&&reply_retire_ready_4;
 assign r_ready[4]=source_ready_4&&!exhausted[4]&&!format_fault;
 assign accept[4]=r_v[4]&&r_ready[4];
 ot_ds_owned_ratio_boundary #(.W(124),.ENABLE(ENABLE)) req_4(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_fast),.abort_d(abort_slow),.in_v(r_v[4]&&!exhausted[4]&&!format_fault),.in_ready(source_ready_4),
 .in_data(source_4),.in_owner(issued_owner[912+:228]),.out_v(rv[4]),.out_ready(rr[4]),.out_data(request_4),.out_owner(ro[912+:228]),
 .retire_v(reqret[4]),.retire_ready(reqrr[4]),.retire_owner(reqro[912+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(reqp[4]),.quarantined(reqquar[4]),.pending_owner());
 assign re[16+:4]=request_4[123:120];assign ra[480+:120]=request_4[119:0];
 ot_ds_owned_ratio_boundary #(.W(2048),.ENABLE(ENABLE)) reply_crossing_4(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_slow),.abort_d(abort_fast),.in_v(pqv[4]),.in_ready(pqr[4]),.in_data(pqdata[8192+: 2048]),.in_owner(pqo[912+:228]),
 .out_v(qraw_4),.out_ready(q_ready[4]&&reply_retire_ready_4),.out_data(reply_4),.out_owner(q_owner[912+:228]),
 .retire_v(qraw_4&&q_ready[4]&&reply_retire_ready_4),.retire_ready(reply_retire_ready_4),.retire_owner(q_owner[912+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(qp[4]),.quarantined(qq[4]),.pending_owner(qpo[912+:228]));
 assign q_data[8192+:2048]={ {(2048-2048){1'b0}},reply_4};
 wire [2235:0] wpacket_0;wire [2235:0] wsource_0;assign wsource_0={me_en,me_wordaddr,me_mask,me_data};wire source_write_ready_0;
 wire write_offer_0=(|me_en);
 assign w_ready[0]=source_write_ready_0&&!exhausted[5]&&!w_visible[0];
 assign accept[5]=write_offer_0&&w_ready[0];
 ot_ds_owned_ratio_boundary #(.W(2236),.ENABLE(ENABLE)) write_0(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_fast),.abort_d(abort_slow),.in_v(write_offer_0&&!exhausted[5]&&!w_visible[0]),.in_ready(source_write_ready_0),
 .in_data(wsource_0),.in_owner(issued_owner[1140+:228]),.out_v(wv[0]),.out_ready(wr[0]),.out_data(wpacket_0),.out_owner(wo[0+:228]),
 .retire_v(wret[0]),.retire_ready(wretr[0]),.retire_owner(wro[0+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(w_pending[0]),.quarantined(wquar[0]),.pending_owner());
 wire [8063:0] wpacket_1;wire [8063:0] wsource_1;assign wsource_1={row_en,row_addr,row_data};wire source_write_ready_1;
 wire write_offer_1=(|row_en);
 assign w_ready[1]=source_write_ready_1&&!exhausted[6]&&!w_visible[1];
 assign accept[6]=write_offer_1&&w_ready[1];
 ot_ds_owned_ratio_boundary #(.W(8064),.ENABLE(ENABLE)) write_1(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_fast),.abort_d(abort_slow),.in_v(write_offer_1&&!exhausted[6]&&!w_visible[1]),.in_ready(source_write_ready_1),
 .in_data(wsource_1),.in_owner(issued_owner[1368+:228]),.out_v(wv[1]),.out_ready(wr[1]),.out_data(wpacket_1),.out_owner(wo[228+:228]),
 .retire_v(wret[1]),.retire_ready(wretr[1]),.retire_owner(wro[228+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(w_pending[1]),.quarantined(wquar[1]),.pending_owner());
 wire [2111:0] wpacket_2;wire [2111:0] wsource_2;assign wsource_2={coll_en,coll_wordaddr,coll_data};wire source_write_ready_2;
 wire write_offer_2=(|coll_en);
 assign w_ready[2]=source_write_ready_2&&!exhausted[7]&&!w_visible[2];
 assign accept[7]=write_offer_2&&w_ready[2];
 ot_ds_owned_ratio_boundary #(.W(2112),.ENABLE(ENABLE)) write_2(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_fast),.abort_d(abort_slow),.in_v(write_offer_2&&!exhausted[7]&&!w_visible[2]),.in_ready(source_write_ready_2),
 .in_data(wsource_2),.in_owner(issued_owner[1596+:228]),.out_v(wv[2]),.out_ready(wr[2]),.out_data(wpacket_2),.out_owner(wo[456+:228]),
 .retire_v(wret[2]),.retire_ready(wretr[2]),.retire_owner(wro[456+:228]),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(w_pending[2]),.quarantined(wquar[2]),.pending_owner());
 ot_ds_native_write_formats formats(.me(wpacket_0),.row(wpacket_1),.coll(wpacket_2),.enable(we),.addr(wa),.data(wd),.bad(formats_bad));
 ot_ds_shared_native_vm_provider #(.ENABLE(ENABLE)) provider(
 .clk(slow_clk),.cold_n(cold_n),.rst_n(slow_rst_n),.abort(abort_slow),
 .r_v(rv),.r_ready(rr),.r_enable(re),.r_addr(ra),.r_owner(ro),.q_v(pqv),.q_ready(pqr),.q_data(pqdata),.q_owner(pqo),
 .consumed(consumed),.consumed_owner(qpo),.r_retire(reqret),.r_retire_ready(reqrr),.r_retire_owner(reqro),
 .w_v(wv),.w_ready(wr),.w_enable(we),.w_addr(wa),.w_data(wd),.w_format_bad(formats_bad),.w_owner(wo),
 .w_retire(wret),.w_retire_ready(wretr),.w_retire_owner(wro),.fault(provider_fault),.quarantined(provider_quarantine),.debt(provider_debt),
 .debug_native_write_accept(debug_native_write_accept),.debug_native_visible(debug_native_visible),.debug_native_read_accept(debug_native_read_accept));
endmodule
`default_nettype wire
