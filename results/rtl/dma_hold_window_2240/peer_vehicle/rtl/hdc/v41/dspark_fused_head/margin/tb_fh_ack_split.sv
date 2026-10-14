`timescale 1ns/1ps
// Compare SAFE=2 receipt partition against the unchanged SAFE=1 cycle contract.
module tb_fh_ack_split;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,packet_v=0,ack_v=0;
 reg [23:0] word=24'h812345,ack_word=0;
 reg [15:0] mask=16'ha35c,ack_mask=0;
 reg [7:0] ack_id=0;
 wire [1:0] retired_v,retired_warm,busy,warm_ack,fault,debt;
 wire [31:0] packet[2]; wire [7:0] id[2];
 wire [63:0] veto[2],pre[2];wire [3:0] wv[2];
 for(genvar g=0;g<2;g=g+1)begin: u
  ot_hdc_v41_fh_retire_parent #(.ENABLE(1),.MARGIN(1),.SAFE(g+1),.PAYLOAD_BITS(32)) dut(
   .clk(clk),.rst_n(rst_n),.packet_v(packet_v),.warm(1'b1),.packet(32'h12345679),
   .warm_word(word),.warm_mask(mask),.poison(64'b0),.address_fault(4'b0),.arithmetic_fault(1'b0),
   .group_fault(4'b0),.sink_busy(1'b0),.ack_v(ack_v),.ack_id(ack_id),.ack_word(ack_word),.ack_mask(ack_mask),
   .retired_v(retired_v[g]),.retired_warm(retired_warm[g]),.retired_packet(packet[g]),.retired_id(id[g]),
   .lane_veto(veto[g]),.lane_veto_pre(pre[g]),.write_veto(wv[g]),.busy(busy[g]),.warm_ack(warm_ack[g]),
   .fault(fault[g]),.warm_debt(debt[g]));
 end
 task tick; begin
  @(posedge clk); #1;
  if({retired_v[0],retired_warm[0],packet[0],id[0],veto[0],pre[0],wv[0],busy[0],warm_ack[0],fault[0],debt[0]} !==
     {retired_v[1],retired_warm[1],packet[1],id[1],veto[1],pre[1],wv[1],busy[1],warm_ack[1],fault[1],debt[1]})
   $fatal(1,"SAFE receipt partition changed cycle semantics");
 end endtask
 reg [47:0] receipt; integer k,accepted=0,rejected=0;
 initial begin
  for(k=-1;k<48;k=k+1) begin
   @(negedge clk);rst_n=0;packet_v=0;ack_v=0;
   repeat(3)tick;
   @(negedge clk);rst_n=1;packet_v=1;tick;
   @(negedge clk);packet_v=0;
   repeat(12)tick;
   receipt={8'b0,word,mask};if(k>=0)receipt=receipt^(48'b1<<k);
   @(negedge clk);{ack_id,ack_word,ack_mask}=receipt;ack_v=1;tick;
   if(k<0)begin if(!warm_ack[1])$fatal(1,"correct receipt refused");accepted=accepted+1;end
   else begin if(warm_ack[1])$fatal(1,"corrupt receipt accepted");rejected=rejected+1;end
   @(negedge clk);ack_v=0;repeat(4)tick;
   if(k>=0&&!fault[1])$fatal(1,"corrupt receipt not quarantined");
  end
  $display("PASS ACK_SPLIT exact receipt edge: accepted=%0d rejected=%0d",accepted,rejected);$finish;
 end
endmodule
