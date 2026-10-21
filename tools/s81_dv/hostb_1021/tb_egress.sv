`timescale 1ns/1ps
module tb_egress;
reg ck=0;always #0.5 ck=~ck;
reg rst_n=0;integer cyc=-1,mode=0,bad=0,count=0;
reg[1:0] lv=0;reg[1105:0] ld=0;reg ev=0,slot=0;reg[552:0] ed=0;
wire[1:0] hv,dv;wire[1105:0] hd,dd;wire[2:0] fault,df;
localparam[552:0] EVENT={1'b1,536'hfedcba9876543210,16'h0a};
dsdv_hostb_head_egress #(.ENABLE(1)) dut(.ck(ck),.rst_n(rst_n),.legacy_v(lv),.legacy_d(ld),.event_v(ev),.event_d(ed),.event_slot(slot),.host_v(hv),.host_d(hd),.fault(fault));
dsdv_hostb_head_egress deflt(.ck(ck),.rst_n(rst_n),.legacy_v(lv),.legacy_d(ld),.event_v(ev),.event_d(ed),.event_slot(slot),.host_v(dv),.host_d(dd),.fault(df));
initial if(!$value$plusargs("MODE=%d",mode))mode=0;
always @(negedge ck)begin cyc++;rst_n=cyc>=3;end
// Model real synchronous producer pins, held through their next capture edge.
always @(posedge ck)begin
 ev<=cyc==20&&mode!=3;slot<=cyc==20&&mode!=2;
 ed<=EVENT;ld<={553'h123456789,553'habcdef00};
 lv<=((cyc==14||cyc==16)?2'b11:((cyc==22&&mode==4)?2'b01:2'b00));
end
always @(posedge ck)begin
 #0.02;
 if(dv!==lv||dd!==ld||df)$fatal(1,"default-off identity");
 if(lv[1]&&(hv[1]!==lv[1]||hd[1105:553]!==ld[1105:553]))$fatal(1,"legacy lane1");
 if((cyc==14||cyc==16)&&(hv!==lv||hd!==ld))$fatal(1,"legacy passthrough age/data");
 if(cyc==22)begin
  if(mode==0)begin if(hv[0]!==1||hd[552:0]!==EVENT)$fatal(1,"booked event age/data");count++;end
  else if(hv[0])$fatal(1,"causal emitted lane0");
 end
 if(cyc==26)begin
  if(mode==0&&(fault||count!=1))$fatal(1,"base fault");
  if(mode==2&&!fault[1])$fatal(1,"unbooked not caught");
  if(mode==3&&!fault[0])$fatal(1,"missing not caught");
  if(mode==4&&!fault[2])$fatal(1,"collision not caught");
  $display("PASS HEAD_EGRESS mode%0d defaultidentity/legacyage fault%h",mode,fault);$finish;
 end
end
endmodule
