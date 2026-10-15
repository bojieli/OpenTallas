`timescale 1ns/1ps
module tb_s81_static_fmt1_channels;
 parameter MUT=0; parameter CLOCKED=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[4:0]tx_slot=0,rx_slot=0;reg[9:0]tx_kind=0,rx_kind=0;
 reg vm_tx_last=0,vm_tx_valid=0;reg[2:0]vm_tx_channel=0;reg[551:0]vm_tx_payload=0;
 reg[513:0]wfc_tx=0;reg host_tx_valid=0;reg[10:0]host_status=0;reg[64:0]host_completion=0;
 wire vm_rx_last,vm_rx_valid;wire[2:0]vm_rx_channel;wire[551:0]vm_rx_payload;
 wire[513:0]wfc_rx;wire[515:0]host_rx;
 reg[49:0]tx_seq=0,rx_expected_seq=0;reg[4:0]rx_expected_last=0;
 reg[4:0]tx_beat_slot=0,tx_frame_slot=0,rx_beat_slot=0,rx_frame_slot=0;
 reg[9:0]tx_phase=0,rx_phase=0;
 wire[4:0]phy_tx_valid,phy_rx_valid;wire[2559:0]phy_tx_data,phy_rx_data;wire fault;
 assign phy_rx_valid=phy_tx_valid;assign phy_rx_data=phy_tx_data;
 generate if(CLOCKED)begin:G_CLOCKED
 wire[4:0]clk_lane={5{clk}};
 s81_static_fmt1_channels_clocked #(.MUT(MUT)) dut(.*,.clk_adapter(clk));
 end else begin:G_SINGLE
 s81_static_fmt1_channels #(.MUT(MUT)) dut(.*);
 end endgenerate
 function automatic[551:0] value(input integer n);
 begin for(integer b=0;b<552;b=b+1)value[b]=((b*3+n*7)%19)<9;end endfunction
 function automatic[31:0] crc(input[562:0]p);
 reg[31:0]x;begin x=32'hffffffff;for(integer b=562;b>=0;b=b-1)x={x[30:0],1'b0}^((x[31]^p[b])?32'h04c11db7:32'b0);crc=x;end endfunction
 function automatic[551:0] sent(input integer n);
 reg[551:0]p;begin p=value(n);case(n%3)
  0:sent=p;1:sent={1'b1,39'b0,p[511:0]};
  default:sent={1'b1,470'b0,11'h345,5'b0,1'b1,64'hf0e1d2c3b4a59687};endcase end endfunction
 wire legacy_v,legacy_lock,legacy_fault;wire[594:0]legacy_frame;
 ot_s81ph_link_gbx #(.FMT(1)) legacy_rx(.clk(clk),.rst_n(rst_n),.f_tx_v(1'b0),.f_tx(595'b0),
 .r_tx_v(1'b0),.r_tx(53'b0),.beat_tx(),.beat_rx_v(phy_tx_valid[0]),.beat_rx(phy_tx_data[511:0]),
 .f_rx_v(legacy_v),.f_rx(legacy_frame),.r_rx_v(),.r_rx(),.locked(legacy_lock),.fault(legacy_fault));
 integer cyc,n,c,k,p,g,j;integer checks=0,legacy_checks=0;
 reg last;reg[551:0]v;reg[562:0]pay;
 initial begin
 repeat(3)@(negedge clk);rst_n=1;
 for(cyc=0;cyc<300;cyc=cyc+1)begin
  tx_slot=0;rx_slot=0;tx_kind=0;rx_kind=0;vm_tx_valid=0;wfc_tx=0;host_tx_valid=0;
  tx_beat_slot=0;rx_beat_slot=0;tx_frame_slot=0;rx_frame_slot=0;tx_phase=0;rx_phase=0;
  // Four-cycle beat spacing is a declared compiler cadence, not a ready loop.
  for(j=0;j<18;j=j+1)for(p=0;p<4;p=p+1)begin
   if(cyc==3+16*j+4*p)begin tx_beat_slot=31;tx_phase={5{2'(p)}};
    if(j>=2 && j<17 && p==0)tx_frame_slot[(j-2)%5]=1;end
   if(cyc==4+16*j+4*p)begin rx_beat_slot=31;rx_phase={5{2'(p)}};
    if(j>=2 && j<17 && p==1)rx_frame_slot[(j-2)%5]=1;end
  end
  for(n=0;n<15;n=n+1)begin
   c=n%5;k=n%3;last=(k==0)?1'b0:1'b1;v=value(n);
   if(cyc==32+16*n)begin tx_slot[c]=1;tx_kind[c*2+:2]=2'(k);case(k)
    0:begin vm_tx_valid=1;vm_tx_last=last;vm_tx_channel=3'(c);vm_tx_payload=v;end
    1:wfc_tx={last,v[511:0],1'b1};
    2:begin host_tx_valid=1;host_status=11'h345;host_completion={1'b1,64'hf0e1d2c3b4a59687};end
   endcase end
   if(cyc==33+16*n)tx_seq[c*10+:10]=10'(n);
   if(cyc==41+16*n)begin rx_expected_seq[c*10+:10]=10'(n);rx_expected_last[c]=last;end
   if(cyc==43+16*n)begin rx_slot[c]=1;rx_kind[c*2+:2]=2'(k);end
  end
  @(posedge clk);#2;
  if(fault)$fatal(1,"composition fault cycle%0d",cyc);
  if(legacy_fault)$fatal(1,"legacy gearbox fault");
  if(legacy_v)begin
   n=int'(legacy_frame[594:585]);last=(n%3==0)?1'b0:1'b1;pay={10'(n),last,sent(n)};
   if(legacy_frame!=={pay,crc(pay)})$fatal(1,"legacy full552/last/sequence/CRC interoperability");legacy_checks=legacy_checks+1;
  end
  if(cyc>=43 && (cyc-43)%16==0 && (cyc-43)/16<15)begin
   n=(cyc-43)/16;c=n%5;k=n%3;v=value(n);
   case(k)
    0:if(!vm_rx_valid||vm_rx_channel!==3'(c)||vm_rx_payload!==v||vm_rx_last!==0)$fatal(1,"VM552 receive");
    1:if(wfc_rx!=={1'b1,v[511:0],1'b1})$fatal(1,"WFC514 receive");
    2:if(host_rx!=={434'b0,11'h345,5'b0,1'b1,64'hf0e1d2c3b4a59687,1'b1})$fatal(1,"host516 receive");
   endcase
   checks=checks+1;
  end else if(vm_rx_valid||wfc_rx[0]||host_rx[0])$fatal(1,"unscheduled result");
  @(negedge clk);
 end
 if(checks!=15||legacy_checks!=3)$fatal(1,"count checks%0d legacy%0d",checks,legacy_checks);
 $display("PASS full552 five-lane static FMT1 composition:15 exact client transfers,3 legacy frame+CRC checks, registered calendar exact");$finish;
 end
endmodule
