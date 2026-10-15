`timescale 1ns/1ps
// HBM opt-in real balanced KP4 with4localTX/8recoveredRX register-bank roots.
// No legacy clock fallback. Siblings require measured same-family phase;
// supplying same-phase clocks in a functional bench is not physical proof.
module hfd_serdes487_rooted #(parameter integer EMUT=0,DMUT=0)(
 input wire clk,clk_collect,clk_encode,clk_codeword,
 input wire rclk_syndrome,rclk_bm0,rclk_bm1,rclk_bm2,rclk_bm3,rclk_chien,rclk_emit,
 input wire rst_n,input wire[486:0]tx,output reg[486:0]rx,
 output wire[1:0]st,output reg padding_fault,
 output wire[543:0]pma_tx,output wire pma_tck,
 input wire[543:0]pma_rx,input wire pma_rck
);
 reg[1:0]rs_t,rs_r;
 always @(posedge clk or negedge rst_n)if(!rst_n)rs_t<=0;else rs_t<={rs_t[0],1'b1};
 always @(posedge pma_rck or negedge rst_n)if(!rst_n)rs_r<=0;else rs_r<={rs_r[0],1'b1};
 wire rn_t=rs_t[1],rn_r=rs_r[1];reg[486:0]tx_pin;wire[511:0]rx_word;
 always @(posedge clk)begin tx_pin<=tx;rx<=rx_word[486:0];end
 always @(posedge clk or negedge rst_n)if(!rst_n)padding_fault<=0;else if(st[1]&&rx_word[511:487]!==25'd0)padding_fault<=1;
 wire ev,ef;wire[543:0]ed;
 ot_hbm_kp4_enc_rooted #(.MUT(EMUT))u_enc(.clk_ctrl(clk),.clk_collect(clk_collect),.clk_encode(clk_encode),.clk_codeword(clk_codeword),.rst_n(rn_t),.tx_v(rn_t),.tx_d({25'd0,tx_pin}),.p_v(ev),.p_d(ed),.fault(ef));
 ot_s81_pma_bm #(.W(544),.LAT(4))u_ptx(.clk(clk),.d_v(ev),.d(ed),.q(pma_tx));
 assign pma_tck=clk;
 wire[543:0]rd;
 ot_s81_pma_bm #(.W(544),.LAT(4))u_prx(.clk(pma_rck),.d_v(1'b1),.d(pma_rx),.q(rd));
 wire qv,qfirst,qunc,lock;wire[511:0]qd;wire[4:0]qn;wire[7:0]qs;wire[31:0]nc,nu,nr;
 ot_hbm_kp4_dec_rooted #(.MUT(DMUT))u_dec(.clk_capture(pma_rck),.clk_syndrome(rclk_syndrome),.clk_bm0(rclk_bm0),.clk_bm1(rclk_bm1),.clk_bm2(rclk_bm2),.clk_bm3(rclk_bm3),.clk_chien(rclk_chien),.clk_emit(rclk_emit),.rst_n(rn_r),.p_v(rn_r),.p_d(rd),.q_v(qv),.q_d(qd),.q_first(qfirst),.q_unc(qunc),.q_nerr(qn),.q_seq(qs),.lock(lock),.n_corr(nc),.n_unc(nu),.n_relock(nr));
 reg unc_r;
 always @(posedge pma_rck or negedge rn_r)if(!rn_r)unc_r<=0;else if(qv&&qfirst&&qunc)unc_r<=1;
 wire rm_fault;
 ot_s81_rate_match u_rm(.wclk(pma_rck),.wrst_n(rn_r),.w_v(qv),.w_d(qd),.rclk(clk),.rrst_n(rn_t),.r_d(rx_word),.fault(rm_fault));
 reg[1:0]lk_s,uf_s;reg[1:0]st_q;
 always @(posedge clk or negedge rn_t)
 if(!rn_t)begin lk_s<=0;uf_s<=0;st_q<=0;end
 else begin lk_s<={lk_s[0],lock};uf_s<={uf_s[0],unc_r};st_q<={lk_s[1],st_q[0]|uf_s[1]|rm_fault|ef};end
 assign st=st_q;
endmodule
