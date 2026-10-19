`timescale 1ps/1ps
module tb_svg_landing_boundary;
 parameter integer MUT=0;
 reg hbm_clk=0,stream_clk=0,hbm_rst_n=0,stream_rst_n=0;
 always #512 hbm_clk=~hbm_clk;always #417 stream_clk=~stream_clk;
 reg in_v=0;wire in_ready,overflow;reg[284:0]in_data=0;
 reg reserve_v=0;reg[1:0]reserve_bank=0;reg[15:0]reserve_epoch=0;reg[11:0]reserve_total=272;reg stop=1;
 wire complete_v,fault;wire[1:0]complete_bank;
 reg read_v=0;reg[1:0]read_bank=0;reg[5:0]read_row=0;wire[255:0]read_data;
 integer errors=0,completes=0,b,r,reads=0,tx=0,wp=0,rp=0,round=0,stall_cycles=0,streak=0,max_streak=0;
 reg[284:0] accepted[0:2047];
 integer accept_edge[0:2047];integer hc=0,pin_start=0,core_start=0,pin_windows=0,core_windows=0;
 wire old_ready,old_over,old_complete,old_fault;wire[1:0]old_bank;wire[255:0]old_data;
 reg rv=0,st=1,rd=0;reg[1:0]rb=0,rdb=0;reg[15:0]ep=0;reg[11:0]total=0;reg[5:0]row=0;
 reg[255:0] read_expected=0;reg read_expected_v=0;
 reg[255:0] old_delayed_data=0;
 reg old_c,old_f;reg[1:0]old_b;
 function automatic[255:0]pattern(input integer bank,row);begin pattern={32'(bank),32'(row),32'(bank^row),32'(bank+row),32'(row*17),32'(bank+99),32'(row^32'hdeadbeef),32'(bank*64+row)};end endfunction
 ot_hbm_svc_sm8_landing_boundary #(.BANK(3),.BMUT(MUT==1?1:0),.FMUT(MUT==2?1:0)) dut(.*);
 // Original flop-FIFO master receives the accepted transaction stream at the
 // FIFO write edge, reconstructed independently from the external pin scoreboard.
 ot_hbm_svc_sm8_landing_bank #(.BANK(3),.LBANKS(4)) reference_bank(
 .hbm_clk(hbm_clk),.hbm_rst_n(dut.hreset),.stream_clk(stream_clk),.stream_rst_n(dut.sreset),
 .in_v(dut.pop),.in_ready(old_ready),.in_data(ref_packet),.overflow(old_over),
 .reserve_v(rv),.reserve_bank(rb),.reserve_epoch(ep),.reserve_total(total),.stop(st),
 .complete_v(old_complete),.complete_bank(old_bank),.fault(old_fault),
 .read_v(rd),.read_bank(rdb),.read_row(row),.read_data(old_data));
 always @(posedge hbm_clk)begin
  hc=hc+1;
  if(dut.hreset)begin
   if(in_v&&in_ready)begin accepted[wp]=in_data;accept_edge[wp]=hc;
    if(in_data[282:277]==16)pin_start=hc;
    if(in_data[282:277]==31)begin
     pin_windows=pin_windows+1;
     $display("PIN_SUSTAIN window=%0d sectors=16 HBM_edges=%0d",pin_windows,hc-pin_start+1);
     if(hc-pin_start!=15)errors=errors+1;
    end
    wp=wp+1;tx=tx+1;streak=streak+1;if(streak>max_streak)max_streak=streak;end else streak=0;
   if(dut.pop)begin
    if(rp>=wp||dut.head!==accepted[rp])begin errors=errors+1;if(errors<8)$display("INGRESS_ORDER_FAIL rp=%0d wp=%0d",rp,wp);end
    if(accepted[rp][282:277]>=16&&accepted[rp][282:277]<=31&&hc-accept_edge[rp]!=2)begin errors=errors+1;if(errors<8)$display("INGRESS_LATENCY_FAIL got=%0d expected=2",hc-accept_edge[rp]);end
    if(accepted[rp][282:277]==16)core_start=hc;
    if(accepted[rp][282:277]==31)begin
     core_windows=core_windows+1;
     $display("CORE_SUSTAIN window=%0d sectors=16 HBM_edges=%0d",core_windows,hc-core_start+1);
     if(hc-core_start!=15)errors=errors+1;
    end
    rp=rp+1;
   end
   if(wp-rp>3)begin errors=errors+1;if(errors<8)$display("ADMISSION_FAIL used=%0d",dut.used);end
   if(!in_ready)stall_cycles=stall_cycles+1;
   #1;
   if(dut.used!=wp-rp||(MUT!=1&&in_ready!==(dut.used<3)))begin errors=errors+1;if(errors<8)$display("RESERVATION_INVARIANT_FAIL used=%0d outstanding=%0d",dut.used,wp-rp);end
  end
 end
 // Avoid advancing the reference read pointer in the same active event as its
 // FIFO write sampling. Source is held from the preceding falling edge.
 reg[284:0] ref_packet=0;
 always @(negedge hbm_clk)ref_packet=accepted[rp];
 always @(posedge stream_clk)begin
  if(dut.sreset)begin
   old_c=old_complete;old_b=old_bank;old_f=old_fault;
   old_delayed_data=old_data;
   if(complete_v)completes=completes+1;
   #1;
   if(complete_v!==old_c||(complete_v&&complete_bank!==old_b)||fault!==old_f)begin errors=errors+1;if(errors<8)$display("EVENT_FAIL");end
   if(read_data!==old_delayed_data)begin errors=errors+1;if(errors<8)$display("READ_REFERENCE_FAIL");end
   if(read_expected_v)begin reads=reads+1;if(read_data!==read_expected)begin errors=errors+1;if(errors<8)$display("READ_PAYLOAD_FAIL bank=%0d row=%0d",rdb,row);end end
   read_expected_v=rd&&!st&&!old_f;read_expected=pattern(rdb,row);
   rv=reserve_v;rb=reserve_bank;ep=reserve_epoch;total=reserve_total;st=stop;rd=read_v;rdb=read_bank;row=read_row;
  end else begin rv=0;st=1;rd=0;read_expected_v=0;end
 end
 task idle(input integer n);begin repeat(n)@(negedge stream_clk);end endtask
 task send(input integer bank,row);begin
  @(negedge hbm_clk);while(!in_ready)begin in_v=0;@(negedge hbm_clk);end
  in_data={11'(3+8*row),2'(bank),16'(bank+7),pattern(bank,row)};in_v=1;
 end endtask
 initial begin
  for(round=0;round<3;round=round+1)begin
   hbm_rst_n=0;stream_rst_n=0;in_v=0;stop=1;reserve_v=0;read_v=0;idle(5);
   wp=0;rp=0;hbm_rst_n=1;stream_rst_n=1;idle(16);
   for(b=0;b<4;b=b+1)begin
    @(negedge stream_clk);reserve_v=1;reserve_bank=2'(b);reserve_epoch=16'(b+7);
    @(negedge stream_clk);reserve_v=0;stop=1;idle(3);
    // Fill the response FIFO and all reserved ingress slots, then release.
    fork
     begin idle(40);stop=0;end
     begin for(r=0;r<34;r=r+1)send(b,r);@(negedge hbm_clk);in_v=0;end
    join
    idle(20);
   end
   for(b=0;b<4;b=b+1)for(r=0;r<34;r=r+1)begin
    @(negedge stream_clk);read_v=1;read_bank=2'(b);read_row=6'(r);
   end
   @(negedge stream_clk);read_v=0;idle(6);
   if(fault||overflow||rp!=wp)errors=errors+1;
   if(round<2)begin stop=1;idle(3);send(0,0);send(0,1);@(negedge hbm_clk);in_v=0;end
  end
  if(completes!=12||reads!=408||stall_cycles<6||max_streak<8||pin_windows!=12||core_windows!=12)errors=errors+1;
  // Duplicate ordinal must still trip the original epoch/duplicate/count guard.
  send(0,0);@(negedge hbm_clk);in_v=0;idle(20);if(!fault)begin errors=errors+1;$display("GUARD_FAIL");end
  $display("SVG_BOUNDARY %s mut=%0d errors=%0d tx=%0d reads=%0d completes=%0d stalls=%0d max_burst=%0d",errors==0?"PASS":"FAIL",MUT,errors,tx,reads,completes,stall_cycles,max_streak);
  if(errors)$fatal(1,"boundary mismatch");$finish;
 end
 initial begin #10000000;$fatal(1,"BOUNDARY_TIMEOUT");end
endmodule
