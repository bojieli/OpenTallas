`timescale 1ns/1ps
`default_nettype none
// Current physical-plan provider. All codecs are existing exact transports.
// h_tx[276] is live job-active; draft traffic uses real stage kind7, no draft PHY.
module ot_s81hd_ctl_core #(parameter integer SK=11)(
 input wire ck,rst_n,start_i,lep_fault_i, input wire[10:0]lw_i,
 input wire[1103:0]lepk_i0, output wire[1103:0]lepk_o0,
 output wire lepf_o0, output wire[44:0]unit_o0,input wire[31:0]ctrl_i0,
 output wire[564:0]x_o,input wire[564:0]b_i,
 output wire[276:0]h_tx_o,input wire[275:0]h_rx_i,
 output wire[63:0]a_tx_o,b7_tx_o,n_tx_o,input wire[63:0]a_rx_i,b7_rx_i,n_rx_i
);
 wire[1:0]htv,hrv;wire[1105:0]htd,hrd;wire[5:0]mtv,mrv;wire[3317:0]mtd,mrd;
 wire[2:0]txf,rxf;wire[35:0]epf;wire host_rf,host_tf;reg adapter_fault;
 wire[552:0]host_frame;wire host_v;
 ot_s81hd_host276_rx u_hr(.ck(ck),.rn(rst_n),.lane(h_rx_i),.v(host_v),.frame(host_frame),.fault(host_rf));
 assign hrv={host_v&&host_frame[3:0]==6,host_v&&host_frame[3:0]==7};
 assign hrd={host_frame,host_frame};
 wire[63:0]ml[0:2];assign ml[0]=a_rx_i;assign ml[1]=b7_rx_i;assign ml[2]=n_rx_i;
 wire[63:0]mo[0:2];assign a_tx_o=mo[0];assign b7_tx_o=mo[1];assign n_tx_o=mo[2];
 genvar k;
 generate for(k=0;k<3;k=k+1)begin:g_mesh
  ot_s81hd_best64_tx u_tx(.ck(ck),.rn(rst_n),.v(mtv[2*k]),.frame(mtd[2*k*553+:553]),.lane(mo[k]),.fault(txf[k]));
  wire[552:0]f;
  ot_s81hd_mesh64_rx u_rx(.ck(ck),.rn(rst_n),.lane(ml[k]),.va(mrv[2*k]),.vb(mrv[2*k+1]),.frame(f),.ep_fault(epf[k*12+:12]),.fault(rxf[k]));
  assign mrd[k*1106+:1106]={f,f};
 end endgenerate
 // A result and status have distinct single-entry holds; result wins the shared
 // three-cycle link slot. Overwrite is a fault; there is no hidden backpressure.
 reg rp,sp;reg[552:0]rq,sq;reg[1:0]cooldown;
 wire send=(cooldown==0)&&(rp||sp);wire[552:0]send_frame=rp?rq:sq;
 always@(posedge ck or negedge rst_n)
  if(!rst_n)begin rp<=0;sp<=0;cooldown<=0;end
  else begin
   if(cooldown!=0)cooldown<=cooldown-1'b1;
   if(send)begin cooldown<=2;if(rp)rp<=0;else sp<=0;end
   if(htv[0])begin rp<=1;rq<=htd[552:0];end
   if(htv[1])begin sp<=1;sq<=htd[1105:553];end
  end
 wire[275:0]hlane;wire job;
 ot_s81hd_host276_tx u_ht(.ck(ck),.rn(rst_n),.v(send),.frame(send_frame),.lane(hlane),.fault(host_tf));
 assign h_tx_o={job,hlane};
 wire[1103:0]core_ro;wire[33:0]muc;wire[10:0]murc;wire[564:0]unused_duplicate;
 wire dv;wire[552:0]dd;wire[0:0]unused_dv;wire[552:0]unused_dd;
 
 // Input kind7 carries HSF0 type in gidx[3:0] and its payload in flit512.
 wire dvalid=lepk_i0[0]&&lepk_i0[3:1]==7;
 wire[552:0]dframe={1'b1,24'd0,lepk_i0[532:21],12'd0,lepk_i0[16:13]};
 ot_s81hd_ctl_hsf0_static #(.SK(SK))u_logic(
  .ck(ck),.rst_n(rst_n),.start_i(start_i),.adapter_fault(adapter_fault),.job_active_o(job),
  .ri(lepk_i0),.mu_rt(ctrl_i0),.lw(lw_i),.lep_f(lep_fault_i),.ro(core_ro),.mu_c(muc),.mu_rc(murc),.ctl_f(lepf_o0),
  .sn_o(x_o),.ss_o(unused_duplicate),.sn_i(b_i),.ss_i(b_i),
  .mtx_v(mtv),.mtx_d(mtd),.mrx_v(mrv),.mrx_d(mrd),.mflt({24{(|epf)||(|rxf)||(|txf)}}),
  .htx_v(htv),.htx_d(htd),.hrx_v(hrv),.hrx_d(hrd),.hflt({8{host_rf||host_tf}}),
  .dtx_v(unused_dv),.dtx_d(unused_dd),.drx_v(dvalid),.drx_d(dframe),.dflt({4{lep_fault_i}}),
  .draft_slot_free(!adapter_fault),.draft_valid_o(dv),.draft_frame_o(dd));
 assign unit_o0={muc,murc};
 assign lepk_o0=core_ro;
 always@(posedge ck or negedge rst_n)
  if(!rst_n)adapter_fault<=0;
  else if((htv[0]&&rp&&!(send&&rp))||(htv[1]&&sp&&!(send&&!rp)) ||
    (host_v&&host_frame[3:0]==8&&(|host_frame[32:16]))||host_rf||host_tf||(|txf)||(|rxf)||(|epf))adapter_fault<=1;
endmodule
`default_nettype wire
