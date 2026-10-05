`timescale 1ns/1ps
module tb_qwen_rom_w1_frame_leaf;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,frame_start=0,frame_clear=0,frame_ue=0;
 wire frame_ready,w1_valid,fallback_v,fault;
 reg [2255:0] ren=0;reg [2256*24-1:0] raddr=0;
 reg [864:0] wen=0;reg [865*24-1:0] waddr=0;
 reg [865*32-1:0] wdata=0;
 reg window_v=0;reg [14:0] window_base=0;reg [2047:0] window_words=0;
 wire window_ready,read_put_v;reg read_put_ready=0;
 wire [2255:0] read_put_mask;wire [2256*32-1:0] read_put_data;
 reg select_v=0;reg [6:0] select_group=0;
 wire select_ready,pack_v;reg pack_ready=0;
 wire [14:0] pack_word;wire [15:0] pack_mask;wire [511:0] pack_data;
 ot_qwen_rom_w1_frame_leaf #(.ENABLE(1)) dut(.*);
 // Real unchanged full16 protected SRAM service, including acceptance and
 // postwrite readback. This bench is the enclosing adapter's owned FSM driver.
 reg rd_v=0;reg [14:0] rd_base_word=0;reg [226:0] rd_owner=0;
 wire rd_accept_v,rd_out_v;wire [1:0] rd_out_rot;
 wire [2047:0] rd_out_bank_words;wire [226:0] rd_out_owner;
 wire rd_fault,wr_fault,rw_collision_fault;
 reg [3:0] wr_v=0;reg [59:0] wr_word_addr=0;reg [2047:0] wr_word_data=0;
 reg [63:0] wr_lane_mask=0;reg [4*227-1:0] wr_owner=0;
 wire [3:0] wr_accept_v,wr_ack_v;wire [4*227-1:0] wr_ack_owner;
 wire [59:0] wr_ack_word_addr;wire [63:0] wr_ack_lane_mask;
 ot_qwen_checked_vm_bank bank(.*);
 integer cycle=0,owned_reads=0,owned_writes=0,read_scalar_checks=0,output_checks=0;
 reg [63:0] serial=1;reg [2255:0] received=0;
 reg held=0;reg [2255:0] held_ren;reg [2256*24-1:0] held_raddr;
 reg [864:0] held_wen;reg [865*24-1:0] held_waddr;reg [865*32-1:0] held_wdata;
 always @(posedge clk)begin
   cycle<=cycle+1;
   if(rst_n && (rd_fault||wr_fault||rw_collision_fault))$fatal(1,"actual bank fault");
   if(held && (ren!==held_ren||raddr!==held_raddr||wen!==held_wen||waddr!==held_waddr||wdata!==held_wdata))
      $fatal(1,"native frame changed during owned service");
   if(held && |wr_v && received!==ren)$fatal(1,"write before ALL old reads captured");
 end
 function automatic [31:0] pattern(input integer address);
   case(address%8)
     0:pattern=32'h80000000;1:pattern=32'h7f800000;2:pattern=32'hff800000;
     3:pattern=32'h7fc12345;4:pattern=32'h7f812345;5:pattern=32'h00000001;
     6:pattern=32'h7f7fffff;default:pattern=32'h12345678^address;
   endcase
 endfunction
 task automatic checked_write(input integer word,input [511:0] data);
   integer b,steps;reg [226:0] tag;
   begin
     b=word%4;tag={163'b0,serial};serial=serial+1;
     @(negedge clk);wr_v=1<<b;wr_word_addr=0;wr_word_addr[b*15+:15]=word;
     wr_word_data=0;wr_word_data[b*512+:512]=data;
     wr_lane_mask=0;wr_lane_mask[b*16+:16]=16'hffff;
     wr_owner=0;wr_owner[b*227+:227]=tag;
     @(posedge clk);if(wr_accept_v!==wr_v)$fatal(1,"write not accepted");
     @(negedge clk);wr_v=0;steps=0;
     while(wr_ack_v==0)begin @(negedge clk);steps=steps+1;if(steps>64)$fatal(1,"checked write failed to drain");end
     if(wr_ack_v!==(4'b1<<b)||wr_ack_owner[b*227+:227]!==tag||
        wr_ack_word_addr[b*15+:15]!==word||wr_ack_lane_mask[b*16+:16]!==16'hffff)
        $fatal(1,"actual postverified ACK identity/address/mask mismatch");
     @(negedge clk);
   end
 endtask
 task automatic checked_read(input integer base,output [2047:0] data);
   integer steps;reg [226:0] tag;
   begin
     tag={163'b0,serial};serial=serial+1;
     @(negedge clk);rd_v=1;rd_base_word=base;rd_owner=tag;
     @(posedge clk);if(!rd_accept_v)$fatal(1,"read not accepted");
     @(negedge clk);rd_v=0;steps=0;
     while(!rd_out_v)begin @(negedge clk);steps=steps+1;if(steps>32)$fatal(1,"checked read failed to drain");end
     if(rd_out_owner!==tag||rd_out_rot!==0)$fatal(1,"actual read owner/rotation mismatch");
     data=rd_out_bank_words;@(negedge clk);
   end
 endtask
 task automatic begin_frame;
   begin
     @(negedge clk);frame_start=1;
     @(negedge clk);frame_start=0;
     while(!w1_valid && !fallback_v && !fault)@(negedge clk);
     if(fault)$fatal(1,"frame validation fault");
   end
 endtask
 reg [511:0] payload;reg [2047:0] response;integer first,last,q,i,w,b,start_cycle;
 initial begin
   repeat(3)@(negedge clk);rst_n=1;
   // Explicit real VM writes initialize every read/modified word; no host
   // golden intermediate or constant-ready response substitutes for hardware.
   for(w=256;w<512;w=w+1)begin
     for(i=0;i<16;i=i+1)payload[i*32+:32]=pattern(w*16+i);
     checked_write(w,payload);
   end
   for(q=0;q<48;q=q+1)begin
     payload=0;checked_write(5175+8*q,payload);
   end
   for(i=208;i<2256;i=i+1)begin ren[i]=1;raddr[i*24+:24]=4096+((i-208)%128)*32;end
   for(i=0;i<768;i=i+1)begin
     wen[i]=1;waddr[i*24+:24]=(5175+(i/16)*8)*16+i%16;
     wdata[i*32+:32]=pattern(((5175+(i/16)*8)*16+i%16)^16'h1234);
   end
   held_ren=ren;held_raddr=raddr;held_wen=wen;held_waddr=waddr;held_wdata=wdata;
   held=1;start_cycle=cycle;begin_frame();
   if(fallback_v)$fatal(1,"actual literal W1 frame rejected");
   for(w=0;w<64;w=w+1)begin
     if(!window_ready)$fatal(1,"missing reserved response seat");
     checked_read(256+4*w,response);owned_reads=owned_reads+1;
     @(negedge clk);window_v=1;window_base=256+4*w;window_words=response;
     @(negedge clk);window_v=0;
     while(!read_put_v && !fault)@(negedge clk);
     if(fault)$fatal(1,"broadcast fault");
     for(i=0;i<2256;i=i+1)begin
       if(read_put_mask[i])begin
         if(!ren[i]||received[i]||read_put_data[i*32+:32]!==pattern(raddr[i*24+:24]))
           $fatal(1,"oldread mismatch/duplicate at actual source seat %0d",i);
         received[i]=1;read_scalar_checks=read_scalar_checks+1;
       end
     end
     // Real destination backpressure: payload and mask must stay held.
     response=read_put_data[208*32+:2048];repeat(w%3+1)@(negedge clk);
     if(!read_put_v||response!==read_put_data[208*32+:2048])$fatal(1,"broadcast changed while blocked");
     read_put_ready=1;@(negedge clk);read_put_ready=0;
   end
   if(received!==ren||read_scalar_checks!=2048)$fatal(1,"not all source reads captured");
   for(q=0;q<48;q=q+1)begin
     @(negedge clk);select_v=1;select_group=q;
     @(negedge clk);select_v=0;
     while(!pack_v && !fault)@(negedge clk);
     if(fault||pack_word!==15'(5175+8*q)||pack_mask!==16'hffff||pack_data!==wdata[q*512+:512])
        $fatal(1,"native masked group mismatch %0d",q);
     payload=pack_data;repeat(q%3+1)@(negedge clk);
     if(!pack_v||pack_data!==payload)$fatal(1,"masked pack changed while blocked");
     checked_write(pack_word,pack_data);owned_writes=owned_writes+1;
     pack_ready=1;@(negedge clk);pack_ready=0;
   end
   last=cycle-start_cycle;
   for(q=0;q<48;q=q+1)begin
     checked_read((5175+8*q)&~3,response);
     for(i=0;i<16;i=i+1)begin
       if(response[(48+i)*32+:32]!==wdata[(q*16+i)*32+:32])$fatal(1,"real VM output mismatch %0d/%0d",q,i);
       output_checks=output_checks+1;
     end
   end
   held=0;@(negedge clk);frame_clear=1;@(negedge clk);frame_clear=0;
   // All other phases reject before command emission; parent keeps old walker.
   raddr[208*24+:24]=4097;begin_frame();
   if(!fallback_v||w1_valid||pack_v||read_put_v)$fatal(1,"other phase not safely rejected");
   @(negedge clk);frame_clear=1;@(negedge clk);frame_clear=0;
   raddr[208*24+:24]=4096;wen[784]=1;waddr[784*24+:24]=4096;begin_frame();
   if(!fallback_v||w1_valid)$fatal(1,"cross-family alias not sent to original walker");
   @(negedge clk);frame_clear=1;@(negedge clk);frame_clear=0;
   wen[784]=0;begin_frame();
   checked_read(256,response);
   @(negedge clk);window_v=1;window_base=256;window_words=response;
   @(negedge clk);window_v=0;
   dut.rcode[0][0]=dut.rcode[0][0]^72'h3;
   while(!fault && !read_put_v)@(negedge clk);
   if(!fault||read_put_v||pack_v)$fatal(1,"uncorrectable response did not hold outputs closed");
   $display("PASS actualheldW1 checked_reads=%0d checked_postwrite_ACKs=%0d oldread_checks=%0d VMoutput_checks=%0d frame_cycles=%0d nonfinite_bits_preserved fallback=2 UEheld=1",owned_reads,owned_writes,read_scalar_checks,output_checks,last);
   $finish;
 end
 initial begin repeat(30000)@(posedge clk);$fatal(1,"source-derived bench failed to finish");end
endmodule
