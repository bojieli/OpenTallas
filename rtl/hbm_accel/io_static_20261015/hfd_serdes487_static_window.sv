`timescale 1ns/1ps
`default_nettype none
// Opt-in native FEC composition candidate. Replaces the marker-sensitive rate
// matcher with real finite-window register storage and compiled reservations.
// No production source/clock calendar or physical view is inferred by this RTL.
// Startup alignment/lock is initialization; normal window starts and every word
// transfer must have explicit compiler-assigned cycles. No data-driven starts.
module hfd_serdes487_static_window #(
 parameter integer EMUT=0,DMUT=0,WINDOW_WORDS=2048,CDC_AW=4
)(
 input wire clk,clk_collect,clk_encode,clk_codeword,
 input wire rclk_syndrome,rclk_bm0,rclk_bm1,rclk_bm2,rclk_bm3,rclk_chien,rclk_emit,
 input wire rst_n,input wire [486:0] tx,
 input wire capture_start,capture_take,capture_last,
 input wire read_start,read_take,read_last,
 output wire [486:0] rx,output wire rx_v,
 output wire [1:0] st,output wire padding_fault,
 output wire [543:0] pma_tx,output wire pma_tck,
 input wire [543:0] pma_rx,input wire pma_rck
);
 reg [1:0] rs_t,rs_r;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)rs_t<=0;else rs_t<={rs_t[0],1'b1};
 always @(posedge pma_rck or negedge rst_n)
 if(!rst_n)rs_r<=0;else rs_r<={rs_r[0],1'b1};
 wire rn_t=rs_t[1],rn_r=rs_r[1];
 reg [486:0] tx_pin;
 always @(posedge clk)tx_pin<=tx;
 wire ev,ef;wire [543:0] ed;
 ot_hbm_kp4_enc_rooted #(.MUT(EMUT)) u_enc(
 .clk_ctrl(clk),.clk_collect(clk_collect),.clk_encode(clk_encode),.clk_codeword(clk_codeword),
 .rst_n(rn_t),.tx_v(rn_t),.tx_d({25'd0,tx_pin}),.p_v(ev),.p_d(ed),.fault(ef));
 ot_s81_pma_bm #(.W(544),.LAT(4)) u_ptx(.clk(clk),.d_v(ev),.d(ed),.q(pma_tx));
 assign pma_tck=clk;
 wire [543:0] rd;
 ot_s81_pma_bm #(.W(544),.LAT(4)) u_prx(.clk(pma_rck),.d_v(1'b1),.d(pma_rx),.q(rd));
 wire qv,qfirst,qunc,locked;wire [511:0] qd;
 wire [4:0] qn;wire [7:0] qs;wire [31:0] nc,nu,nr;
 ot_hbm_kp4_dec_rooted #(.MUT(DMUT)) u_dec(
 .clk_capture(pma_rck),.clk_syndrome(rclk_syndrome),.clk_bm0(rclk_bm0),.clk_bm1(rclk_bm1),
 .clk_bm2(rclk_bm2),.clk_bm3(rclk_bm3),.clk_chien(rclk_chien),.clk_emit(rclk_emit),
 .rst_n(rn_r),.p_v(rn_r),.p_d(rd),.q_v(qv),.q_d(qd),.q_first(qfirst),.q_unc(qunc),
 .q_nerr(qn),.q_seq(qs),.lock(locked),.n_corr(nc),.n_unc(nu),.n_relock(nr));
 reg capture_active,unc_r,pad_r;
 always @(posedge rclk_emit or negedge rn_r)
 if(!rn_r)begin capture_active<=0;unc_r<=0;pad_r<=0;end
 else begin
  if(capture_start)capture_active<=1;
  else if(capture_take && capture_last)capture_active<=0;
  if(qv && qfirst && qunc)unc_r<=1;
  if(capture_active && capture_take && qv && qd[511:487]!==25'd0)pad_r<=1;
 end
 wire wf,rf;
 ot_hbm_static_word_cdc #(.W(487),.AW(CDC_AW),.WORDS(WINDOW_WORDS)) u_window(
 .wclk(rclk_emit),.rclk(clk),.rst_n(rst_n),
 .w_start(capture_start),.w_take(capture_take),.w_last(capture_last),
 .w_observed_v(qv && capture_active && !capture_start),.w_data(qd[486:0]),
 .r_start(read_start),.r_take(read_take),.r_last(read_last),
 .r_v(rx_v),.r_data(rx),.w_fault(wf),.r_fault(rf));
 reg [1:0] lock_s,unc_s,wf_s,pad_s;
 reg status_fault;
 always @(posedge clk or negedge rn_t)
 if(!rn_t)begin lock_s<=0;unc_s<=0;wf_s<=0;pad_s<=0;status_fault<=0;end
 else begin
  lock_s<={lock_s[0],locked};unc_s<={unc_s[0],unc_r};
  wf_s<={wf_s[0],wf};pad_s<={pad_s[0],pad_r};
  status_fault<=status_fault|unc_s[1]|wf_s[1]|pad_s[1]|rf|ef;
 end
 assign st={lock_s[1],status_fault};
 assign padding_fault=pad_s[1];
endmodule
`default_nettype wire
