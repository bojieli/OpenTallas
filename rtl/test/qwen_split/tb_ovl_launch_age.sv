`timescale 1ns/1ps
// Boundary model: compute face input/output PR1, D2D calendar input PR1, calendar event, D2D slot output PR1.
module tb_ovl_launch_age;
 parameter DIR="scratch/selected_F16_origin0_model";
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0,ep=0,ep_pr=0;
 always @(posedge ck)ep_pr<=ep;
 wire[11:0]ta,ra;reg[31:0]tx[0:4095],rx[0:4095],tq,rq,tcap,rcap;
 initial begin $readmemh({DIR,"/list_C_tx.memh"},tx);$readmemh({DIR,"/list_C_rx.memh"},rx);end
 always @(posedge ck)begin tq<=tx[ta];rq<=rx[ra];tcap<=tq;rcap<=rq;end
 wire cs,cg,rs,rg,cw,rw,ad,ready,sf;wire[5:0]ca;wire[31:0]cd;wire[1:0]ut,ur;
 ot_qwen_d2d_ovl_seq #(.AW(12),.ADM(0),.FIRST_OFS(1176)) seq(.ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(ep_pr),.halt(1'b0),
 .cfg_tx_we(cw),.cfg_rx_we(rw),.cfg_addr(ca),.cfg_data(cd),.cal_start(cs),.cal_seg(cg),.cal_start_rx(rs),.cal_seg_rx(rg),
 .cal_user_tx(ut),.cal_user_rx(ur),.tx_rom_addr(ta),.tx_rom_q(tcap),.rx_rom_addr(ra),.rx_rom_q(rcap),.cal_ready(ready),.adm_done(ad),.running(),.fault(sf));
 reg cs_out=0,rs_out=0,cs_in=0;
 always @(posedge ck)begin cs_out<=cs;rs_out<=rs;cs_in<=cs_out;end
 // Minimal real one-event request calendar, programmed before the epoch; a request has dt1 after its start.
 reg we=0;reg[5:0]a=0;reg[31:0]d=0;
 wire ev;wire[2:0]p;wire[3:0]k;wire[4:0]b;wire cf;
 ot_qwen_d2d_cal cal(.ck(ck),.rst_n(rst_n),.cfg_we(we),.cfg_addr(a),.cfg_data(d),.start(cs_in),.start_seg(1'b0),.halt(1'b0),
 .ev_v(ev),.ev_port(p),.ev_kind(k),.ev_beat(b),.running(),.fault(cf));
 reg slot_out=0;always @(posedge ck)slot_out<=ev;
 integer cyc=0,anchor=-1;integer core=-1,face=-1,receive=-1,slot=-1;integer rface=-1;
 always @(posedge ck)begin
  cyc=cyc+1;if(ep&&anchor<0)anchor=cyc;
  #0.01;
  if(anchor>=0)begin
   if(cs&&core<0)core=cyc-anchor;
   if(cs_out&&face<0)face=cyc-anchor;
   if(cs_in&&receive<0)receive=cyc-anchor;
   if(slot_out&&slot<0)slot=cyc-anchor;
   if(rs_out&&rface<0)rface=cyc-anchor;
   if(slot>=0&&rface>=0)begin
    if(sf||cf||core!=1966||face!=1967||receive!=1968||slot!=1971||rface!=3773)
      $display("OVL_LAUNCH_FAIL core%0d face%0d calpin%0d slot%0d rxface%0d sf%b cf%b",core,face,receive,slot,rface,sf,cf);
    else $display("OVL_LAUNCH_PASS core%0d face%0d calpin%0d slot%0d rxface%0d TXslot_minus_rawCMD%0d",core,face,receive,slot,rface,slot-774);
    $finish;
   end
  end
 end
 initial begin
  repeat(5)@(negedge ck);rst_n=1;we=1;a=0;d=32'h00060400;@(negedge ck);we=0;
  repeat(100)@(negedge ck);ep=1;@(negedge ck);ep=0;
  repeat(10000)@(negedge ck);$display("OVL_LAUNCH_FAIL timeout");$finish;
 end
endmodule
