`timescale 1ns/1ps
// Actual ROM W1 native apertures, connected adapter + original checked macro
// backing. Protocol data are raw IEEE bit patterns, not numerical activations.
module tb_qwen_w1_held_frame;
 localparam NR=2256,NW=865,VX0=208,NVX=2048;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg me_wanted=0;
 reg [NR-1:0] re=0;reg [NR*24-1:0] ra=0;wire [NR*32-1:0] rq;
 reg [NW-1:0] we=0;reg [NW*24-1:0] wa=0;reg [NW*32-1:0] wd=0;
 wire tick,lease,drained,fault,native_clk;
 wire [63:0] epoch,reads,writes,acks,held;
 reg [63:0] native_edges=0;
 ot_hdc_cg gate(.clk(clk),.en(!rst_n||tick),.gclk(native_clk));
 always @(posedge native_clk)if(rst_n)native_edges<=native_edges+1;
 ot_qwen_finite_vm_adapter #(.ENABLE(1),.HEAD_CACHE(0),.W1_FRAME(1),
   .NR(NR),.NW(NW),.VX0(VX0),.NVX(NVX)) dut(
   .clk(clk),.rst_n(rst_n),.source_me_wanted(me_wanted),.head_source_producer_go(1'b0),
   .read_en(re),.read_addr(ra),.read_q(rq),.write_en(we),.write_addr(wa),.write_data(wd),
   .native_tick(tick),.native_me_lease(lease),.drained(drained),.fault(fault),
   .native_epoch(epoch),.physical_reads(reads),.physical_writes(writes),.physical_ACKs(acks),
   .held_edges(held),.head_fill_reads(),.head_hit_edges());
 reg [31:0] reference_vm[0:177807],expected[0:NR-1];
 integer checks=0,output_checks=0,phase=0,leaf_frames=0,fallback_frames=0;
 reg watching=0;
 always @(posedge clk)if(rst_n)begin
   if(fault)$fatal(1,"unexpected adapter fault phase %0d state %0d",phase,dut.state);
   if(tick && (dut.pack_valid || dut.physical_writes!=dut.physical_ACKs))
     $fatal(1,"native advance with unpaid physical ACK/debt");
   if(dut.state==11 && dut.leaf_valid)leaf_frames<=leaf_frames+1;
   if(dut.state==11 && dut.leaf_fallback)fallback_frames<=fallback_frames+1;
   // Reference memory follows actual postverified write ACK, never supplies
   // DUT responses. Reads are checked against snapshots made before capture.
   if(dut.state==6 && |dut.wr_ACK)begin
     for(integer i=0;i<16;i=i+1)if(dut.pack_mask[i])
       reference_vm[dut.pack_word*16+i]<=dut.pack_data[i*32+:32];
   end
   if(watching && ((dut.leaf_active && dut.wr_issue) || dut.state==7))begin
     for(integer i=0;i<NR;i=i+1)if(re[i] && dut.raw[i*32+:32]!==expected[i])
       $fatal(1,"old-read snapshot mismatch phase %0d seat %0d",phase,i);
   end
 end
 function automatic [31:0] pattern(input integer a);
   case(a%8)
     0:pattern=32'h80000000;1:pattern=32'h7f800000;2:pattern=32'hff800000;
     3:pattern=32'h7fc12345;4:pattern=32'h7f812345;5:pattern=32'h00000001;
     6:pattern=32'h7f7fffff;default:pattern=32'h12345678^a;
   endcase
 endfunction
 task automatic frame(input integer weight_hold);
   reg [63:0] oldepoch,oldnative;integer edges,n;
   begin
     oldepoch=epoch;oldnative=native_edges;edges=0;
     for(n=0;n<NR;n=n+1)if(re[n])expected[n]=reference_vm[ra[n*24+:24]];
     watching=1;
     // Hold the real weight permission after frame capture; the activation
     // service may drain, but its completion cannot create a free ME grant.
     @(posedge clk);#1;
     if(weight_hold)begin
       @(negedge clk);me_wanted=0;
       while(dut.state!=7)begin
         @(negedge clk);edges=edges+1;
         if(fault || edges>NR*14+NW*33+4000)$fatal(1,"held frame failed to reach admission");
         if(epoch!=oldepoch || native_edges!=oldnative)$fatal(1,"source advanced while physical service held");
       end
       repeat(4)begin
         @(negedge clk);
         if(tick || lease || epoch!=oldepoch || native_edges!=oldnative || writes!=acks)
           $fatal(1,"weight hold bypassed or frame debt not drained");
       end
       me_wanted=1;
     end
     while(epoch==oldepoch)begin
       @(posedge clk);#1;edges=edges+1;
       if(fault || edges>NR*14+NW*33+4000)$fatal(1,"frame failed to drain");
       if(epoch==oldepoch && native_edges!=oldnative)$fatal(1,"controller advanced on held frame");
     end
     if(native_edges!=oldnative+1 || !drained || dut.g_w1.u_leaf.w1_valid || dut.g_w1.u_leaf.fallback_v)
       $fatal(1,"native release/leaf clear/XVM epoch mismatch");
     watching=0;@(negedge clk);re=0;we=0;
   end
 endtask
 // Boot source rows through the adapter's real write path; no deposit into
 // SRAM, mock grant, or host callback replaces the physical transaction.
 task automatic boot(input integer first,input integer count,input integer stride);
   integer offset,n,word,left;
   begin
     offset=0;
     while(offset<count)begin
       we=0;left=count-offset;if(left>54)left=54;
       for(n=0;n<left*16;n=n+1)begin
         word=first+((offset+n/16)/4)*stride+(offset+n/16)%4;
         we[n]=1;wa[n*24+:24]=word*16+n%16;wd[n*32+:32]=pattern(word*16+n%16);
       end
       frame(0);offset=offset+left;
     end
   end
 endtask
 reg [63:0] r0,w0,a0;reg [31:0] first_x[0:2047],second_x[0:2047];
 integer i,q;
 initial begin
   repeat(3)@(negedge clk);rst_n=1;
   boot(256,256,4);boot(5172,192,8);
   $display("BOOT actual_postverified_words=%0d",acks);
   phase=1;me_wanted=1;r0=reads;w0=writes;a0=acks;
   for(i=208;i<2256;i=i+1)begin
     re[i]=1;ra[i*24+:24]=4096+((i-208)%128)*32;
     first_x[i-208]=reference_vm[ra[i*24+:24]];
   end
   for(i=0;i<768;i=i+1)begin
     we[i]=1;wa[i*24+:24]=(5175+(i/16)*8)*16+i%16;
     wd[i*32+:32]=pattern(wa[i*24+:24]^16'h1234);
   end
   frame(1);
   if(reads-r0!=64 || writes-w0!=48 || acks-a0!=48 || leaf_frames!=1)
     $fatal(1,"W1 did not use 64 checked reads/48 real positive ACKs");
   for(i=0;i<2048;i=i+1)begin
     if(dut.xpipe[i*32+:32]!==first_x[i] || rq[(208+i)*32+:32]!==0)
       $fatal(1,"first native XVM capture/publication order mismatch %0d",i);
     checks=checks+1;
   end
   $display("W1 literalphase checked_reads=%0d positive_ACKs=%0d",reads-r0,acks-a0);
   // Actual next phase changes LIVE address parity; fallback must use those
   // addresses, not the literal firstphase leaf map. Same-frame SU writes a
   // read operand: all old reads must precede its physical masked write.
   phase=2;r0=reads;w0=writes;a0=acks;
   for(i=208;i<2256;i=i+1)begin
     re[i]=1;ra[i*24+:24]=4097+((i-208)%128)*32;
     second_x[i-208]=reference_vm[ra[i*24+:24]];
   end
   we[784]=1;wa[784*24+:24]=4097;wd[784*32+:32]=32'hdeadcafe;
   frame(1);
   if(reads-r0!=1024 || writes-w0!=1 || acks-a0!=1 || leaf_frames!=1)
     $fatal(1,"changed phase did not use original physical fallback");
   for(i=0;i<2048;i=i+1)begin
     if(rq[(208+i)*32+:32]!==first_x[i] || dut.xpipe[i*32+:32]!==second_x[i])
       $fatal(1,"cross-phase XVM publication mismatch %0d",i);
     checks=checks+1;
   end
   $display("W1 nextphase fallback_reads=%0d positive_ACKs=%0d",reads-r0,acks-a0);
   // A non-ME readback does not advance the held ME response. Check all 48
   // physically written vectors and their three preserved neighbor words.
   phase=3;me_wanted=0;
   for(q=0;q<48;q=q+1)begin
     for(i=0;i<64;i=i+1)begin re[i]=1;ra[i*24+:24]=(5172+8*q)*16+i;end
     frame(0);
     for(i=0;i<64;i=i+1)begin
       if(rq[i*32+:32]!==reference_vm[(5172+8*q)*16+i])$fatal(1,"physical W1 readback mismatch %0d/%0d",q,i);
       output_checks=output_checks+1;
     end
   end
   re[0]=1;ra[0+:24]=4097;frame(0);
   if(rq[0+:32]!==32'hdeadcafe)$fatal(1,"fallback masked ACK/readback missing");
   me_wanted=1;frame(0);
   for(i=0;i<2048;i=i+1)if(rq[(208+i)*32+:32]!==second_x[i])$fatal(1,"non-ME changed XVM response or empty ME failed to publish");
   // Negative owned ACK echo after all positive phases: fault must keep the
   // command unpaid and native source held; no synthetic success response.
   phase=4;me_wanted=0;we[784]=1;wa[784*24+:24]=4097;wd[784*32+:32]=32'habcdef01;
   @(posedge clk);#1;wait(dut.wr_ACK!=0);
   force dut.wr_ACK_owner=0;
   @(posedge clk);#1;release dut.wr_ACK_owner;
   if(!fault || tick || lease || !dut.pack_valid)$fatal(1,"foreign ACK discharged debt/native source");
   $display("PASS connected_native_W1 checked_reads64 postwrite_ACK48 oldreadchecks%0d outputchecks%0d crossphase_fallback1024 XVM_preserved weight_hold ACK_debt foreign_ACK",checks,output_checks);
   $finish;
 end
endmodule
