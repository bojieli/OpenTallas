`timescale 1ns/1ps
module tb_a3_weight_tile_prefetch;
 parameter integer FIFO_DEPTH=4;
 localparam integer CW=$clog2(FIFO_DEPTH+1);
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg reserve_valid=0,reserve_bank=0,fill_valid=0,fill_bank=0;
 reg [63:0] reserve_tag=0,fill_tag=0,cancel_tag=0,tile_tag=0;
 reg [9:0] reserve_words=0,tile_words=0;
 reg [127:0] fill_data=0;
 reg cancel_valid=0,cancel_bank=0,tile_valid=0,tile_bank=0,tile_retain=0,word_ready=0;
 wire reserve_ready,fill_ready,cancel_ready,tile_ready,word_valid,word_last,tile_released;
 wire [127:0] word_data;
 wire [63:0] word_tag,released_tag;
 wire [63:0] tile_stream_tag=tile_tag;
 wire [9:0] word_index;
 wire [1:0] ready_banks,active_banks;
 wire [CW:0] reserved_slots;
 integer consumed=0,streak=0,max_streak=0,overlap=0,i;
 reg held=0;reg [202:0] held_word;
 ot_a3_weight_tile_prefetch #(.FIFO_DEPTH(FIFO_DEPTH)) dut(.*);
 task tick;begin @(posedge clk);#1;end endtask
 task load(input bit bank,input [63:0] tag,input integer words);
 integer j;
 begin
  @(negedge clk);reserve_valid=1;reserve_bank=bank;reserve_tag=tag;reserve_words=10'(words);
  #1;if(!reserve_ready)$fatal(1,"reserve refused");tick();@(negedge clk);reserve_valid=0;
  for(j=0;j<words;j=j+1)begin
   fill_valid=1;fill_bank=bank;fill_tag=tag;fill_data=128'(tag)+128'(j);
   #1;if(!fill_ready)$fatal(1,"fill refused");tick();@(negedge clk);
  end
  fill_valid=0;
 end endtask
 task launch(input bit bank,input [63:0] tag,input integer words);
 begin
  @(negedge clk);tile_valid=1;tile_bank=bank;tile_tag=tag;tile_words=10'(words);
  #1;while(!tile_ready)begin tick();@(negedge clk);end
  tick();@(negedge clk);tile_valid=0;
 end endtask
 always @(posedge clk)begin
  if(rst_n)begin
   if(reserved_slots>(CW+1)'(FIFO_DEPTH))$fatal(1,"FIFO reservation overflow");
   if(held && (!word_valid || {word_tag,word_index,word_last,word_data}!==held_word))
    $fatal(1,"stalled output changed");
   held<=word_valid && !word_ready;
   held_word<={word_tag,word_index,word_last,word_data};
   if(word_valid && word_ready)begin
    if(consumed<32)begin
     if(word_tag!==64'h100 || word_index!==10'(consumed) || word_data!==128'h100+128'(consumed) || word_last!==(consumed==31))$fatal(1,"tile0 order/data");
    end else if(consumed<34)begin
     if(word_tag!==64'h200 || word_index!==10'(consumed-32) || word_data!==128'h200+128'(consumed-32) || word_last!==(consumed==33))$fatal(1,"tile1 copy changed after bank reuse");
    end else if(consumed<66)begin
     if(word_tag!==64'h300 || word_index!==10'(consumed-34) || word_data!==128'h300+128'(consumed-34) || word_last!==(consumed==65))$fatal(1,"tile2 order/data");
    end else if(consumed<74)begin
     if(word_tag!==64'h400 || word_index!==10'((consumed-66)%4) || word_data!==128'h400+128'((consumed-66)%4) || word_last!==((consumed-66)%4==3))$fatal(1,"retained tile replay");
    end else begin
     if(word_tag!==64'h600 || word_index!==10'(consumed-74) || word_data!==128'h600+128'(consumed-74) || word_last!==(consumed==75))$fatal(1,"stale response after reset");
    end
    consumed=consumed+1;streak=streak+1;if(streak>max_streak)max_streak=streak;
    if(fill_valid && fill_ready)overlap=overlap+1;
   end else streak=0;
  end else held<=0;
 end
 initial begin
 tick();@(negedge clk);rst_n=1;
 load(0,64'h100,32);
 // Both undersized and oversized acquisitions must refuse without ownership.
 tile_bank=0;tile_tag=64'h100;tile_words=31;tile_valid=1;#1;
 if(tile_ready)$fatal(1,"short acquisition accepted");tick();@(negedge clk);
 tile_words=33;#1;if(tile_ready)$fatal(1,"long acquisition accepted");tick();@(negedge clk);tile_valid=0;
 launch(0,64'h100,32);word_ready=1;
 load(1,64'h200,2);
 wait(consumed==32);@(negedge clk);word_ready=0;
 launch(1,64'h200,2);
 // A one-entry FIFO cannot retain both words: consume the first before
 // stalling the last copy. Larger FIFOs retain the entire two-word tile.
 if(FIFO_DEPTH==1)begin
  word_ready=1;wait(consumed==33);@(negedge clk);word_ready=0;
 end
 // Queue copies survive bank release and overwrite while consumer is stalled.
 wait(tile_released);@(negedge clk);
 if(released_tag!==64'h200)$fatal(1,"wrong release identity");
 load(1,64'h300,32);
 repeat(8)tick();@(negedge clk);
 launch(1,64'h300,32);
 repeat(8)tick();@(negedge clk);
 for(i=0;consumed<66;i=i+1)begin
  word_ready=(i%7<4);tick();@(negedge clk);
 end
 word_ready=0;
 if(FIFO_DEPTH>=3 && max_streak<16)$fatal(1,"prefetch did not sustain continuous consumption");
 if(overlap==0)$fatal(1,"no refill/consume overlap exercised");
 // Retain a tile, then acquire it again without a second external fill.
 wait(active_banks==0);
 load(0,64'h400,4);tile_retain=1;
 launch(0,64'h400,4);word_ready=1;
 wait(consumed==70);wait(tile_released);@(negedge clk);word_ready=0;
 if(!ready_banks[0])$fatal(1,"retained tile lost residency");
 tile_retain=0;launch(0,64'h400,4);word_ready=1;
 wait(consumed==74);wait(tile_released);@(negedge clk);word_ready=0;
 if(ready_banks[0])$fatal(1,"final use retained bank");
 // Reset while an SRAM response is in flight; no old queue credit may survive.
 load(0,64'h500,8);launch(0,64'h500,8);
 wait(dut.outstanding);@(negedge clk);rst_n=0;
 #1;if(word_valid || reserved_slots!=0 || active_banks!=0)$fatal(1,"reset did not revoke in-flight state");
 tick();@(negedge clk);rst_n=1;
 repeat(3)tick();if(word_valid)$fatal(1,"old response survived reset");
 load(0,64'h600,2);launch(0,64'h600,2);word_ready=1;
 wait(consumed==76);@(negedge clk);word_ready=0;
 rst_n=0;#1;if(word_valid || tile_ready)$fatal(1,"reset left credits");
 $display("PASS tile prefetch words=%0d max_contiguous=%0d refill_consume_overlap=%0d depth=%0d",consumed,max_streak,overlap,FIFO_DEPTH);
 $finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
