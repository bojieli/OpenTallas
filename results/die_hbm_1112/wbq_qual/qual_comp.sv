`timescale 1ns/1ps
`default_nettype none
// HBM-WBQ-QUAL-1: ot_hbm_svc_wb_kport_q composition = 4 root slots + ot_wbq_sw (reform_1105b, the sw the d44v plan builds) + 16 K pin skids
// (inside ot_wbq_sw). NEWROOT=0: ot_wbq_root_g2 of reform_1105b (old g0 grp + old g1 grp_ps); NEWROOT=1: qual_s7_g2 (ROOT S7 + CBREG/SSTOPREG/GREG).
// Separate fifo_clk and hbm_clk (the die has two clocks); stream_clk = the one fifo_clk of all four roots.
// Observation outputs (bench only): root-side activity counts, taken by hierarchical probes that are identical in both forms.
module qual_comp #(parameter integer NEWROOT=0, parameter integer HREG=2, parameter integer GIN=0,
                   parameter integer CBREG=1, parameter integer SSTOPREG=1, parameter integer GREG=1,
                   parameter integer MUTCB=0, parameter integer MUTSTOP=0, parameter integer CRED=4)(
 input wire fifo_clk,hbm_clk,stream_rst_n,hbm_rst_n,
 input wire [1:0] stk,input wire quad,
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire [15:0] wb_reserve_epoch,wb_fill_epoch,
 input wire [11:0] wb_reserve_sectors,input wire [31:0] wb_reserve_base,
 input wire wb_fill_start,input wire [2311:0] wd,
 output wire wb_ready,output wire [11:0] wa,output wire wbw_v,output wire [29:0] wbw_base,output wire [11:0] wbw_total,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata,input wire [15:0] w_k_wr_done,
 output wire fault,
 output wire s_stop,h_stop,copy_on,copy_sel,
 // observation: per root group (8 groups) event counts of this fifo_clk / hbm_clk cycle
 output wire [31:0] obs_fillw,    // 4 bits per group: lane fill SRAM writes (fifo_clk)
 output wire [31:0] obs_fifowe,   // 4 bits per group: lane FIFO enqueues (fifo_clk)
 output wire [31:0] obs_memrd,    // 4 bits per group: lane SRAM reads (fifo_clk)
 output wire [7:0] obs_gv         // group valid at the seam (hbm_clk)
);
 wire [3:0] root_ready;wire [7:0] g_v,g_credit,root_id;wire [2287:0] g_d;
 wire [263:0] wd_c;
 genvar k,r;
 generate for(k=0;k<8;k=k+1)begin:g_wc assign wd_c[33*k+:33]={wd[289*k+288],wd[289*k+256+:32]}; end endgenerate
 wire [7:0] wdv;generate for(k=0;k<8;k=k+1)begin:g_wv assign wdv[k]=wd[289*k+288]; end endgenerate
 generate for(r=0;r<4;r=r+1)begin:g_r
  if(NEWROOT)begin:g_n
   qual_s7_g2 #(.CRED(CRED),.CBREG(CBREG),.SSTOPREG(SSTOPREG),.GREG(GREG),.MUTCB(MUTCB),.MUTSTOP(MUTSTOP)) u_root(
    .hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.root_id(root_id[2*r+:2]),
    .reserve_v(wb_reserve_v),.reserve_bank(wb_reserve_bank),.reserve_total(wb_reserve_sectors),.reserve_base(wb_reserve_base[29:0]),
    .fill_start(wb_fill_start),.fill_start_bank(wb_fill_bank),
    .wd0(wd[0+:256]),.wd1(wd[289+:256]),.wd2(wd[578+:256]),.wd3(wd[867+:256]),.wd4(wd[1156+:256]),.wd5(wd[1445+:256]),.wd6(wd[1734+:256]),.wd7(wd[2023+:256]),.wd_v(wdv),
    .copy_on(copy_on),.copy_bank(copy_sel),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit[2*r+:2]),
    .root_ready(root_ready[r]),.g_v(g_v[2*r+:2]),.g_d(g_d[572*r+:572]));
  end else begin:g_o
   ot_wbq_root_g2 #(.CRED(CRED)) u_root(
    .hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.root_id(root_id[2*r+:2]),
    .reserve_v(wb_reserve_v),.reserve_bank(wb_reserve_bank),.reserve_total(wb_reserve_sectors),.reserve_base(wb_reserve_base[29:0]),
    .fill_start(wb_fill_start),.fill_start_bank(wb_fill_bank),
    .wd0(wd[0+:256]),.wd1(wd[289+:256]),.wd2(wd[578+:256]),.wd3(wd[867+:256]),.wd4(wd[1156+:256]),.wd5(wd[1445+:256]),.wd6(wd[1734+:256]),.wd7(wd[2023+:256]),.wd_v(wdv),
    .copy_on(copy_on),.copy_bank(copy_sel),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit[2*r+:2]),
    .root_ready(root_ready[r]),.g_v(g_v[2*r+:2]),.g_d(g_d[572*r+:572]));
  end
  // probes (same instance names in both forms)
  genvar gg,l;
  for(gg=0;gg<2;gg=gg+1)begin:g_p
   for(l=0;l<4;l=l+1)begin:g_l
    if(NEWROOT)begin:pn
     if(gg==0)begin:q0
      assign obs_fillw[8*r+4*gg+l]=g_r[r].g_n.u_root.u_g0.u_grp.g_lane[l].u_payload.w_ce_in;
      assign obs_fifowe[8*r+4*gg+l]=g_r[r].g_n.u_root.u_g0.u_grp.fifo_we[l];
      assign obs_memrd[8*r+4*gg+l]=g_r[r].g_n.u_root.u_g0.u_grp.mem_read[l];
     end else begin:q1
      assign obs_fillw[8*r+4*gg+l]=g_r[r].g_n.u_root.u_g1.u_grp.g_lane[l].u_payload.w_ce_in;
      assign obs_fifowe[8*r+4*gg+l]=g_r[r].g_n.u_root.u_g1.u_grp.fifo_we[l];
      assign obs_memrd[8*r+4*gg+l]=g_r[r].g_n.u_root.u_g1.u_grp.mem_read[l];
     end
    end else begin:po
     if(gg==0)begin:q0
      assign obs_fillw[8*r+4*gg+l]=g_r[r].g_o.u_root.u_g0.u_grp.g_lane[l].u_payload.w_ce_in;
      assign obs_fifowe[8*r+4*gg+l]=g_r[r].g_o.u_root.u_g0.u_grp.fifo_we[l];
      assign obs_memrd[8*r+4*gg+l]=g_r[r].g_o.u_root.u_g0.u_grp.mem_read[l];
     end else begin:q1
      assign obs_fillw[8*r+4*gg+l]=g_r[r].g_o.u_root.u_g1.u_grp.g_lane[l].u_payload.w_ce_in;
      assign obs_fifowe[8*r+4*gg+l]=g_r[r].g_o.u_root.u_g1.u_grp.fifo_we[l];
      assign obs_memrd[8*r+4*gg+l]=g_r[r].g_o.u_root.u_g1.u_grp.mem_read[l];
     end
    end
   end
  end
 end endgenerate
 assign obs_gv=g_v;
 ot_wbq_sw #(.HREG(HREG),.GIN(GIN),.CRED(CRED)) u_sw(.stream_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.stk(stk),.quad(quad),
  .wb_reserve_v(wb_reserve_v),.wb_reserve_bank(wb_reserve_bank),.wb_fill_bank(wb_fill_bank),.wb_reserve_epoch(wb_reserve_epoch),.wb_fill_epoch(wb_fill_epoch),
  .wb_reserve_sectors(wb_reserve_sectors),.wb_reserve_base(wb_reserve_base),.wb_fill_start(wb_fill_start),.wd_c(wd_c),.wb_ready(wb_ready),.wa(wa),
  .wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),.w_k_v(w_k_v),.w_k_rdy(w_k_rdy),.w_k_addr(w_k_addr),.w_k_wdata(w_k_wdata),.w_k_wr_done(w_k_wr_done),.fault(fault),
  .root_ready(root_ready),.g_v(g_v),.g_d(g_d),.g_credit(g_credit),.root_id(root_id),.copy_on(copy_on),.copy_sel(copy_sel),.s_stop(s_stop),.h_stop(h_stop));
endmodule
`default_nettype wire
